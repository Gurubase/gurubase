import logging
from core.github.exceptions import GithubAPIError, GithubInvalidInstallationError, GithubPrivateKeyError
from core.integrations.helpers import IntegrationError
from core.integrations.strategy import IntegrationStrategy
from core.models import GuruType, Integration

logger = logging.getLogger(__name__)

class GitHubStrategy(IntegrationStrategy):
    def __init__(self, integration: 'Integration' = None):
        from core.github.app_handler import GithubAppHandler
        super().__init__(integration)
        self.github_handler = GithubAppHandler(integration)

    def _fetch_repositories(self, installation_id: str, client_id: str = None, private_key: str = None) -> list:
        """Fetch repositories for a GitHub installation"""
        return self.github_handler.fetch_repositories(installation_id, client_id, private_key)
        
    def _fetch_installation(self, installation_id: str, client_id: str = None, private_key: str = None) -> dict:
        """Fetch installation details for a GitHub installation"""
        return self.github_handler.get_installation(installation_id, client_id, private_key)

    def get_workspace_name(self, token_response: dict) -> str:
        raise NotImplementedError("GitHub integration does not support getting workspace name")

    def exchange_token(self, code: str) -> dict:
        """For GitHub, we don't exchange a code. Instead, we use the installation_id as the external_id."""
        raise NotImplementedError("GitHub integration does not use code exchange")

    def get_external_id(self, token_response: dict) -> str:
        """For GitHub, the external_id is the installation_id"""
        return token_response.get('installation_id')

    def list_channels(self, installation_id: str = None, client_id: str = None, private_key: str = None) -> list:
        """For GitHub, we return repositories as channels"""
        repo_names = self._fetch_repositories(installation_id or self.get_integration().external_id, client_id, private_key)
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

    def fetch_workspace_details(self, installation_id: str, client_id: str = None, private_key: str = None) -> dict:
        """For GitHub, we use the installation_id as both external_id and workspace name"""
        installation = self._fetch_installation(installation_id, client_id, private_key)
        if not installation:
            self.github_handler.clear_redis_cache()
            raise ValueError(f"GitHub installation not found for ID: {installation_id}")
        workspace_name = installation.get('account', {}).get('login')
        if not workspace_name:
            workspace_name = f"GitHub Installation {installation_id}"
        
        bot_slug = installation.get('app_slug')
        if not bot_slug:
            bot_slug = 'gurubase'

        html_url = installation.get('html_url')
        if not html_url:
            # Fallback, works on non-organization installations
            html_url = f"https://github.com/settings/installations/{installation_id}"

        return {
            'external_id': installation_id,  # bot_token is actually installation_id in this case
            'workspace_name': workspace_name,
            'bot_slug': bot_slug,
            'html_url': html_url
        }

    def get_type(self) -> str:
        return 'GITHUB'

    def create_integration(self, installation_id: str, guru_type: GuruType) -> Integration:
        """Create GitHub integration with the installation ID
        Used in OAuth flow.
        """
        # Check if integration already exists for this type and external_id
        if Integration.objects.filter(type=self.get_type(), external_id=installation_id).exists():
            logger.error(f"Integration for {self.get_type()} with ID {installation_id} already exists")
            raise IntegrationError(f"This integration type is already connected to this guru. Please disconnect the existing integration before connecting a new one.")
        
        try:
            # Fetch repository names for workspace name
            installation_details = self.fetch_workspace_details(installation_id)
            channels = self.list_channels(installation_id)
            
            return Integration.objects.create(
                type=self.get_type(),
                external_id=installation_id,
                guru_type=guru_type,
                access_token=installation_id,  # For GitHub, we use installation_id as the access_token
                workspace_name=installation_details.get('workspace_name'),
                github_bot_name=installation_details.get('bot_slug'),
                github_html_url=installation_details.get('html_url'),
                channels=channels
            )
        except (GithubAPIError, GithubInvalidInstallationError, GithubPrivateKeyError) as e:
            raise e
        except Exception as e:
            logger.error(f"Error creating GitHub integration: {e}", exc_info=True)
            raise IntegrationError(f"Error creating GitHub integration. Please try again. If the problem persists, please contact support.")
