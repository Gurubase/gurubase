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
            channels = []
            cursor = None

            max_retries = 3
            base_delay = 1

            while True:
                params = {
                    'limit': 200,
                    'types': 'public_channel,private_channel',  # Include both public and private channels
                    'exclude_archived': True
                }
                if cursor:
                    params['cursor'] = cursor
                
                retry_count = 0
                data = None
                while retry_count < max_retries:
                    try:
                        response = requests.get(
                            'https://slack.com/api/conversations.list',
                            headers={'Authorization': f"Bearer {integration.access_token}"},
                            params=params
                        )
                        
                        # Check for rate limiting
                        if response.status_code in [429, 503]:
                            retry_after = int(response.headers.get('Retry-After', base_delay * (2 ** retry_count)))
                            logger.warning(f"Rate limited by Slack API. Waiting {retry_after} seconds before retry.")
                            time.sleep(retry_after)
                            retry_count += 1
                            continue
                            
                        response.raise_for_status()
                        data = response.json()
                        
                        if not data.get('ok', False):
                            error = data.get('error')
                            if error == 'ratelimited':
                                retry_after = int(response.headers.get('Retry-After', base_delay * (2 ** retry_count)))
                                logger.warning(f"Rate limited by Slack API. Waiting {retry_after} seconds before retry.")
                                time.sleep(retry_after)
                                retry_count += 1
                                continue
                            else:
                                logger.error(f"Slack API error: {data}")
                                raise ValueError(f"Slack API error: {error}")
                        
                        # If we get here, the request was successful
                        break
                        
                    except requests.exceptions.RequestException as e:
                        if retry_count == max_retries - 1:
                            raise
                        retry_count += 1
                        time.sleep(base_delay * (2 ** retry_count))
                        continue

                if not data:
                    raise ThrottleError("Slack API rate limit exceeded. Too many requests.")
                
                channels.extend([
                    {
                        'id': c['id'],
                        'name': c['name'],
                        'allowed': False,
                        'mode': 'manual',
                        'direct_messages': False
                    }
                    for c in data.get('channels', [])
                ])
            
                cursor = data.get('response_metadata', {}).get('next_cursor')
                if not cursor:
                    break

                time.sleep(3)
                    
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
