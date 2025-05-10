from integrations.models import Integration
from integrations.strategy import IntegrationStrategy
from core.exceptions import ConfluenceAuthenticationError, ConfluenceError, ConfluenceInvalidDomainError
from ...bots.helpers import IntegrationError
from core.requester import ConfluenceRequester
import logging

logger = logging.getLogger(__name__)

class ConfluenceStrategy(IntegrationStrategy):
    def get_type(self) -> str:
        return Integration.Type.CONFLUENCE

    def exchange_token(self, code: str) -> dict:
        # Confluence uses API Token authentication, not OAuth code exchange in this setup
        raise NotImplementedError("Confluence integration uses API Token, not OAuth code exchange.")

    def get_external_id(self, token_response: dict) -> str:
        # Not applicable for API Token authentication
        raise NotImplementedError("External ID retrieval not applicable for Confluence API Token setup.")

    def list_channels(self, installation_id: str = None, client_id: str = None, private_key: str = None) -> list:
        # Confluence doesn't have the concept of channels like Slack/Discord/GitHub repos in this context
        return []

    def get_workspace_name(self, token_response: dict) -> str:
        # Not applicable for API Token authentication
        raise NotImplementedError("Workspace name retrieval not applicable for Confluence API Token setup.")

    def fetch_workspace_details(self, confluence_domain: str, confluence_user_email: str, confluence_api_token: str) -> dict:
        """
        Validates Confluence connection using provided credentials.
        Returns basic workspace details (domain) upon successful validation.
        Raises IntegrationError if validation fails.
        """
        try:
            # Create a temporary integration-like object for the requester
            class TempIntegration:
                def __init__(self, domain, email, token):
                    self.confluence_domain = domain
                    self.confluence_user_email = email
                    self.confluence_api_token = token
            
            temp_integration = TempIntegration(confluence_domain, confluence_user_email, confluence_api_token)
            try:
                confluence_requester = ConfluenceRequester(temp_integration)
            except Exception as e:
                raise IntegrationError(f"Could not connect to Confluence instance at {confluence_domain}. Please check the domain.")
            
            # Attempt a simple API call to validate credentials
            spaces = confluence_requester.list_spaces(start=0, limit=1)

            # If successful, return the domain as workspace name and external id
            return {
                'workspace_name': confluence_domain,
                'external_id': confluence_domain # Using domain as a unique identifier for the workspace
            }
        except Exception as e:
            logger.error(f"Confluence connection validation failed for domain {confluence_domain}: {e}", exc_info=True)
            # Re-raise as IntegrationError for consistent handling in the command
            if "Invalid Confluence credentials" in str(e) or "401" in str(e):
                # Confluence user email or API token is wrong
                raise ConfluenceAuthenticationError("Invalid Confluence credentials. Check if the API token is correct.")
            elif "Current user not permitted" in str(e):
                raise ConfluenceAuthenticationError("Current user not permitted. Check if the user email is correct and has access to the Confluence instance.")
            elif "Confluence API access forbidden" in str(e) or "403" in str(e):
                raise ConfluenceError("Confluence API access forbidden. Check user permissions or API token scope.")
            else:
                # Confluence domain is wrong
                raise ConfluenceInvalidDomainError(f"Could not connect to Confluence instance at {confluence_domain}. Please check the domain.")

    def send_test_message(self, channel_id: str) -> bool:
        raise NotImplementedError("Sending test messages is not applicable for Confluence integration.")

    def revoke_access_token(self) -> None:
        # API Tokens are typically revoked manually in Confluence settings
        raise NotImplementedError("API Token revocation must be done manually in Confluence.")

    def refresh_access_token(self, refresh_token: str) -> dict:
        # Not applicable for API Token authentication
        raise NotImplementedError("Token refresh not applicable for Confluence API Token setup.") 