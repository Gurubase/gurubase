import os
import discord
import logging
import sys
import aiohttp
from django.core.management.base import BaseCommand
from django.conf import settings
from core.models import Integration, GuruType
from django.core.cache import cache
from datetime import datetime, timedelta
from asgiref.sync import sync_to_async

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
                metadata_length += len(f"\n• [{ref['title']}]({ref['link']})")
        
        # Calculate max length for content to stay within Discord's 2000 char limit
        max_content_length = 1900 - metadata_length  # Leave some buffer
        
        # Truncate content if necessary
        content = response['content']
        if len(content) > max_content_length:
            content = content[:max_content_length-3] + "..."
        
        # Build the message
        formatted_msg.append(content)
        
        # Add trust score
        formatted_msg.append(f"\n\n**Trust Score**: {trust_emoji} {trust_score}%\n")
        
        # Add references if they exist
        if response.get('references'):
            formatted_msg.append("\n**References**:")
            for ref in response['references']:
                formatted_msg.append(f"\n• [{ref['title']}]({ref['link']})")
        
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

    async def send_question_to_backend(self, guru_type, question, api_key):
        url = f"{self.prod_backend_url}/api/v1/{guru_type}/answer/"
        headers = {
            'X-API-KEY': f'{api_key}',
            'Content-Type': 'application/json'
        }
        payload = {
            'question': question,
            'stream': False,
            'short_answer': True
        }
        
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

                        thinking_msg = await message.channel.send("Thinking... 🤔")
                        
                        # Send request to backend
                        response, success = await self.send_question_to_backend(
                            guru_type_slug,
                            question,
                            api_key
                        )
                        
                        if success:
                            formatted_response = self.format_response(response)
                            await thinking_msg.edit(content=formatted_response)
                        else:
                            if response:
                                await thinking_msg.edit(content=response)
                            else:
                                await thinking_msg.edit(content="Sorry, I couldn't process your request. 😕")

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