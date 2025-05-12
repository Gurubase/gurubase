import logging
from django.conf import settings
import requests

logger = logging.getLogger(__name__)

class DiscordAppHandler:
    def __init__(self, integration=None):
        self.integration = integration
        self.base_url = "https://discord.com/api/v10"
        self.headers = self._get_headers()

    def _get_headers(self) -> dict:
        """Get headers with appropriate bot token based on environment"""
        if settings.ENV != 'selfhosted':
            return {"Authorization": f"Bot {settings.DISCORD_BOT_TOKEN}"}
        
        # In selfhosted mode, use the integration's token
        if self.integration and self.integration.access_token:
            return {"Authorization": f"Bot {self.integration.access_token}"}
            
        raise ValueError("No valid bot token available")
    

    def get_thread_messages(self, thread_id: str, max_length: int = settings.GITHUB_CONTEXT_CHAR_LIMIT) -> list:
        """Get messages in a thread until max_length is reached."""
        try:
            messages = []
            total_length = 0
            
            # Discord API returns messages in descending order (newest first)
            response = requests.get(
                f"{self.base_url}/channels/{thread_id}/messages?limit=100",
                headers=self.headers
            )
            
            if response.status_code != 200:
                raise Exception(f"Error fetching thread messages: {response.text}")
            
            # Process messages and check length
            for msg in response.json():
                # Format message
                if not msg['content']:
                    continue
                formatted_msg = self._format_single_message(msg)
                msg_length = len(formatted_msg)
                
                # Check if adding this message would exceed the limit
                if total_length + msg_length > max_length:
                    return messages
                    
                messages.append(formatted_msg)
                total_length += msg_length
                    
            return messages
            
        except Exception as e:
            logger.error(f"Error fetching thread messages: {e}", exc_info=True)
            raise e

    def get_channel_messages(self, channel_id: str, max_length: int = settings.GITHUB_CONTEXT_CHAR_LIMIT) -> list:
        """Get recent messages from a channel until max_length is reached."""
        try:
            messages = []
            total_length = 0
            
            # Discord API returns messages in descending order (newest first)
            response = requests.get(
                f"{self.base_url}/channels/{channel_id}/messages?limit=100",
                headers=self.headers
            )
            
            if response.status_code != 200:
                raise Exception(f"Error fetching channel messages: {response.text}")
            
            # Process messages and check length
            for msg in response.json():
                # Skip bot messages
                if msg.get('author', {}).get('bot'):
                    continue
                    
                # Format message
                formatted_msg = self._format_single_message(msg)
                msg_length = len(formatted_msg)
                
                # Check if adding this message would exceed the limit
                if total_length + msg_length > max_length:
                    return messages
                    
                messages.append(formatted_msg)
                total_length += msg_length
                    
            return messages
            
        except Exception as e:
            logger.error(f"Error fetching channel messages: {e}", exc_info=True)
            raise e

    def _format_single_message(self, msg: dict) -> str:
        """Format a single message with user info."""
        author = msg.get('author', {})
        username = author.get('username', '')
        content = msg.get('content', '')
        return f"<Discord message>\nUser: {username}\nMessage: {content}\n</Discord message>\n"

    def format_messages(self, messages: list) -> str:
        """Format messages with user info and timestamps."""
        formatted_messages = []
        
        for msg in messages:
            # Get user info
            author = msg.get('author', {})
            username = author.get('username', '')
            content = msg.get('content', '')
            
            # Format the message
            formatted_msg = f"<Discord message>\nUser: {username}\nMessage: {content}\n</Discord message>\n"
            formatted_messages.append(formatted_msg)
            
        return '\n'.join(formatted_messages)

    def format_comments_for_prompt(self, messages: list) -> str:
        """Format comments for the prompt."""
        return self.format_messages(messages)

    def get_initial_thread_message(self, parent_channel_id: str, message_id: str, max_length: int = settings.GITHUB_CONTEXT_CHAR_LIMIT) -> str:
        """Get the initial message that started the thread."""
        try:
            response = requests.get(
                f"{self.base_url}/channels/{parent_channel_id}/messages/{message_id}",
                headers=self.headers
            )
            
            if response.status_code != 200:
                raise Exception(f"Error fetching initial thread message: {response.text}")
            
            msg = response.json()
            formatted_msg = self._format_single_message(msg)
            
            # Only return if within length limit
            if len(formatted_msg) <= max_length:
                return formatted_msg
            return ""
            
        except Exception as e:
            logger.error(f"Error fetching initial thread message: {e}", exc_info=True)
            raise e 