import logging
from django.conf import settings
import requests

from integrations.bots.models import BotContext
from integrations.strategy import IntegrationContextHandler, IntegrationStrategy

logger = logging.getLogger(__name__)

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


class SlackContextHandler(IntegrationContextHandler):
    """Handler for Slack integration context."""
    
    def get_context(self, api_url: str, external_id: str) -> BotContext:
        # TODO: Implement actual Slack context gathering
        # This is a mock implementation
        try:
            # Mock implementation would:
            # 1. Get thread messages using Slack API
            # 2. Format messages with user info and timestamps
            # 3. Limit context by length
            return BotContext(
                type=BotContext.Type.SLACK,
                data="Mock Slack message 1\nMock Slack message 2"
            )
        except Exception as e:
            logger.error(f"Error getting Slack context: {e}", exc_info=True)
            return None
