from .strategy import IntegrationStrategy
from .helpers import IntegrationError
from core.models import Integration, GuruType
from core.requester import JiraRequester # Import JiraRequester
import logging

logger = logging.getLogger(__name__)

class JiraStrategy(IntegrationStrategy):
    def get_type(self) -> str:
        return Integration.Type.JIRA

    def exchange_token(self, code: str) -> dict:
        # Jira uses API Key authentication, not OAuth code exchange in this setup
        raise NotImplementedError("Jira integration uses API Key, not OAuth code exchange.")

    def get_external_id(self, token_response: dict) -> str:
        # Not applicable for API Key authentication
        raise NotImplementedError("External ID retrieval not applicable for Jira API Key setup.")

    def list_channels(self, installation_id: str = None, client_id: str = None, private_key: str = None) -> list:
        # Jira doesn't have the concept of channels like Slack/Discord/GitHub repos in this context
        return []

    def get_workspace_name(self, token_response: dict) -> str:
        # Not applicable for API Key authentication
        raise NotImplementedError("Workspace name retrieval not applicable for Jira API Key setup.")

    def fetch_workspace_details(self, jira_domain: str, jira_user_email: str, jira_api_key: str) -> dict:
        """
        Validates Jira connection using provided credentials.
        Returns basic workspace details (domain) upon successful validation.
        Raises IntegrationError if validation fails.
        """
        try:
            # Create a temporary integration-like object for the requester
            class TempIntegration:
                def __init__(self, domain, email, key):
                    self.jira_domain = domain
                    self.jira_user_email = email
                    self.jira_api_key = key
            
            temp_integration = TempIntegration(jira_domain, jira_user_email, jira_api_key)
            try:
                jira_requester = JiraRequester(temp_integration)
            except Exception as e:
                raise IntegrationError(f"Could not connect to Jira instance at {jira_domain}. Please check the domain.")
            
            # Attempt a simple API call to validate credentials, e.g., get server info or current user
            jira_requester.jira.myself() # Throws exception on auth failure

            # If successful, return the domain as workspace name and external id
            return {
                'workspace_name': jira_domain,
                'external_id': jira_domain # Using domain as a unique identifier for the workspace
            }
        except Exception as e:
            logger.error(f"Jira connection validation failed for domain {jira_domain}: {e}", exc_info=True)
            # Re-raise as IntegrationError for consistent handling in the command
            if "Unauthorized" in str(e) or "401" in str(e):
                # Jira user email or API key is wrong
                 raise IntegrationError("Invalid Jira credentials. Either the user email or API key is wrong.")
            elif "Forbidden" in str(e) or "403" in str(e):
                 raise IntegrationError("Jira API access forbidden. Check user permissions or API key scope.")
            else:
                # Jira domain is wrong
                 raise IntegrationError(f"Could not connect to Jira instance at {jira_domain}. Please check the domain.")

    def send_test_message(self, channel_id: str) -> bool:
        raise NotImplementedError("Sending test messages is not applicable for Jira integration.")

    def revoke_access_token(self) -> None:
        # API Keys are typically revoked manually in Jira settings
        raise NotImplementedError("API Key revocation must be done manually in Jira.")

    def refresh_access_token(self, refresh_token: str) -> dict:
        # Not applicable for API Key authentication
        raise NotImplementedError("Token refresh not applicable for Jira API Key setup.")

    # create_integration is handled by the base class or command directly for API Key setups
    # handle_api_call might not be needed if API Key doesn't expire like OAuth tokens
