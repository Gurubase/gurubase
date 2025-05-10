from django.core.management.base import BaseCommand
from integrations.bots.discord.discord_listener import DiscordListener

class Command(BaseCommand):
    help = 'Starts a Discord listener bot'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting Discord listener...'))
        listener = DiscordListener()
        listener.run() 