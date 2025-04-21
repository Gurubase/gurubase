import re
import traceback
import discord
import logging
import sys
import aiohttp
from django.core.management.base import BaseCommand
from django.conf import settings
from core.integrations.helpers import NotEnoughData, NotRelated, cleanup_title, get_trust_score_emoji
from core.models import Integration, Thread
from asgiref.sync import sync_to_async
from core.utils import create_fresh_binge
import time
from django.core.cache import caches
import requests
from core.views import api_answer
from rest_framework.test import APIRequestFactory

class BotTokenValidationException(Exception):
    pass

class Command(BaseCommand):
    help = 'Starts a Discord listener bot'

    def __init__(self):
        super().__init__()
        # Cache timeout in seconds (e.g., 5 minutes)
        # Set to 0 to disable caching
        # This is because dynamic channel updates are not immediately reflected
        # And this may result in bad UX, and false positive bug reports
        self.cache_timeout = 0

    def strip_first_header(self, content):
        """Remove the first header (starting with # and ending with newline) from content."""
        if content.startswith('#'):
            # Find the first newline
            newline_index = content.find('\n')
            if newline_index != -1:
                # Return content after the newline
                return content[newline_index + 1:].lstrip()
        return content

    def format_response(self, response):
        formatted_msg = []
        content = self.strip_first_header(response['content'])
        metadata_length = 0
        
        # Calculate space needed for metadata (trust score and references)
        trust_score = response.get('trust_score', 0)
        trust_emoji = get_trust_score_emoji(trust_score)
        formatted_msg.append(f"---------\n_**Trust Score**: {trust_emoji} {trust_score}%_")
        
        if response.get('references'):
            formatted_msg.append("_**Sources:**_")
            for ref in response['references']:
                # Remove both Slack-style emoji codes and Unicode emojis along with adjacent spaces
                clean_title = re.sub(r'\s*:[a-zA-Z0-9_+-]+:\s*', ' ', ref['title'])

                # Then remove Unicode emojis and their modifiers with adjacent spaces
                clean_title = re.sub(
                    r'\s*(?:[\u2600-\u26FF\u2700-\u27BF\U0001F300-\U0001F9FF\U0001FA70-\U0001FAFF]'
                    r'[\uFE00-\uFE0F\U0001F3FB-\U0001F3FF]?\s*)+',
                    ' ',
                    clean_title
                ).strip()

                formatted_msg.append(f"• [*{clean_title}*](<{ref['link']}>)")

        # Add space for frontend link
        formatted_msg.append(f":eyes: [_View on Gurubase for a better UX_](<{response['question_url']}>)")

        metadata_length = sum(len(msg) for msg in formatted_msg)
        
        # Calculate max length for content to stay within Discord's 2000 char limit
        max_content_length = 1900 - metadata_length  # Leave some buffer
        
        # Truncate content if necessary
        if len(content) > max_content_length:
            content = content[:max_content_length-3] + "..."

        formatted_msg.insert(0, content)
        
        return "\n".join(formatted_msg)

    async def get_guru_type_slug(self, integration):
        # Wrap the guru_type access in sync_to_async
        guru_type = await sync_to_async(lambda: integration.guru_type)()
        return await sync_to_async(lambda: guru_type.slug)()

    async def get_api_key(self, integration):
        # Wrap the guru_type access in sync_to_async
        api_key = await sync_to_async(lambda: integration.api_key)()
        return await sync_to_async(lambda: api_key.key)()

    async def get_guild_integration(self, guild_id):
        # Try to get integration from cache first
        cache = caches['alternate']
        cache_key = f"discord_integration:{guild_id}"
        integration = cache.get(cache_key)
        
        if not integration:
            try:
                # If not in cache, get from database
                integration = await sync_to_async(Integration.objects.get)(
                    type=Integration.Type.DISCORD,
                    external_id=guild_id
                )
                # Cache for 5 minutes
                cache.set(cache_key, integration, timeout=self.cache_timeout)
            except Integration.DoesNotExist:
                logging.error(f"No integration found for guild {guild_id}", exc_info=True)
                return None
        
        return integration

    async def get_or_create_thread_binge(self, thread_id, integration, guru_type_object):
        try:
            # Try to get existing thread
            thread = await sync_to_async(Thread.objects.get)(thread_id=thread_id, integration=integration)
            # Get binge asynchronously
            binge = await sync_to_async(lambda: thread.binge)()
            return binge
        except Thread.DoesNotExist:
            # Create new binge and thread without needing a question
            binge = await sync_to_async(create_fresh_binge)(guru_type_object, None)
            await sync_to_async(Thread.objects.create)(
                thread_id=thread_id,
                binge=binge,
                integration=integration
            )
            return binge

    async def stream_answer(self, guru_type, question, api_key, binge_id=None):
        # Create request using APIRequestFactory
        factory = APIRequestFactory()
        
        request_data = {
            'question': question,
            'stream': True,
            'short_answer': True
        }
        if binge_id:
            request_data['session_id'] = str(binge_id)
            
        request = factory.post(
            f'/api/v1/{guru_type}/answer/',
            request_data,
            HTTP_X_API_KEY=api_key,
            format='json'
        )
        
        # Call api_answer directly in a sync context
        response = await sync_to_async(api_answer)(request, guru_type)
        
        # Handle StreamingHttpResponse
        if hasattr(response, 'streaming_content'):
            buffer = ""
            line_buffer = ""
            
            # Create an async wrapper for the generator iteration
            @sync_to_async
            def get_next_chunk():
                try:
                    return next(response.streaming_content)
                except StopIteration:
                    return None
            
            # Iterate over the generator asynchronously
            while True:
                chunk = await get_next_chunk()
                if chunk is None:
                    # Yield any remaining text in the buffer
                    if line_buffer.strip():
                        buffer += line_buffer
                        yield buffer
                    break
                    
                if chunk:
                    text = chunk.decode('utf-8') if isinstance(chunk, bytes) else str(chunk)
                    line_buffer += text
                    
                    # Check if we have complete lines
                    while '\n' in line_buffer:
                        line, line_buffer = line_buffer.split('\n', 1)
                        if line.strip():
                            buffer += line + '\n'
                            yield buffer

    async def get_finalized_answer(self, guru_type, question, api_key, binge_id=None):
        # Create request using APIRequestFactory
        factory = APIRequestFactory()
        
        request_data = {
            'question': question,
            'stream': False,
            'short_answer': True,
            'fetch_existing': True
        }
        if binge_id:
            request_data['session_id'] = str(binge_id)
            
        request = factory.post(
            f'/api/v1/{guru_type}/answer/',
            request_data,
            HTTP_X_API_KEY=api_key,
            format='json'
        )
        
        try:
            # Call api_answer directly
            response = await sync_to_async(api_answer)(request, guru_type)
            
            # Convert response to dict if it's a Response object
            if hasattr(response, 'data'):
                return response.data, True
            return response, True
        except Exception as e:
            return str(e), False

    async def send_channel_unauthorized_message(
        self,
        message: discord.Message,
        guru_slug: str,
        question: str
    ) -> None:
        """Send a message explaining how to authorize the channel."""
        try:
            settings_url = f"{settings.BASE_URL.rstrip('/')}/guru/{guru_slug}/integrations/discord"
            
            # Create embed for better formatting
            embed = discord.Embed(
                title="❌ Channel Not Authorized",
                description=(
                    "This channel is not authorized to use the bot.\n\n"
                    f"Please visit [Gurubase Settings]({settings_url}) to configure "
                    "the bot and add this channel to the allowed channels list."
                ),
                color=discord.Color.red()  # Red color for error messages
            )
            
            # If in a thread, reply in thread. Otherwise create a thread
            if isinstance(message.channel, discord.Thread):
                await message.channel.send(embed=embed)
            else:
                thread = await message.create_thread(
                    name=f"Q: {question[:50]}...",
                    auto_archive_duration=60  # Archive after 1 hour of inactivity
                )
                await thread.send(embed=embed)
            
        except discord.Forbidden as e:
            logging.error(f"Discord forbidden error while sending unauthorized message: {str(e)}")
        except discord.HTTPException as e:
            logging.error(f"Discord API error while sending unauthorized message: {str(e)}")
        except Exception as e:
            logging.error(f"Error sending unauthorized channel message: {str(e)}")

    def setup_discord_client(self):
        # Setup logging to stdout
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))

        # Setup Discord client
        intents = discord.Intents.default()
        intents.message_content = True
        client = discord.Client(intents=intents, connector=None)

        @client.event
        async def on_ready():
            self.stdout.write(self.style.SUCCESS(f'We have logged in as {client.user}'))

        @client.event
        async def on_message(message):
            if message.author == client.user:
                return

            # First check if bot was mentioned
            if client.user not in message.mentions:
                return

            # Then check if we have a valid guild
            guild_id = str(message.guild.id) if message.guild else None
            if not guild_id:
                return

            # Get integration from cache/database
            integration = await self.get_guild_integration(guild_id)
            await sync_to_async(lambda: print(f'integration: {integration}'))()
            if not integration or not await sync_to_async(lambda: integration.access_token)():
                return

            try:
                # Check if the current channel is allowed
                channel_id = str(message.channel.id)
                # If message is from a thread, get the parent channel id
                if isinstance(message.channel, discord.Thread):
                    channel_id = str(message.channel.parent_id)
                
                channels = await sync_to_async(lambda: integration.channels)()
                channel_allowed = False
                question = message.content.replace(f'<@{client.user.id}>', '').strip()

                for channel in channels:
                    if str(channel.get('id')) == channel_id and channel.get('allowed', False):
                        channel_allowed = True
                        break
                
                if not channel_allowed:
                    guru_type_slug = await self.get_guru_type_slug(integration)
                    await self.send_channel_unauthorized_message(
                        message, 
                        guru_type_slug, 
                        question)
                    return

                # Remove the bot mention from the message
                
                # Get guru type slug and API key
                guru_type_slug = await self.get_guru_type_slug(integration)
                api_key = await self.get_api_key(integration)
                guru_type_object = await sync_to_async(lambda: integration.guru_type)()

                # Handle message in thread or create new thread
                try:
                    if message.channel.type == discord.ChannelType.public_thread:
                        # If in thread, send thinking message directly to thread
                        thread = message.channel
                        thinking_msg = await thread.send("Thinking... 🤔")
                        
                        # Get or create thread and binge
                        binge = await self.get_or_create_thread_binge(
                            str(message.channel.id),
                            integration,
                            guru_type_object
                        )
                        binge_id = binge.id
                    else:
                        # If not in thread, create a thread and send thinking message there
                        thread = await message.create_thread(
                            name=f"Q: {question[:50]}...",  # Use first 50 chars of question as thread name
                            auto_archive_duration=60  # Archive after 1 hour of inactivity
                        )
                        thinking_msg = await thread.send("Thinking... 🤔")
                        
                        # Create new thread and binge
                        binge = await self.get_or_create_thread_binge(
                            str(thread.id),
                            integration,
                            guru_type_object
                        )
                        binge_id = binge.id
                    
                    last_update = time.time()
                    update_interval = 0.5  # Update every 0.5 seconds
                    messages = [thinking_msg]  # List to keep track of all messages
                    previous_content = ""  # Track the total content we've seen before
                    message_contents = {"thinking": ""}  # Track actual content of each message
                    
                    # First, stream the response
                    async for streamed_content in self.stream_answer(
                        guru_type_slug,
                        question,
                        api_key,
                        binge_id
                    ):
                        current_time = time.time()
                        if current_time - last_update >= update_interval:
                            # Strip header from streamed content
                            cleaned_content = self.strip_first_header(streamed_content)
                            if cleaned_content:
                                # Get the new content by removing what we've seen before
                                if previous_content and cleaned_content.startswith(previous_content):
                                    new_content = cleaned_content[len(previous_content):]
                                else:
                                    new_content = cleaned_content
                                    
                                if new_content:  # Only proceed if we have new content
                                    new_content = re.sub(r'(\[.*?\]\()(http[^\)]+)(\))', r'\1<\2>\3', new_content)
                                    new_content = re.sub(r'\s*#{4,}\s*', '', new_content)
                                    current_message = messages[-1]  # Get the last message
                                    current_msg_id = str(current_message.id)
                                    if current_msg_id not in message_contents:
                                        message_contents[current_msg_id] = ""
                                    
                                    # Check if adding new content would exceed limit
                                    if len(message_contents[current_msg_id] + new_content) + len('\n:clock1: _streaming..._') > 1900:
                                        # Remove streaming indicator from current message
                                        await current_message.edit(content=message_contents[current_msg_id])
                                        
                                        # Create new message with just the new content in the thread
                                        new_message = await thread.send(new_content + '\n:clock1: _streaming..._')
                                        messages.append(new_message)
                                        message_contents[str(new_message.id)] = new_content
                                    else:
                                        # Update current message with combined content
                                        message_contents[current_msg_id] += new_content
                                        await current_message.edit(
                                            content=message_contents[current_msg_id] + '\n:clock1: _streaming..._'
                                        )
                                    
                                    previous_content = cleaned_content  # Update what we've seen
                                last_update = current_time
                    
                    # After streaming is done, fetch the formatted response
                    response, success = await self.get_finalized_answer(
                        guru_type_slug,
                        question,
                        api_key,
                        binge_id
                    )
                    
                    if success:
                        # Clean up streaming indicators from all messages
                        for msg in messages[:-1]:
                            msg_id = str(msg.id)
                            if msg_id in message_contents:
                                await msg.edit(content=message_contents[msg_id])
                        
                        # Format metadata
                        trust_score = response.get('trust_score', 0)
                        trust_emoji = get_trust_score_emoji(trust_score)
                        metadata = f"\n---------\n_**Trust Score**: {trust_emoji} {trust_score}%_"
                        
                        if 'msg' in response and 'doesn\'t have enough data' in response['msg']:
                            raise NotEnoughData(response['msg'])
                        elif 'msg' in response and 'is not related to' in response['msg']:
                            raise NotRelated(response['msg'])
                        elif 'msg' in response:
                            raise Exception(response['msg'])

                        if response.get('references'):
                            metadata += "\n_**Sources:**_"
                            for ref in response['references']:
                                # Remove both Slack-style emoji codes and Unicode emojis along with adjacent spaces
                                clean_title = cleanup_title(ref['title'])
                                metadata += f"\n• [*{clean_title}*](<{ref['link']}>)"
                        
                        metadata += f"\n:eyes: [_View on Gurubase for a better UX_](<{response['question_url']}>)"
                        
                        # Get complete response with metadata
                        complete_response = response['content'] + metadata
                        
                        # Split into chunks preserving code blocks
                        chunks = self.split_content_preserve_codeblocks(complete_response)
                        
                        # Update existing messages or create/delete as needed
                        for i, chunk in enumerate(chunks):
                            # Remove leading # and newline if present
                            if i == 0 and chunk.startswith('#'):
                                newline_index = chunk.find('\n')
                                if newline_index != -1:
                                    chunk = chunk[newline_index + 1:].lstrip()

                            # Use regex to format links by enclosing URLs in angle brackets
                            chunk = re.sub(r'(\[.*?\]\()(http[^\)]+)(\))', r'\1<\2>\3', chunk)
                            if i < len(messages):
                                # Update existing message
                                await messages[i].edit(content=chunk)
                            else:
                                # Create new message for extra chunk
                                new_msg = await thread.send(chunk)
                                messages.append(new_msg)
                        
                        # Delete any extra messages if we have fewer chunks
                        if len(chunks) < len(messages):
                            for msg in messages[len(chunks):]:
                                await msg.delete()
                            messages = messages[:len(chunks)]
                    else:
                        error_msg = response if response else "Sorry, I couldn't process your request. 😕"
                        # Clean up all messages except the first one
                        for msg in messages[1:]:
                            await msg.delete()
                        await messages[0].edit(content=error_msg)
                        
                except NotRelated as e:
                    logging.error(f"Not related to the question: {str(e)}")
                    await thinking_msg.edit(content=f'❌ {str(e)}')
                except NotEnoughData as e:
                    logging.error(f"Not enough data to process question: {str(e)}")
                    await thinking_msg.edit(content=f'❌ {str(e)}')
                except discord.Forbidden as e:
                    logging.error(f"Discord forbidden error occurred: {str(e)}")
                    await thinking_msg.edit(content="❌ I don't have permission to perform this action. Please check my permissions.")
                except discord.HTTPException as e:
                    logging.error(f"Discord API error occurred: {str(e)}")
                    await thinking_msg.edit(content=f"❌ Discord API error occurred")
                except aiohttp.ClientError as e:
                    logging.error(f"Network error occurred while processing your request. {str(e)}")
                    await thinking_msg.edit(content="❌ Network error occurred while processing your request.")
                except Exception as e:
                    logging.error(f"An unexpected error occurred: {str(e)}. {traceback.format_exc()}")
                    await thinking_msg.edit(content=f"❌ An unexpected error occurred.")

            except Exception as e:
                logging.error(f"Error processing Discord message: {str(e)}", exc_info=True)

        return client, handler

    def _validate_bot_token(self, token: str) -> bool:
        """Validate a bot token by making a sample request to Discord API"""
        try:
            response = requests.get(
                'https://discord.com/api/v10/users/@me',
                headers={'Authorization': f'Bot {token}'}
            )
            return response.status_code == 200
        except Exception as e:
            logging.error(f"Error validating bot token: {str(e)}")
            return False

    def _get_valid_bot_token(self) -> str:
        """Get a valid bot token based on environment"""
        if settings.ENV != 'selfhosted':
            token = settings.DISCORD_BOT_TOKEN
            if not self._validate_bot_token(token):
                raise BotTokenValidationException(
                    "Invalid Discord bot token in settings.DISCORD_BOT_TOKEN. "
                    "Please check your environment variables and ensure the bot token is valid."
                )
            logging.info("Using bot token from settings")
            return token

        # Get all Discord integrations
        discord_integrations = Integration.objects.filter(type=Integration.Type.DISCORD)
        if not discord_integrations.exists():
            raise BotTokenValidationException("No Discord integrations found in selfhosted mode")

        # Get unique tokens
        unique_tokens = set(integration.access_token for integration in discord_integrations if integration.access_token)
        
        if len(unique_tokens) > 1:
            logging.warning(
                "Multiple Discord bots detected! This is not recommended. \n"
                "Please review your integrations and delete any unnecessary bots. \n"
                f"Found {len(unique_tokens)} unique bot tokens. \n"
                "Will try to use the first valid one."
            )

        # Try each token until we find a valid one
        for token in unique_tokens:
            if self._validate_bot_token(token):
                logging.info(f"Using bot token: {token}")
                return token

        raise BotTokenValidationException(
            "No valid Discord bot tokens found. Please check your integration settings "
            "and ensure at least one bot token is valid."
        )

    def split_content_preserve_codeblocks(self, content, max_length=1900):
        """Split content into chunks while preserving code blocks and staying under max_length."""
        chunks = []
        current_chunk = ""
        in_code_block = False
        code_block_content = ""
        lines = content.split('\n')
        
        def try_add_to_current_chunk(text_to_add):
            nonlocal current_chunk
            if not current_chunk:
                return text_to_add
            elif len(current_chunk + text_to_add) <= max_length:
                return current_chunk + text_to_add
            else:
                chunks.append(current_chunk.rstrip())
                return text_to_add.lstrip()  # Remove leading newline
        
        for line in lines:
            # Check for code block markers
            if line.strip().startswith('```'):
                if in_code_block:
                    # End of code block
                    code_block_content += line + '\n'
                    # Try to add the complete code block to current chunk
                    new_chunk = try_add_to_current_chunk(code_block_content)
                    if len(new_chunk) <= max_length:
                        current_chunk = new_chunk
                    else:
                        # If code block doesn't fit, it needs its own chunk(s)
                        if current_chunk:
                            chunks.append(current_chunk.rstrip())
                        if len(code_block_content) <= max_length:
                            current_chunk = code_block_content
                        else:
                            # If code block itself is too long, split it
                            code_chunks = [code_block_content[i:i+max_length] for i in range(0, len(code_block_content), max_length)]
                            chunks.extend(chunk.rstrip() for chunk in code_chunks[:-1])
                            current_chunk = code_chunks[-1]
                    code_block_content = ""
                    in_code_block = False
                else:
                    # Start of code block
                    in_code_block = True
                    code_block_content = line + '\n'
            else:
                if in_code_block:
                    code_block_content += line + '\n'
                else:
                    # Regular line handling
                    new_chunk = try_add_to_current_chunk(line + '\n')
                    if len(new_chunk) <= max_length:
                        current_chunk = new_chunk
                    else:
                        chunks.append(current_chunk.rstrip())
                        current_chunk = line + '\n'
        
        # Add any remaining content
        if code_block_content:
            # Try to add the final code block to current chunk
            new_chunk = try_add_to_current_chunk(code_block_content)
            if len(new_chunk) <= max_length:
                current_chunk = new_chunk
            else:
                if current_chunk:
                    chunks.append(current_chunk.rstrip())
                current_chunk = code_block_content
        
        if current_chunk:
            chunks.append(current_chunk.rstrip())
        
        cleared_chunks = []
        for chunk in chunks:
            intermediate_chunk = re.sub(r'\n\n', '\n', chunk)
            intermediate_chunk = re.sub(r'\s*#{4,}\s*', '', intermediate_chunk)
            cleared_chunks.append(intermediate_chunk)

        return cleared_chunks

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting Discord listener...'))
        
        while True:
            try:
                client, handler = self.setup_discord_client()
                token = self._get_valid_bot_token()
                
                client.run(token, log_handler=handler, log_level=logging.DEBUG)
                break  # If client.run() completes normally, exit the loop
            except BotTokenValidationException as e:
                # self.stdout.write(self.style.WARNING(f'No valid bot token found: {str(e)}'))
                # self.stdout.write(self.style.WARNING('Retrying in 5 seconds...'))
                time.sleep(5)  # Wait for 5 seconds before retrying
            except KeyboardInterrupt:
                self.stdout.write(self.style.SUCCESS('Shutting down Discord listener...'))
                break
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'Error: {str(e)}'))
                raise 