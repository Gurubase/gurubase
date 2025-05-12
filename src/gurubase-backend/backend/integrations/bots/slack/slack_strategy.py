import logging
import time
from django.conf import settings
import requests

from core.exceptions import ThrottleError
from integrations.bots.models import BotContext
from integrations.strategy import IntegrationContextHandler, IntegrationStrategy
from .app_handler import SlackAppHandler

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
            channels = integration.channels
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

    def validate_channel(self, channel_id: str) -> dict:
        """Validate a single channel ID and return its details.
        
        Args:
            channel_id: Channel ID to validate
            
        Returns:
            dict: {
                'success': bool,
                'data': {
                    'id': str,
                    'name': str,
                    'allowed': bool,
                    'mode': str
                } | None,
                'error': str | None
            }
        """
        def _validate_channel() -> dict:
            integration = self.get_integration()
            from slack_sdk import WebClient
            client = WebClient(token=integration.access_token)
            
            try:
                # Get channel info
                response = client.conversations_info(channel=channel_id)
                if response["ok"]:
                    channel = response["channel"]
                    return {
                        'success': True,
                        'data': {
                            'id': channel['id'],
                            'name': channel['name'],
                            'allowed': True,
                            'mode': 'manual'
                        },
                        'error': None
                    }
                else:
                    return {
                        'success': False,
                        'data': None,
                        'error': response.get('error', 'Unknown error')
                    }
            except Exception as e:
                return {
                    'success': False,
                    'data': None,
                    'error': str(e)
                }

        try:
            return self.handle_api_call(_validate_channel)
        except Exception as e:
            logger.error(f"Error validating Slack channel {channel_id}: {e}", exc_info=True)
            return {
                'success': False,
                'data': None,
                'error': str(e)
            }


class SlackContextHandler(IntegrationContextHandler):
    """Handler for Slack integration context."""
    
    def get_context(self, api_url: str, external_id: str) -> BotContext:
        try:
            # Get channel_id and thread_ts from api_url
            # api_url format: channel_id:thread_ts
            channel_id, thread_ts = api_url.split(':')
            
            # Initialize Slack app handler
            slack_handler = SlackAppHandler(self.integration)
            
            # First get thread messages if in a thread
            if thread_ts:
                thread_messages = slack_handler.get_thread_messages(channel_id, thread_ts)
            
            # # If we haven't exceeded the limit, get channel messages
            # length = sum(len(msg) for msg in thread_messages)
            # if length < settings.GITHUB_CONTEXT_CHAR_LIMIT:  # If we got less than char limit
            #     channel_messages = slack_handler.get_channel_messages(channel_id, max_length=settings.GITHUB_CONTEXT_CHAR_LIMIT - length)
            # else:
            #     channel_messages = []
            
            return BotContext(
                type=BotContext.Type.SLACK,
                data={'thread_messages': list(reversed(thread_messages))}
            )
            
        except Exception as e:
            logger.error(f"Error getting Slack context: {e}", exc_info=True)
            return None
