from abc import ABC, abstractmethod
import re
import requests
from django.conf import settings
from .models import Integration, GuruType
import logging

logger = logging.getLogger(__name__)

class IntegrationError(Exception):
    pass

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
    def fetch_workspace_details(self, bot_token: str) -> dict:
        """Fetch workspace details using bot token in selfhosted mode"""
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
            logger.error(f"Integration for {self.get_type()} with ID {external_id} already exists")
            raise IntegrationError(f"This integration type is already connected to this guru. Please disconnect the existing integration before connecting a new one.")
        
        # Fetch available channels
        workspace_name = self.get_workspace_name(token_data)
        
        try:
            return Integration.objects.create(
                type=self.get_type(),
                external_id=external_id,
                guru_type=guru_type,
                access_token=access_token,
                refresh_token=refresh_token,
                code=code,
                workspace_name=workspace_name
            )
        except Exception as e:
            logger.error(f"Error creating integration: {e}", exc_info=True)
            raise IntegrationError(f"Error creating integration. Please try again. If the problem persists, please contact support.")

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
    def _get_bot_token(self, integration=None) -> str:
        """Helper to get the appropriate bot token based on environment"""
        if settings.ENV == 'selfhosted':
            integration = integration or self.get_integration()
            return integration.access_token
        return settings.DISCORD_BOT_TOKEN

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
                headers={'Authorization': f"Bot {self._get_bot_token(integration)}"}
            )
            channels_response.raise_for_status()
            channels = channels_response.json()
            
            # Only include text channels
            text_channels = [
                {
                    'id': c['id'],
                    'name': c['name'],
                    'allowed': False,
                    'type': 'text' if c['type'] == 0 else 'forum' if c['type'] == 15 else 'unknown'
                }
                for c in channels
                if c['type'] in [0, 15]  # 0 is text channel, 15 is forum
            ]
            return sorted(text_channels, key=lambda x: x['name'])

        return self.handle_api_call(_list_channels)

    def get_type(self) -> str:
        return 'DISCORD'

    def send_test_message(self, channel_id: str) -> bool:
        def _send_test_message() -> bool:
            integration = self.get_integration()
            
            # Find the channel type from integration.channels
            channel_type = 'text'  # default to text
            for channel in integration.channels:
                if channel['id'] == channel_id:
                    channel_type = channel.get('type', 'text')
                    break

            url = f'https://discord.com/api/channels/{channel_id}'
            headers = {'Authorization': f'Bot {self._get_bot_token(integration)}'}
            
            if channel_type == 'forum':
                # Create a forum post
                url += '/threads'
                data = {
                    'name': 'Test Message from Gurubase',
                    'message': {
                        'content': '👋 Hello! This is a test message from your Guru. I am working correctly!'
                    }
                }
            else:
                # Regular text channel message
                url += '/messages'
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

    def fetch_workspace_details(self, bot_token: str) -> dict:
        """Fetch Discord guild details using bot token"""
        response = requests.get(
            'https://discord.com/api/v10/users/@me/guilds',
            headers={
                'Authorization': f'Bot {bot_token}',
                'Content-Type': 'application/json'
            }
        )
        response.raise_for_status()
        guilds = response.json()
        
        if not guilds:
            raise ValueError("No guilds found for the bot")
            
        # For selfhosted, we'll use the first guild the bot has access to
        guild = guilds[0]
        return {
            'external_id': guild['id'],
            'workspace_name': guild['name']
        }


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

    def fetch_workspace_details(self, bot_token: str) -> dict:
        """Fetch Slack workspace details using bot token"""
        response = requests.post(
            'https://slack.com/api/auth.test',
            headers={
                'Authorization': f'Bearer {bot_token}'
            }
        )
        response.raise_for_status()
        data = response.json()
        
        if not data.get('ok', False):
            raise ValueError(f"Slack API error: {data.get('error')}")
            
        return {
            'external_id': data['team_id'],
            'workspace_name': data['team']
        }


