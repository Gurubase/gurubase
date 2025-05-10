from abc import ABC, abstractmethod
from django.conf import settings
from typing import List, Optional, Dict, Any
from core.utils import APIType

from integrations.bots.helpers import IntegrationError
from integrations.models import Integration
from core.models import GuruType

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
    def list_channels(self, installation_id: str = None, client_id: str = None, private_key: str = None) -> list:
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

class IntegrationContextHandler(ABC):
    """Abstract base class for handling integration-specific context gathering."""
    
    def __init__(self, integration: Any):
        self.integration = integration
    
    @abstractmethod
    def get_context(self, api_url: str, external_id: str) -> Optional[List[str]]:
        """
        Get context from the integration.
        
        Args:
            api_url: The API URL for the integration
            external_id: The external ID (e.g. issue number, thread ID)
            
        Returns:
            List of context strings or None if no context available
        """
        pass


def get_context_handler(api_type: APIType, integration: Any) -> Optional[IntegrationContextHandler]:
    """
    Factory function to get the appropriate context handler.
    
    Args:
        api_type: The type of API (e.g. APIType.GITHUB, APIType.SLACK, APIType.DISCORD)
        integration: The integration object
        
    Returns:
        An instance of the appropriate IntegrationContextHandler or None
    """
    from integrations.bots.discord.discord_strategy import DiscordContextHandler
    from integrations.bots.github.github_strategy import GithubContextHandler
    from integrations.bots.slack.slack_strategy import SlackContextHandler
    handlers = {
        APIType.GITHUB: GithubContextHandler,
        APIType.SLACK: SlackContextHandler,
        APIType.DISCORD: DiscordContextHandler
    }
    
    handler_class = handlers.get(api_type)
    if handler_class:
        return handler_class(integration)
    return None


