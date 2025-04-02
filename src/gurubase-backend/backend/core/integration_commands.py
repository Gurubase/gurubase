from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from rest_framework.response import Response
from rest_framework import status
from django.conf import settings
import logging
from .models import Integration, GuruType
from .integrations import IntegrationFactory, IntegrationError

logger = logging.getLogger(__name__)

class IntegrationCommand(ABC):
    @abstractmethod
    def execute(self) -> Response:
        pass

class GetIntegrationCommand(IntegrationCommand):
    def __init__(self, integration: Integration):
        self.integration = integration

    def execute(self) -> Response:
        return Response({
            'id': self.integration.id,
            'type': self.integration.type,
            'workspace_name': self.integration.workspace_name,
            'external_id': self.integration.external_id,
            'channels': self.integration.channels,
            'github_client_id': self.integration.masked_github_client_id,
            'github_secret': self.integration.masked_github_secret,
            'date_created': self.integration.date_created,
            'date_updated': self.integration.date_updated,
            'access_token': self.integration.masked_access_token,
        })

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
        if settings.ENV != 'selfhosted':
            return Response({'msg': 'Selfhosted only'}, status=status.HTTP_403_FORBIDDEN)

        try:
            # Validate required fields based on integration type
            if self.integration_type == Integration.Type.GITHUB:
                self._validate_github_fields()
            else:
                self._validate_standard_fields()

            # Get the appropriate integration strategy
            strategy = IntegrationFactory.get_strategy(self.integration_type)
            
            # Fetch workspace details
            workspace_details = self._fetch_workspace_details(strategy)
            
            # Create integration
            integration = self._create_integration(strategy, workspace_details)
            
            return Response({
                'id': integration.id,
                'type': integration.type,
                'workspace_name': integration.workspace_name,
                'external_id': integration.external_id,
                'channels': integration.channels,
                'date_created': integration.date_created,
                'date_updated': integration.date_updated,
                'access_token': integration.masked_access_token,
            }, status=status.HTTP_201_CREATED)
                
        except IntegrationError as e:
            return Response({'msg': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Error creating integration: {e}", exc_info=True)
            return Response({'msg': 'Internal server error'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

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

    def _fetch_workspace_details(self, strategy) -> Dict[str, Any]:
        try:
            if self.integration_type == Integration.Type.GITHUB:
                return strategy.fetch_workspace_details(
                    self.data['installation_id'],
                    self.data['client_id'],
                    self.data['private_key']
                )
            else:
                return strategy.fetch_workspace_details(self.data['access_token'])
        except Exception as e:
            logger.error(f"Error fetching workspace details: {e}", exc_info=True)
            raise IntegrationError('Failed to fetch workspace details. Please make sure your inputs are valid.')

    def _create_integration(self, strategy, workspace_details: Dict[str, Any]) -> Integration:
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
            )
        else:
            return Integration.objects.create(
                guru_type=self.guru_type_object,
                type=self.integration_type,
                workspace_name=workspace_details['workspace_name'],
                external_id=workspace_details['external_id'],
                access_token=self.data['access_token'],
                channels=[]
            ) 