class GitHubStrategy(IntegrationStrategy):
    def __init__(self, integration: 'Integration' = None):
        from .github_handler import GithubAppHandler
        super().__init__(integration)
        self.github_handler = GithubAppHandler()

    def _fetch_repositories(self, installation_id: str) -> list:
        """Fetch repositories for a GitHub installation"""
        try:
            return self.github_handler.fetch_repositories(installation_id)
        except Exception as e:
            logger.error(f"Error fetching GitHub repositories: {e}", exc_info=True)
            return []
        
    def _fetch_installation(self, installation_id: str) -> dict:
        """Fetch installation details for a GitHub installation"""
        try:
            return self.github_handler.get_installation(installation_id)
        except Exception as e:
            logger.error(f"Error fetching GitHub installation: {e}", exc_info=True)
            return {}

    def exchange_token(self, code: str) -> dict:
        """For GitHub, we don't exchange a code. Instead, we use the installation_id as the external_id."""
        raise NotImplementedError("GitHub integration does not use code exchange")

    def get_external_id(self, token_response: dict) -> str:
        """For GitHub, the external_id is the installation_id"""
        return token_response.get('installation_id')

    def get_workspace_name(self, installation_id: str) -> str:
        """For GitHub, we use the repository names as the workspace name"""
        installation = self._fetch_installation(installation_id)
        if not installation:
            return f"GitHub Installation {installation_id}"
            
        return installation.get('account', {}).get('login')

    def list_channels(self, installation_id: str = None) -> list:
        """For GitHub, we return repositories as channels"""
        repo_names = self._fetch_repositories(installation_id or self.get_integration().external_id)
        return [{'id': name, 'name': name, 'mode': 'auto'} for name in repo_names]

    def send_test_message(self, channel_id: str) -> bool:
        """GitHub doesn't support test messages"""
        return True

    def revoke_access_token(self) -> None:
        """Delete the installation"""
        integration = self.get_integration()
        self.github_handler.delete_installation(integration.external_id)

    def refresh_access_token(self, refresh_token: str) -> dict:
        """GitHub doesn't support token refresh"""
        raise NotImplementedError("GitHub tokens don't expire and can't be refreshed")

    def fetch_workspace_details(self, bot_token: str) -> dict:
        """For GitHub, we use the installation_id as both external_id and workspace name"""
        installation = self._fetch_installation(bot_token)
        workspace_name = installation.get('account', {}).get('login')
        if not workspace_name:
            workspace_name = f"GitHub Installation {bot_token}"
        
        return {
            'external_id': bot_token,  # bot_token is actually installation_id in this case
            'workspace_name': workspace_name
        }

    def get_type(self) -> str:
        return 'GITHUB'

    def create_integration(self, installation_id: str, guru_type: GuruType) -> Integration:
        """Create GitHub integration with the installation ID"""
        # Check if integration already exists for this type and external_id
        if Integration.objects.filter(type=self.get_type(), external_id=installation_id).exists():
            logger.error(f"Integration for {self.get_type()} with ID {installation_id} already exists")
            raise IntegrationError(f"This integration type is already connected to this guru. Please disconnect the existing integration before connecting a new one.")
        
        try:
            # Fetch repository names for workspace name
            workspace_name = self.get_workspace_name(installation_id)
            channels = self.list_channels(installation_id)
            
            return Integration.objects.create(
                type=self.get_type(),
                external_id=installation_id,
                guru_type=guru_type,
                access_token=installation_id,  # For GitHub, we use installation_id as the access_token
                workspace_name=workspace_name,
                channels=channels
            )
        except Exception as e:
            logger.error(f"Error creating GitHub integration: {e}", exc_info=True)
            raise IntegrationError(f"Error creating GitHub integration. Please try again. If the problem persists, please contact support.")


class IntegrationFactory:
    @staticmethod
    def get_strategy(integration_type: str, integration: 'Integration' = None) -> IntegrationStrategy:
        integration_type = integration_type.upper()
        if integration_type == 'DISCORD':
            return DiscordStrategy(integration)
        elif integration_type == 'SLACK':
            return SlackStrategy(integration)
        elif integration_type == 'GITHUB':
            return GitHubStrategy(integration)
        else:
            raise ValueError(f'Invalid integration type: {integration_type}')

class NotEnoughData(Exception):
    pass

class NotRelated(Exception):
    pass

def strip_first_header(content: str) -> str:
    """Remove the first header (starting with # and ending with newline) from content."""
    if content.startswith('#'):
        # Find the first newline
        newline_index = content.find('\n')
        if newline_index != -1:
            # Return content after the newline
            return content[newline_index + 1:].lstrip()
    return content

def get_trust_score_emoji(trust_score: int) -> str:
    if trust_score >= 80:
        return "🟢"
    elif trust_score >= 60:
        return "🟡"
    elif trust_score >= 40:
        return "🟡"
    elif trust_score >= 20:
        return "🟠"
    else:
        return "🔴"

def cleanup_title(title: str) -> str:
    """Clean up the title of a repository"""
    clean_title = re.sub(r'\s*:[a-zA-Z0-9_+-]+:\s*', ' ', title)
    clean_title = re.sub(
        r'\s*(?:[\u2600-\u26FF\u2700-\u27BF\U0001F300-\U0001F9FF\U0001FA70-\U0001FAFF]'
        r'[\uFE00-\uFE0F\U0001F3FB-\U0001F3FF]?\s*)+',
        ' ',
        clean_title
    ).strip()

    clean_title = ' '.join(clean_title.split())

    return clean_title