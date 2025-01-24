from abc import ABC, abstractmethod
import requests
from django.conf import settings
from .models import Integration, GuruType
import logging

logger = logging.getLogger(__name__)

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

    @abstractmethod
    def get_workspace_name(self, token_response: dict) -> str:
        """Get workspace name from the platform"""
        pass

    @abstractmethod
    def send_test_message(self, access_token: str, channel_id: str) -> bool:
        """Send a test message to the specified channel"""
        pass

    @abstractmethod
    def revoke_access_token(self, access_token: str) -> None:
        """Revoke the OAuth access token"""
        pass

    @abstractmethod
    def refresh_access_token(self, refresh_token: str) -> dict:
        """Refresh the OAuth access token using the refresh token.
        Returns a dict with new access_token and optionally new refresh_token."""
        pass

    def handle_token_refresh(self, integration: 'Integration') -> str:
        """Handle token refresh for an integration. Returns the new access token."""
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
        channels = self.list_channels(access_token, external_id)
        workspace_name = self.get_workspace_name(token_data)
        
        return Integration.objects.create(
            type=self.get_type(),
            external_id=external_id,
            guru_type=guru_type,
            access_token=access_token,
            refresh_token=refresh_token,
            code=code,
            channels=channels,
            workspace_name=workspace_name
        )

    @abstractmethod
    def get_type(self) -> str:
        """Get integration type"""
        pass

    def handle_api_call(self, integration: 'Integration', api_func: callable, *args, **kwargs):
        """Helper method to handle API calls with token refresh logic.
        
        Args:
            integration: The Integration model instance
            api_func: The function to call that makes the actual API request
            *args, **kwargs: Arguments to pass to the api_func
        """
        try:
            return api_func(integration.access_token, *args, **kwargs)
        except Exception as e:
            # Check if it's a token-related error
            error_msg = str(e).lower()
            if any(err in error_msg for err in ['token_expired', 'invalid_auth', 'unauthorized', 'not_authed', '401']):
                try:
                    # Try to refresh the token
                    new_token = self.handle_token_refresh(integration)
                    # Retry with new token
                    return api_func(new_token, *args, **kwargs)
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
            raise ValueError(f"Discord API error: {response.text}")
        return response.json()

    def get_external_id(self, token_response: str) -> str:
        guild_id = token_response.get('guild', {}).get('id')
        if not guild_id:
            raise ValueError("No guild ID found in the OAuth response")
        return guild_id
    
    def get_workspace_name(self, token_response: dict) -> str:
        return token_response.get('guild', {}).get('name')

    def list_channels(self, access_token: str, external_id: str) -> list:
        def _list_channels(token: str, guild_id: str) -> list:
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
            return text_channels

        return self.handle_api_call(None, _list_channels, external_id)  # Using None since we use bot token

    def get_type(self) -> str:
        return 'DISCORD'

    def send_test_message(self, access_token: str, channel_id: str) -> bool:
        def _send_test_message(token: str, ch_id: str) -> bool:
            url = f'https://discord.com/api/channels/{ch_id}/messages'
            headers = {'Authorization': f'Bot {settings.DISCORD_BOT_TOKEN}'}
            data = {
                'content': '👋 Hello! This is a test message from your Guru. I am working correctly!'
            }
            response = requests.post(url, headers=headers, json=data)
            response.raise_for_status()
            return True

        try:
            return self.handle_api_call(None, _send_test_message, channel_id)  # Using None since we use bot token
        except Exception as e:
            logger.error(f"Error sending Discord test message: {e}", exc_info=True)
            return False

    def revoke_access_token(self, access_token: str) -> None:
        """Revoke Discord OAuth token."""
        try:
            token_url = 'https://discord.com/api/oauth2/token/revoke'
            headers = {
                'Content-Type': 'application/x-www-form-urlencoded'
            }
            data = {
                'client_id': settings.DISCORD_CLIENT_ID,
                'client_secret': settings.DISCORD_CLIENT_SECRET,
                'token': access_token
            }
            response = requests.post(token_url, headers=headers, data=data)
            response.raise_for_status()
        except Exception as e:
            logger.error(f"Error revoking Discord token: {e}", exc_info=True)
            raise

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
        # For Slack, we get the team ID from the token exchange response
        # So we'll pass it through the access_token parameter
        return token_response.get('team', {}).get('id')

    def get_workspace_name(self, token_response: dict) -> str:
        return token_response.get('team', {}).get('name')

    def list_channels(self, access_token: str, external_id: str) -> list:
        def _list_channels(token: str, _: str) -> list:
            channels = []
            cursor = None
            
            while True:
                params = {'limit': 100}
                if cursor:
                    params['cursor'] = cursor
                    
                response = requests.get(
                    'https://slack.com/api/conversations.list',
                    headers={'Authorization': f"Bearer {token}"},
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
                        'allowed': False
                    }
                    for c in data.get('channels', [])
                ])
                
                cursor = data.get('response_metadata', {}).get('next_cursor')
                if not cursor:
                    break
                    
            return channels

        return self.handle_api_call(self, _list_channels, access_token, external_id)

    def get_type(self) -> str:
        return 'SLACK'

    def send_test_message(self, access_token: str, channel_id: str) -> bool:
        def _send_test_message(token: str, ch_id: str) -> bool:
            from slack_sdk import WebClient
            client = WebClient(token=token)
            response = client.chat_postMessage(
                channel=ch_id,
                text="👋 Hello! This is a test message from your Guru. I am working correctly!"
            )
            return response["ok"]

        try:
            return self.handle_api_call(self, _send_test_message, access_token, channel_id)
        except Exception as e:
            logger.error(f"Error sending Slack test message: {e}", exc_info=True)
            return False

    def revoke_access_token(self, access_token: str) -> None:
        def _revoke_token(token: str) -> None:
            revoke_url = 'https://slack.com/api/auth.revoke'
            headers = {
                'Authorization': f'Bearer {token}'
            }
            response = requests.get(revoke_url, headers=headers)
            response_data = response.json()
            
            if not response_data.get('ok', False):
                raise ValueError(f"Slack API error: {response_data.get('error')}")

        return self.handle_api_call(self, _revoke_token)

    def refresh_access_token(self, refresh_token: str) -> dict:
        """Refresh Slack OAuth token.
        Note: Slack's OAuth 2.0 tokens don't expire and don't need refresh tokens.
        This is implemented for consistency with the interface."""
        raise NotImplementedError("Slack tokens don't expire and can't be refreshed")


class IntegrationFactory:
    @staticmethod
    def get_strategy(integration_type: str) -> IntegrationStrategy:
        integration_type = integration_type.upper()
        if integration_type == 'DISCORD':
            return DiscordStrategy()
        elif integration_type == 'SLACK':
            return SlackStrategy()
        else:
            raise ValueError(f'Invalid integration type: {integration_type}') 