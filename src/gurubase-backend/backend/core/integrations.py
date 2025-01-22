from abc import ABC, abstractmethod
import requests
from django.conf import settings
from .models import Integration, GuruType

class IntegrationStrategy(ABC):
    @abstractmethod
    def exchange_token(self, code: str) -> dict:
        """Exchange authorization code for access token"""
        pass

    @abstractmethod
    def get_external_id(self, access_token: str) -> str:
        """Get external user/team ID from the platform"""
        pass

    @abstractmethod
    def list_channels(self, access_token: str) -> list:
        """List available channels"""
        pass

    def create_integration(self, code: str, guru_type: GuruType) -> Integration:
        """Create integration with the platform"""
        token_data = self.exchange_token(code)
        access_token = token_data.get('access_token')
        refresh_token = token_data.get('refresh_token')
        external_id = self.get_external_id(token_data)
        
        # Check if integration already exists for this type and external_id
        if Integration.objects.filter(type=self.get_type(), external_id=external_id).exists():
            raise ValueError(f"Integration for {self.get_type()} with ID {external_id} already exists")
        
        # Fetch available channels
        channels = self.list_channels(external_id)
        
        return Integration.objects.create(
            type=self.get_type(),
            external_id=external_id,
            guru_type=guru_type,
            access_token=access_token,
            refresh_token=refresh_token,
            code=code,
            channels=channels
        )

    @abstractmethod
    def get_type(self) -> str:
        """Get integration type"""
        pass


class DiscordStrategy(IntegrationStrategy):
    def exchange_token(self, code: str) -> dict:
        token_url = 'https://discord.com/api/oauth2/token'
        data = {
            'client_id': settings.DISCORD_CLIENT_ID,
            'client_secret': settings.DISCORD_CLIENT_SECRET,
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': settings.DISCORD_REDIRECT_URI
        }
        response = requests.post(token_url, data=data)
        if not response.ok:
            raise ValueError(f"Discord API error: {response.text}")
        return response.json()

    def get_external_id(self, token_response: str) -> str:
        guild_id = token_response.get('guild', {}).get('id')
        if not guild_id:
            raise ValueError("No guild ID found in the OAuth response")
        return guild_id

    def list_channels(self, external_id: str) -> list:
        # First get the guild ID from the token response
        guild_id = external_id
        # For each guild, get its channels
        all_channels = []
        channels_response = requests.get(
            f'https://discord.com/api/guilds/{guild_id}/channels',
            headers={'Authorization': f"Bot {settings.DISCORD_BOT_TOKEN}"}
        )
        channels_response.raise_for_status()
        channels = channels_response.json()
        
        # Only include text channels
        text_channels = [
            {
                'id': c['id'],
                'name': c['name'],
                'allowed': False
            }
            for c in channels
            if c['type'] == 0  # 0 is text channel
        ]
        all_channels.extend(text_channels)
            
        return all_channels

    def get_type(self) -> str:
        return 'DISCORD'


class SlackStrategy(IntegrationStrategy):
    def exchange_token(self, code: str) -> dict:
        token_url = 'https://slack.com/api/oauth.v2.access'
        data = {
            'client_id': settings.SLACK_CLIENT_ID,
            'client_secret': settings.SLACK_CLIENT_SECRET,
            'code': code
        }
        response = requests.post(token_url, data=data)
        response.raise_for_status()
        return response.json()

    def get_external_id(self, access_token: str) -> str:
        # For Slack, we get the team ID from the token exchange response
        # So we'll pass it through the access_token parameter
        return access_token.split(':')[0]  # team_id is the first part

    def list_channels(self, access_token: str) -> list:
        channels = []
        cursor = None
        
        while True:
            params = {'limit': 100}
            if cursor:
                params['cursor'] = cursor
                
            response = requests.get(
                'https://slack.com/api/conversations.list',
                headers={'Authorization': f"Bearer {access_token}"},
                params=params
            )
            response.raise_for_status()
            data = response.json()
            
            if not data.get('ok', False):
                raise ValueError(f"Slack API error: {data.get('error')}")
                
            channels.extend([
                {
                    'id': c['id'],
                    'name': c['name'],
                    'is_private': c['is_private'],
                    'is_archived': c['is_archived']
                }
                for c in data.get('channels', [])
            ])
            
            cursor = data.get('response_metadata', {}).get('next_cursor')
            if not cursor:
                break
                
        return channels

    def get_type(self) -> str:
        return 'SLACK'


class IntegrationFactory:
    @staticmethod
    def get_strategy(integration_type: str) -> IntegrationStrategy:
        if integration_type == 'DISCORD':
            return DiscordStrategy()
        elif integration_type == 'SLACK':
            return SlackStrategy()
        else:
            raise ValueError(f'Invalid integration type: {integration_type}') 