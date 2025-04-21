from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from rest_framework.response import Response
from rest_framework import status
from django.conf import settings
import logging
from core.exceptions import ZendeskError, ZendeskInvalidDomainError, ZendeskInvalidSubdomainError
from core.models import Integration, GuruType
from .helpers import IntegrationError
from .factory import IntegrationFactory
from core.github.exceptions import GithubAPIError, GithubInvalidInstallationError, GithubPrivateKeyError

logger = logging.getLogger(__name__)

class IntegrationCommand(ABC):
    @abstractmethod
    def execute(self) -> Response:
        pass

class GetIntegrationCommand(IntegrationCommand):
    def __init__(self, integration: Integration):
        self.integration = integration

    def execute(self) -> Response:
        response_data = {
            'id': self.integration.id,
            'type': self.integration.type,
            'workspace_name': self.integration.workspace_name,
            'external_id': self.integration.external_id,
            'channels': self.integration.channels,
            'date_created': self.integration.date_created,
            'date_updated': self.integration.date_updated,
        }
        
        if self.integration.type == Integration.Type.GITHUB:
            response_data.update({
                'github_client_id': self.integration.masked_github_client_id,
                'github_secret': self.integration.masked_github_secret,
                'github_bot_name': self.integration.github_bot_name,
                'github_html_url': self.integration.github_html_url,
            })
        elif self.integration.type == Integration.Type.JIRA:
             response_data.update({
                'jira_domain': self.integration.jira_domain,
                'jira_user_email': self.integration.jira_user_email,
                'jira_api_key': self.integration.masked_jira_api_key, # Use the masked key
            })
        elif self.integration.type == Integration.Type.ZENDESK:
            response_data.update({
                'zendesk_domain': self.integration.zendesk_domain,
                'zendesk_user_email': self.integration.zendesk_user_email,
                'zendesk_api_token': self.integration.masked_zendesk_api_token,
            })
        else: # Slack, Discord
            response_data.update({
                 'access_token': self.integration.masked_access_token,
            })

        return Response(response_data)

class DeleteIntegrationCommand(IntegrationCommand):
    def __init__(self, integration: Integration, guru_type_object: GuruType):
        self.integration = integration
        self.guru_type_object = guru_type_object

    def execute(self) -> Response:
        self.integration.delete()
        return Response({"encoded_guru_slug": self.guru_type_object.slug}, status=status.HTTP_202_ACCEPTED)

