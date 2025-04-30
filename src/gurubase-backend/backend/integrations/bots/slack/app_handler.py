import logging
from django.conf import settings
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

logger = logging.getLogger(__name__)

class SlackAppHandler:
    def __init__(self, integration=None):
        self.integration = integration
        self.client = WebClient(token=integration.access_token) if integration else None

    def get_thread_messages(self, channel_id: str, thread_ts: str, max_length: int = settings.GITHUB_CONTEXT_CHAR_LIMIT) -> list:
        """Get messages in a thread until max_length is reached, prioritizing recent messages."""
        try:
            all_messages = []
            cursor = None
            
            # First, fetch all messages
            while True:
                params = {
                    'channel': channel_id,
                    'ts': thread_ts,
                    'limit': 100
                }
                if cursor:
                    params['cursor'] = cursor
                    
                response = self.client.conversations_replies(**params)
                
                if not response["ok"]:
                    raise SlackApiError(f"Error fetching thread messages: {response.get('error')}")
                
                all_messages.extend(response["messages"])
                
                cursor = response.get('response_metadata', {}).get('next_cursor')
                if not cursor:
                    break
            
            # Sort messages by timestamp in descending order (newest first)
            all_messages.sort(key=lambda x: float(x.get('ts', 0)), reverse=True)
            
            # Now process the sorted messages
            messages = []
            total_length = 0
            
            for msg in all_messages:
                # Format message
                formatted_msg = self._format_single_message(msg)
                msg_length = len(formatted_msg)
                
                # Check if adding this message would exceed the limit
                if total_length + msg_length > max_length:
                    return messages
                    
                messages.append(formatted_msg)
                total_length += msg_length
                    
            return messages
            
        except SlackApiError as e:
            logger.error(f"Error fetching thread messages: {e}", exc_info=True)
            raise e

    def get_channel_messages(self, channel_id: str, max_length: int = settings.GITHUB_CONTEXT_CHAR_LIMIT) -> list:
        """Get recent messages from a channel until max_length is reached."""
        try:
            messages = []
            total_length = 0
            cursor = None
            
            while True:
                params = {
                    'channel': channel_id,
                    'limit': 100
                }
                if cursor:
                    params['cursor'] = cursor
                    
                response = self.client.conversations_history(**params)
                
                if not response["ok"]:
                    raise SlackApiError(f"Error fetching channel messages: {response.get('error')}")
                
                # Process messages and check length
                for msg in response["messages"]:
                    # Skip bot messages
                    if msg.get('bot_id'):
                        continue
                        
                    # Format message
                    formatted_msg = self._format_single_message(msg)
                    msg_length = len(formatted_msg)
                    
                    # Check if adding this message would exceed the limit
                    if total_length + msg_length > max_length:
                        return messages
                        
                    messages.append(formatted_msg)
                    total_length += msg_length
                
                cursor = response.get('response_metadata', {}).get('next_cursor')
                if not cursor:
                    break
                    
            return messages
            
        except SlackApiError as e:
            logger.error(f"Error fetching channel messages: {e}", exc_info=True)
            raise e

    def _format_single_message(self, msg: dict) -> str:
        """Format a single message with user info."""
        # user = msg.get('user', '')
        text = msg.get('text', '')
        return f"<Slack message>\nMessage: {text}\n</Slack message>\n"

    def format_messages(self, messages: list) -> str:
        """Format messages with user info and timestamps."""
        formatted_messages = []
        
        for msg in messages:
            # Get user info
            # user = msg.get('user', '')
            text = msg.get('text', '')
            
            # Format the message
            formatted_msg = f"<Slack message>\nMessage: {text}\n</Slack message>\n"
            formatted_messages.append(formatted_msg)
            
        return '\n'.join(formatted_messages)

    def limit_messages_by_length(self, messages: list, max_length: int = settings.GITHUB_CONTEXT_CHAR_LIMIT) -> list:
        """Limit messages by total character length."""
        total_length = 0
        limited_messages = []
        
        for msg in messages:
            msg_length = len(msg)
            if total_length + msg_length > max_length:
                break
            limited_messages.append(msg)
            total_length += msg_length
            
        return limited_messages 

    def format_comments_for_prompt(self, messages: list) -> str:
        """Format comments for the prompt."""
        return self.format_messages(messages)