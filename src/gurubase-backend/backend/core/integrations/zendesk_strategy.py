import requests
import logging

from core.exceptions import ZendeskAuthenticationError, ZendeskError, ZendeskInvalidDomainError, ZendeskInvalidSubdomainError
from .strategy import IntegrationStrategy
from .helpers import IntegrationError
from core.models import Integration
from core.requester import ZendeskRequester

logger = logging.getLogger(__name__)

class ZendeskStrategy(IntegrationStrategy):
    def get_type(self) -> str:
        return Integration.Type.ZENDESK

    def exchange_token(self, code: str) -> dict:
        # Zendesk uses API Token authentication, not OAuth code exchange in this setup
        raise NotImplementedError("Zendesk integration uses API Token, not OAuth code exchange.")

    def get_external_id(self, token_response: dict) -> str:
        # Not applicable for API Token authentication
        raise NotImplementedError("External ID retrieval not applicable for Zendesk API Token setup.")

    def list_channels(self, installation_id: str = None, client_id: str = None, private_key: str = None) -> list:
        # Zendesk doesn't have a direct equivalent of channels/repos in this context for simple listing.
        # Could potentially list groups or organizations later if needed.
        return []

    def get_workspace_name(self, token_response: dict) -> str:
        # Not applicable for API Token authentication
        raise NotImplementedError("Workspace name retrieval not applicable for Zendesk API Token setup.")

    def fetch_workspace_details(self, zendesk_domain: str, zendesk_user_email: str, zendesk_api_token: str) -> dict:
        """
        Validates Zendesk connection using provided credentials.
        Returns basic workspace details (domain) upon successful validation.
        Raises IntegrationError if validation fails.
        """
        try:
            # Create a temporary integration-like object for the requester
            class TempIntegration:
                def __init__(self, domain, email, token):
                    self.zendesk_domain = domain
                    self.zendesk_user_email = email
                    self.zendesk_api_token = token

            temp_integration = TempIntegration(zendesk_domain, zendesk_user_email, zendesk_api_token)
            
            try:
                # Attempt to instantiate the requester (checks credentials are provided)
                zendesk_requester = ZendeskRequester(temp_integration)
            except ValueError as e: # Catches missing credentials error from requester init
                 raise IntegrationError(str(e))
                 
            # Attempt a simple API call to validate credentials and connectivity
            # List tickets with a small batch size to check permissions
            zendesk_requester.list_tickets(batch_size=1) 

            # If successful, return the domain as workspace name and external id
            return {
                'workspace_name': zendesk_domain,
                'external_id': zendesk_domain # Using domain as a unique identifier
            }
        except ValueError as e:
            # Catch validation errors raised by ZendeskRequester's list_tickets
            error_str = str(e)
            logger.error(f"Zendesk connection validation failed for domain {zendesk_domain}: {error_str}", exc_info=False) # Don't need full traceback here
            
            if "Authentication failed" in error_str:
                # Email or API key invalid
                raise ZendeskAuthenticationError("Invalid Zendesk credentials. Check the user email and API token.")
            elif "Permission denied" in error_str:
                 raise ZendeskError("Zendesk API access forbidden. Check user permissions or API token scope.")
            elif "Resource not found" in error_str or "invalid Zendesk domain" in error_str:
                # Subdomain invalid
                 raise ZendeskInvalidSubdomainError(f"Could not connect to Zendesk instance at {zendesk_domain}. Check the domain.")
            elif "rate limit exceeded" in error_str:
                 # Unlikely during validation, but handle anyway
                 raise ZendeskError("Zendesk API rate limit exceeded during validation.")
            elif "name or service not known" in error_str.lower():
                # Domain invalid
                raise ZendeskInvalidDomainError(f"Could not connect to Zendesk instance at {zendesk_domain}. Check the domain.")
            else:
                # Includes the initial credential check error from __init__
                raise ZendeskError(f"Failed to connect to Zendesk: {error_str}")
        except Exception as e:
            # Catch any other unexpected errors
            logger.error(f"Unexpected error during Zendesk validation for {zendesk_domain}: {e}", exc_info=True)
            raise ZendeskError(f"An unexpected error occurred during Zendesk validation: {str(e)}")

    def send_test_message(self, channel_id: str) -> bool:
        # Sending a test message might involve creating a test ticket, which could be complex.
        raise NotImplementedError("Sending test messages is not applicable for Zendesk integration.")

    def revoke_access_token(self) -> None:
        # API Tokens are revoked manually in Zendesk settings
        raise NotImplementedError("API Token revocation must be done manually in Zendesk.")

    def refresh_access_token(self, refresh_token: str) -> dict:
        # Not applicable for API Token authentication
        raise NotImplementedError("Token refresh not applicable for Zendesk API Token setup.")

    # create_integration is handled by the base class or command directly for API Token setups
