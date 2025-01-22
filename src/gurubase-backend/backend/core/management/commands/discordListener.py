import os
import discord
import logging
import sys
import aiohttp
from django.core.management.base import BaseCommand
from django.conf import settings
from core.models import Integration, Thread
from datetime import datetime, timedelta
from asgiref.sync import sync_to_async
from core.utils import create_fresh_binge
import time

class Command(BaseCommand):
    help = 'Starts a Discord listener bot'

    def __init__(self):
        super().__init__()
        # In-memory cache for guild integrations
        self.guild_cache = {}
        # Cache timeout in seconds (e.g., 5 minutes)
        self.cache_timeout = 300
        self.prod_backend_url = settings.PROD_BACKEND_URL.rstrip('/')

    def get_trust_score_emoji(self, trust_score):
        score = trust_score / 100.0
        if score >= 0.8:
            return "🟢"  # Green
        elif score >= 0.6:
            return "🟡"  # Yellow
        elif score >= 0.4:
            return "🟡"  # Yellow
        elif score >= 0.2:
            return "🟠"  # Orange
        else:
            return "🔴"  # Red

    def format_response(self, response):
        formatted_msg = []
        
        # Calculate space needed for metadata (trust score and references)
        metadata_length = 0
        trust_score = response.get('trust_score', 0)
        trust_emoji = self.get_trust_score_emoji(trust_score)
        metadata_length += len(f"\n\n**Trust Score**: {trust_emoji} {trust_score}%\n")
        
        if response.get('references'):
            metadata_length += len("\n**References**:")
            for ref in response['references']:
                metadata_length += len(f"\n• [{ref['title']}](<{ref['link']}>)")
        
        # Calculate max length for content to stay within Discord's 2000 char limit
        max_content_length = 1900 - metadata_length  # Leave some buffer
        
        # Truncate content if necessary
        content = response['content']
        if len(content) > max_content_length:
            content = content[:max_content_length-3] + "..."
        
        # Build the message
        formatted_msg.append(content)
        
        # Add trust score
        formatted_msg.append(f"\n**Trust Score**: {trust_emoji} {trust_score}%")
        
        # Add references if they exist
        if response.get('references'):
            formatted_msg.append("\n**References**:")
            for ref in response['references']:
                formatted_msg.append(f"\n• [{ref['title']}](<{ref['link']}>)")
        
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
        current_time = datetime.now()
        
        # Check if guild is in cache and not expired
        if guild_id in self.guild_cache:
            cached_data = self.guild_cache[guild_id]
            if current_time < cached_data['expires_at']:
                return cached_data['integration']
            else:
                # Remove expired cache entry
                del self.guild_cache[guild_id]
        
        # If not in cache or expired, query database
        try:
            # Wrap the database query in sync_to_async
            integration = await sync_to_async(Integration.objects.get)(
                type=Integration.Type.DISCORD,
                external_id=guild_id
            )
            # Cache the result
            self.guild_cache[guild_id] = {
                'integration': integration,
                'expires_at': current_time + timedelta(seconds=self.cache_timeout)
            }
            return integration
        except Integration.DoesNotExist:
            # Cache negative result too to avoid repeated DB queries
            self.guild_cache[guild_id] = {
                'integration': None,
                'expires_at': current_time + timedelta(seconds=self.cache_timeout)
            }
            return None

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
        url = f"{self.prod_backend_url}/api/v1/{guru_type}/answer/"
        headers = {
            'X-API-KEY': f'{api_key}',
            'Content-Type': 'application/json'
        }
        payload = {
            'question': question,
            'stream': True,
            'short_answer': True
        }
        if binge_id:
            payload['session_id'] = str(binge_id)
        
        buffer = ""
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, headers=headers) as response:
                async for chunk in response.content:
                    if chunk:
                        text = chunk.decode('utf-8')
                        buffer += text
                        if buffer.strip():
                            yield buffer

    async def get_finalized_answer(self, guru_type, question, api_key, binge_id=None):
        url = f"{self.prod_backend_url}/api/v1/{guru_type}/answer/"
        headers = {
            'X-API-KEY': f'{api_key}',
            'Content-Type': 'application/json'
        }
        payload = {
            'question': question,
            'stream': False,
            'short_answer': True,
            'fetch_existing': True
        }
        if binge_id:
            payload['session_id'] = str(binge_id)
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, headers=headers) as response:
                response_json = await response.json()
                if response.status == 200:
                    return response_json, True
                else:
                    print(response_json, type(response_json))
                    return response_json['msg'], False

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

            # Check if bot was mentioned
            if client.user in message.mentions:
                # Get guild ID and look for integration
                guild_id = str(message.guild.id) if message.guild else None
                if guild_id:
                    integration = await self.get_guild_integration(guild_id)
                    if integration and integration.access_token:
                        # Remove the bot mention from the message
                        question = message.content.replace(f'<@{client.user.id}>', '').strip()
                        print(question)
                        
                        # Get guru type slug safely
                        guru_type_slug = await self.get_guru_type_slug(integration)
                        api_key = await self.get_api_key(integration)
                        guru_type_object = await sync_to_async(lambda: integration.guru_type)()

                        # Check if message is in a thread
                        binge_id = None
                        try:
                            if message.channel.type == discord.ChannelType.public_thread:
                                # If in thread, send thinking message directly to thread
                                thinking_msg = await message.channel.send("Thinking... 🤔")
                                
                                raise Exception("Not implemented")
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
                            
                            # First, stream the response
                            async for streamed_content in self.stream_answer(
                                guru_type_slug,
                                question,
                                api_key,
                                binge_id
                            ):
                                current_time = time.time()
                                if current_time - last_update >= update_interval:
                                    await thinking_msg.edit(content=streamed_content)
                                    last_update = current_time
                            
                            # After streaming is done, fetch the formatted response
                            response, success = await self.get_finalized_answer(
                                guru_type_slug,
                                question,
                                api_key,
                                binge_id
                            )
                            
                            if success:
                                formatted_response = self.format_response(response)
                                await thinking_msg.edit(content=formatted_response)
                            else:
                                error_msg = response if response else "Sorry, I couldn't process your request. 😕"
                                await thinking_msg.edit(content=error_msg)
                                
                        except discord.Forbidden:
                            logging.error(f"Discord forbidden error occurred: {str(e)}")
                            await thinking_msg.edit(content="❌ I don't have permission to perform this action. Please check my permissions.")
                        except discord.HTTPException as e:
                            logging.error(f"Discord API error occurred: {str(e)}")
                            await thinking_msg.edit(content=f"❌ Discord API error occurred")
                        except aiohttp.ClientError:
                            logging.error(f"Network error occurred while processing your request. {str(e)}")
                            await thinking_msg.edit(content="❌ Network error occurred while processing your request.")
                        except Exception as e:
                            logging.error(f"An unexpected error occurred: {str(e)}")
                            await thinking_msg.edit(content=f"❌ An unexpected error occurred.")

        return client, handler

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting Discord listener...'))
        
        try:
            client, handler = self.setup_discord_client()
            token = settings.DISCORD_BOT_TOKEN
            
            client.run(token, log_handler=handler, log_level=logging.DEBUG)
        except KeyboardInterrupt:
            self.stdout.write(self.style.SUCCESS('Shutting down Discord listener...'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error: {str(e)}')) 