from abc import ABC, abstractmethod
import requests
from django.conf import settings
from .models import Integration, GuruType
import logging

logger = logging.getLogger(__name__)

class IntegrationStrategy(ABC):
    def __init__(self, integration: 'Integration' = None):
        self.integration = integration

    def get_integration(self) -> 'Integration':
        """Helper method to get an integration instance"""
        if self.integration:
            return self.integration
        else:
            raise ValueError("No integration found")

    @abstractmethod
    def exchange_token(self, code: str) -> dict:
        """Exchange authorization code for access token"""
        pass

    @abstractmethod
    def get_external_id(self, token_response: dict) -> str:
        """Get external user/team ID from the platform"""
        pass

    @abstractmethod
    def list_channels(self) -> list:
        """List available channels"""
        pass

    @abstractmethod
    def get_workspace_name(self, token_response: dict) -> str:
        """Get workspace name from the platform"""
        pass

    @abstractmethod
    def send_test_message(self, channel_id: str) -> bool:
        """Send a test message to the specified channel"""
        pass

    @abstractmethod
    def revoke_access_token(self) -> None:
        """Revoke the OAuth access token"""
        pass

    @abstractmethod
    def refresh_access_token(self, refresh_token: str) -> dict:
        """Refresh the OAuth access token using the refresh token.
        Returns a dict with new access_token and optionally new refresh_token."""
        pass

    def handle_token_refresh(self) -> str:
        """Handle token refresh for an integration. Returns the new access token."""
        integration = self.get_integration()
        try:
            if not integration.refresh_token:
                raise ValueError("No refresh token available")
                
            token_data = self.refresh_access_token(integration.refresh_token)
            integration.access_token = token_data['access_token']
            if 'refresh_token' in token_data:
                integration.refresh_token = token_data['refresh_token']
            integration.save()
            
            return integration.access_token
        except Exception as e:
            logger.error(f"Failed to refresh token: {e}", exc_info=True)
            raise

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
        workspace_name = self.get_workspace_name(token_data)
        
        return Integration.objects.create(
            type=self.get_type(),
            external_id=external_id,
            guru_type=guru_type,
            access_token=access_token,
            refresh_token=refresh_token,
            code=code,
            workspace_name=workspace_name
        )

    @abstractmethod
    def get_type(self) -> str:
        """Get integration type"""
        pass

    def handle_api_call(self, api_func: callable, *args, **kwargs):
        """Helper method to handle API calls with token refresh logic."""
        integration = self.get_integration()
        try:
            return api_func(*args, **kwargs)
        except Exception as e:
            if settings.ENV == 'selfhosted':
                raise
            # Check if it's a token-related error
            error_msg = str(e).lower()
            if any(err in error_msg for err in ['token_expired', 'invalid_auth', 'unauthorized', 'not_authed', '401']):
                try:
                    # Try to refresh the token
                    self.handle_token_refresh()
                    # Retry with new token
                    return api_func(*args, **kwargs)
                except Exception as refresh_error:
                    logger.error(f"Error refreshing token: {refresh_error}", exc_info=True)
                    raise
            raise


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
            logger.error(f"Discord API error: {response.text}")
            raise ValueError(f"Discord API error: {response.text}")
        return response.json()

    def get_external_id(self, token_response: dict) -> str:
        guild_id = token_response.get('guild', {}).get('id')
        if not guild_id:
            raise ValueError("No guild ID found in the OAuth response")
        return guild_id
    
    def get_workspace_name(self, token_response: dict) -> str:
        return token_response.get('guild', {}).get('name')

    def list_channels(self) -> list:
        def _list_channels() -> list:
            integration = self.get_integration()
            channels_response = requests.get(
                f'https://discord.com/api/guilds/{integration.external_id}/channels',
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
            return sorted(text_channels, key=lambda x: x['name'])

        return self.handle_api_call(_list_channels)

    def get_type(self) -> str:
        return 'DISCORD'

    def send_test_message(self, channel_id: str) -> bool:
        def _send_test_message() -> bool:
            url = f'https://discord.com/api/channels/{channel_id}/messages'
            headers = {'Authorization': f'Bot {settings.DISCORD_BOT_TOKEN}'}
            data = {
                'content': '👋 Hello! This is a test message from your Guru. I am working correctly!'
            }
            response = requests.post(url, headers=headers, json=data)
            response.raise_for_status()
            return True

        try:
            return self.handle_api_call(_send_test_message)
        except Exception as e:
            logger.error(f"Error sending Discord test message: {e}", exc_info=True)
            return False

    def revoke_access_token(self) -> None:
        """Revoke Discord OAuth token."""
        def _revoke_token() -> None:
            integration = self.get_integration()
            token_url = 'https://discord.com/api/oauth2/token/revoke'
            headers = {
                'Content-Type': 'application/x-www-form-urlencoded'
            }
            data = {
                'client_id': settings.DISCORD_CLIENT_ID,
                'client_secret': settings.DISCORD_CLIENT_SECRET,
                'token': integration.access_token
            }
            response = requests.post(token_url, headers=headers, data=data)
            response.raise_for_status()

        return self.handle_api_call(_revoke_token)

    def refresh_access_token(self, refresh_token: str) -> dict:
        """Refresh Discord OAuth token."""
        try:
            token_url = 'https://discord.com/api/oauth2/token'
            data = {
                'client_id': settings.DISCORD_CLIENT_ID,
                'client_secret': settings.DISCORD_CLIENT_SECRET,
                'grant_type': 'refresh_token',
                'refresh_token': refresh_token
            }
            response = requests.post(token_url, data=data)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error refreshing Discord token: {e}", exc_info=True)
            raise


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

    def get_external_id(self, token_response: dict) -> str:
        return token_response.get('team', {}).get('id')

    def get_workspace_name(self, token_response: dict) -> str:
        return token_response.get('team', {}).get('name')

    def list_channels(self) -> list:
        def _list_channels() -> list:
            integration = self.get_integration()
            channels = []
            cursor = None
            
            while True:
                params = {
                    'limit': 100,
                    'types': 'public_channel,private_channel',  # Include both public and private channels
                    'exclude_archived': True
                }
                if cursor:
                    params['cursor'] = cursor
                    
                response = requests.get(
                    'https://slack.com/api/conversations.list',
                    headers={'Authorization': f"Bearer {integration.access_token}"},
                    params=params
                )
                response.raise_for_status()
                data = response.json()
                
                if not data.get('ok', False):
                    logger.error(f"Slack API error: {data}")
                    raise ValueError(f"Slack API error: {data.get('error')}")
                    
                channels.extend([
                    {
                        'id': c['id'],
                        'name': c['name'],
                        'allowed': False
                    }
                    for c in data.get('channels', [])
                ])
                
                cursor = data.get('response_metadata', {}).get('next_cursor')
                if not cursor:
                    break
                    
            return sorted(channels, key=lambda x: x['name'])

        return self.handle_api_call(_list_channels)

    def get_type(self) -> str:
        return 'SLACK'

    def send_test_message(self, channel_id: str) -> bool:
        def _send_test_message() -> bool:
            integration = self.get_integration()
            from slack_sdk import WebClient
            client = WebClient(token=integration.access_token)
            response = client.chat_postMessage(
                channel=channel_id,
                text="👋 Hello! This is a test message from your Guru. I am working correctly!"
            )
            return response["ok"]

        try:
            return self.handle_api_call(_send_test_message)
        except Exception as e:
            logger.error(f"Error sending Slack test message: {e}", exc_info=True)
            return False

    def revoke_access_token(self) -> None:
        def _revoke_token() -> None:
            integration = self.get_integration()
            revoke_url = 'https://slack.com/api/auth.revoke'
            headers = {
                'Authorization': f'Bearer {integration.access_token}'
            }
            response = requests.get(revoke_url, headers=headers)
            response_data = response.json()
            
            if not response_data.get('ok', False):
                logger.error(f"Slack API error: {response_data}")
                raise ValueError(f"Slack API error: {response_data.get('error')}")

        return self.handle_api_call(_revoke_token)

    def refresh_access_token(self, refresh_token: str) -> dict:
        """Refresh Slack OAuth token.
        Note: Slack's OAuth 2.0 tokens don't expire and don't need refresh tokens.
        This is implemented for consistency with the interface."""
        raise NotImplementedError("Slack tokens don't expire and can't be refreshed")


class IntegrationFactory:
    @staticmethod
    def get_strategy(integration_type: str, integration: 'Integration' = None) -> IntegrationStrategy:
        integration_type = integration_type.upper()
        if integration_type == 'DISCORD':
            return DiscordStrategy(integration)
        elif integration_type == 'SLACK':
            return SlackStrategy(integration)
        else:
            raise ValueError(f'Invalid integration type: {integration_type}') 