class CreateIntegrationCommand(IntegrationCommand):
    def __init__(self, guru_type_object: GuruType, integration_type: str, data: Dict[str, Any]):
        self.guru_type_object = guru_type_object
        self.integration_type = integration_type
        self.data = data

    def execute(self) -> Response:
        # Allow Jira creation in cloud, restrict others to selfhosted
        if self.integration_type not in [Integration.Type.JIRA, Integration.Type.ZENDESK] and settings.ENV != 'selfhosted':
            return Response({'msg': 'This integration type is only available in the self-hosted version.'}, status=status.HTTP_403_FORBIDDEN)

        try:
            # Validate required fields based on integration type
            if self.integration_type == Integration.Type.GITHUB:
                self._validate_github_fields()
            elif self.integration_type == Integration.Type.JIRA:
                self._validate_jira_fields()
            elif self.integration_type == Integration.Type.ZENDESK:
                self._validate_zendesk_fields()
            else: # Slack, Discord
                self._validate_standard_fields()

            # Get the appropriate integration strategy
            strategy = IntegrationFactory.get_strategy(self.integration_type)
            
            # Fetch workspace details (or validate credentials for Jira)
            workspace_details = self._fetch_workspace_details(strategy)
            
            # Create integration
            integration = self._create_integration(strategy, workspace_details)
            
            # Use GetIntegrationCommand to format the response consistently
            get_command = GetIntegrationCommand(integration)
            return Response(get_command.execute().data, status=status.HTTP_201_CREATED)
                
        except GithubPrivateKeyError as e:
            return Response({'msg': 'Invalid GitHub private key'}, status=status.HTTP_400_BAD_REQUEST)
        except GithubInvalidInstallationError as e:
            return Response({'msg': 'Invalid GitHub installation ID'}, status=status.HTTP_400_BAD_REQUEST)
        except GithubAPIError as e:
            return Response({'msg': 'Invalid GitHub client ID or API error'}, status=status.HTTP_400_BAD_REQUEST)
        except (ZendeskError, ZendeskInvalidDomainError, ZendeskInvalidSubdomainError) as e:
            return Response({'msg': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except IntegrationError as e:
            # Pass specific Jira errors through
            if "Jira" in str(e):
                 return Response({'msg': str(e)}, status=status.HTTP_400_BAD_REQUEST)
            return Response({'msg': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Error creating integration: {e}", exc_info=True)
            # Check if it's a Jira authentication error from the SDK
            if "Unauthorized" in str(e) or "401" in str(e) and self.integration_type == Integration.Type.JIRA:
                 return Response({'msg': 'Invalid Jira credentials.'}, status=status.HTTP_401_UNAUTHORIZED)
            return Response({'msg': 'Internal server error.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def _validate_github_fields(self):
        if not self.data.get('client_id'):
            raise IntegrationError('Missing client ID for GitHub integration')
        if not self.data.get('installation_id'):
            raise IntegrationError('Missing installation ID for GitHub integration')
        if not self.data.get('private_key'):
            raise IntegrationError('Missing private key for GitHub integration')

    def _validate_standard_fields(self):
        if not self.data.get('access_token'):
            raise IntegrationError('Missing access token')

    def _validate_jira_fields(self):
        if not self.data.get('jira_domain'):
            raise IntegrationError('Missing Jira domain')
        if not self.data.get('jira_user_email'):
            raise IntegrationError('Missing Jira user email')
        if not self.data.get('jira_api_key'):
            raise IntegrationError('Missing Jira API key')

    def _validate_zendesk_fields(self):
        if not self.data.get('zendesk_domain'):
            raise IntegrationError('Missing Zendesk domain')
        if not self.data.get('zendesk_user_email'):
            raise IntegrationError('Missing Zendesk user email')
        if not self.data.get('zendesk_api_token'):
            raise IntegrationError('Missing Zendesk API token')

    def _fetch_workspace_details(self, strategy) -> Dict[str, Any]:
        try:
            if self.integration_type == Integration.Type.GITHUB:
                return strategy.fetch_workspace_details(
                    self.data['installation_id'],
                    self.data['client_id'],
                    self.data['private_key']
                )
            elif self.integration_type == Integration.Type.ZENDESK:
                return strategy.fetch_workspace_details(
                    self.data['zendesk_domain'],
                    self.data['zendesk_user_email'],
                    self.data['zendesk_api_token']
                )
            elif self.integration_type == Integration.Type.JIRA:
                 # For Jira, we primarily validate credentials here
                 return strategy.fetch_workspace_details(
                    self.data['jira_domain'],
                    self.data['jira_user_email'],
                    self.data['jira_api_key']
                 )
            else: # Slack, Discord
                return strategy.fetch_workspace_details(self.data['access_token'])
        except (GithubAPIError, GithubInvalidInstallationError, GithubPrivateKeyError) as e:
            raise e
        except (ZendeskError, ZendeskInvalidDomainError, ZendeskInvalidSubdomainError) as e:
            raise e
        except Exception as e:
            logger.error(f"Error fetching workspace details/validating credentials: {e}", exc_info=True)
            if self.integration_type == Integration.Type.JIRA:
                 # TODO: Make this like github exceptions
                 # Check for specific Jira auth errors
                 if "Unauthorized" in str(e) or "401" in str(e):
                      raise IntegrationError('Invalid Jira credentials.')
                 elif "Forbidden" in str(e) or "403" in str(e):
                      raise IntegrationError('Jira API access forbidden.')
                 else:
                      raise IntegrationError(f"Failed to validate Jira connection: {str(e)}")
            else:
                raise IntegrationError('Failed to fetch workspace details. Please make sure your inputs are valid.')

    def _create_integration(self, strategy, workspace_details: Dict[str, Any]) -> Integration:
        """Create integration with CRUD."""
        if self.integration_type == Integration.Type.GITHUB:
            channels = strategy.list_channels(
                self.data['installation_id'],
                self.data['client_id'],
                self.data['private_key']
            )
            return Integration.objects.create(
                guru_type=self.guru_type_object,
                type=self.integration_type,
                workspace_name=workspace_details['workspace_name'],
                external_id=self.data['installation_id'],
                github_private_key=self.data['private_key'],
                channels=channels,
                github_client_id=self.data['client_id'],
                github_secret=self.data.get('github_secret'),
                github_bot_name=workspace_details['bot_slug'],
                github_html_url=workspace_details['html_url']
            )
        elif self.integration_type == Integration.Type.JIRA:
             # workspace_details for Jira contains validated domain/email
             return Integration.objects.create(
                 guru_type=self.guru_type_object,
                 type=self.integration_type,
                 workspace_name=workspace_details['workspace_name'], # Typically the domain
                 external_id=workspace_details['external_id'], # Typically the domain
                 jira_domain=self.data['jira_domain'],
                 jira_user_email=self.data['jira_user_email'],
                 jira_api_key=self.data['jira_api_key'],
                 channels=[] # Jira doesn't have channels in the same way
             )
        elif self.integration_type == Integration.Type.ZENDESK:
            return Integration.objects.create(
                guru_type=self.guru_type_object,
                type=self.integration_type,
                workspace_name=workspace_details['workspace_name'],
                external_id=workspace_details['external_id'],
                zendesk_domain=self.data['zendesk_domain'],
                zendesk_user_email=self.data['zendesk_user_email'],
                zendesk_api_token=self.data['zendesk_api_token'],
                channels=[]
            )
        else: # Slack, Discord
            return Integration.objects.create(
                guru_type=self.guru_type_object,
                type=self.integration_type,
                workspace_name=workspace_details['workspace_name'],
                external_id=workspace_details['external_id'],
                access_token=self.data['access_token'],
                channels=[]
            ) 