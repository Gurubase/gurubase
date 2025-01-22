import os
import discord
import logging
import sys
from django.core.management.base import BaseCommand
from django.conf import settings
from core.models import Integration
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
                        await message.channel.send('message received')

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