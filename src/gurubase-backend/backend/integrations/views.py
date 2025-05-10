import json
import logging
from django.conf import settings
from django.core.cache import caches
from integrations.factory import IntegrationFactory
from integrations.models import Integration
from integrations.rest_commands import CreateIntegrationCommand, DeleteIntegrationCommand, GetIntegrationCommand
from core.utils import (
    # Authentication & validation
    decode_guru_slug, encode_guru_slug,
)
from core.guru_types import get_guru_type_object_by_maintainer
from core.exceptions import PermissionError, NotFoundError
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from integrations.bots.helpers import IntegrationError
from rest_framework.decorators import api_view
from rest_framework.response import Response

from core.auth import (
    jwt_auth,
)
from core.exceptions import NotFoundError, PermissionError
from core.guru_types import (
    get_guru_type_object_by_maintainer,
)
from core.models import (
    GuruType,
)

logger = logging.getLogger(__name__)

@api_view(['GET'])
def create_integration(request):
    # OAuth flow
    code = request.query_params.get('code')
    state = request.query_params.get('state')

    if not state:
        return Response({
            'msg': 'Missing required parameters'
        }, status=status.HTTP_400_BAD_REQUEST)

    try:
        # Decode the state parameter
        state_json = json.loads(state)
        integration_type = state_json.get('type')
        guru_type_slug = state_json.get('guru_type')
        encoded_guru_slug = state_json.get('encoded_guru_slug')
        installation_id = state_json.get('installation_id')

        if not all([integration_type, guru_type_slug, encoded_guru_slug]):
            return Response({
                'msg': 'Invalid state parameter'
            }, status=status.HTTP_400_BAD_REQUEST)

        decoded_guru_slug = decode_guru_slug(encoded_guru_slug)
        if not decoded_guru_slug or decoded_guru_slug != guru_type_slug:
            return Response({
                'msg': 'Invalid state parameter'
            }, status=status.HTTP_400_BAD_REQUEST)                    

    except Exception as e:
        logger.error(f"Error creating integration: {e}", exc_info=True)
        return Response({
            'msg': 'There has been an error while creating the integration. Please try again. If the problem persists, please contact support.'
        }, status=status.HTTP_400_BAD_REQUEST)

    try:
        guru_type = GuruType.objects.get(slug=guru_type_slug)
    except GuruType.DoesNotExist:
        return Response({
            'msg': 'Invalid guru type'
        }, status=status.HTTP_400_BAD_REQUEST)

    try:
        strategy = IntegrationFactory.get_strategy(integration_type)
        if integration_type.upper() == 'GITHUB':
            if not installation_id:
                return Response({
                    'msg': 'Missing installation_id for GitHub integration'
                }, status=status.HTTP_400_BAD_REQUEST)
            integration = strategy.create_integration(installation_id, guru_type)
        else:
            if not code:
                return Response({
                    'msg': 'Missing code parameter'
                }, status=status.HTTP_400_BAD_REQUEST)
            integration = strategy.create_integration(code, guru_type)
    except IntegrationError as e:
        return Response({
            'msg': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        logger.error(f"Error creating integration: {e}", exc_info=True)
        return Response({
            'msg': 'There has been an error while creating the integration. Please try again. If the problem persists, please contact support.'
        }, status=status.HTTP_400_BAD_REQUEST)

    return Response({
        'id': integration.id,
        'type': integration.type,
        'guru_type': guru_type.slug,
        'channels': integration.channels
    })



@api_view(['GET', 'DELETE', 'POST'])
@jwt_auth
def manage_integration(request, guru_type, integration_type):
    """
    GET: Get integration details for a specific guru type and integration type.
    DELETE: Delete an integration and invalidate its OAuth token.
    POST: Create a new integration.
    """
    try:
        guru_type_object = get_guru_type_object_by_maintainer(guru_type, request)
    except PermissionError:
        return Response({'msg': 'Forbidden'}, status=status.HTTP_403_FORBIDDEN)
    except NotFoundError:
        return Response({'msg': f'Guru type {guru_type} not found'}, status=status.HTTP_404_NOT_FOUND)
        
    # Validate integration type
    if integration_type not in [choice.value for choice in Integration.Type]:
        return Response({'msg': f'Invalid integration type: {integration_type}'}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        if request.method in ['GET', 'DELETE']:
            integration = Integration.objects.get(
                guru_type=guru_type_object,
                type=integration_type
            )
        else:
            integration = None

        if request.method == 'GET':
            command = GetIntegrationCommand(integration)
            return command.execute()
        elif request.method == 'DELETE':
            command = DeleteIntegrationCommand(integration, guru_type_object)
            return command.execute()
        elif request.method == 'POST':
            command = CreateIntegrationCommand(guru_type_object, integration_type, request.data)
            return command.execute()
            
    except Integration.DoesNotExist:
        if request.method == 'GET':
            return Response({"encoded_guru_slug": encode_guru_slug(guru_type_object.slug)}, status=status.HTTP_202_ACCEPTED)
        else:
            return Response({'msg': 'Integration not found'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"Error in manage_integration: {e}", exc_info=True)
        return Response({'msg': 'Internal server error'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@jwt_auth
def list_integrations(request, guru_type):
    """
    GET: List all integrations for a specific guru type.
    """
    try:
        guru_type_object = get_guru_type_object_by_maintainer(guru_type, request)
    except PermissionError:
        return Response({'msg': 'Forbidden'}, status=status.HTTP_403_FORBIDDEN)
    except NotFoundError:
        return Response({'msg': f'Guru type {guru_type} not found'}, status=status.HTTP_404_NOT_FOUND)
    
    try:
        integrations = Integration.objects.filter(guru_type=guru_type_object)
        
        response_data = []
        for integration in integrations:
            response_data.append({
                'id': integration.id,
                'type': integration.type,
                'workspace_name': integration.workspace_name,
                'external_id': integration.external_id,
                'channels': integration.channels,
                'date_created': integration.date_created,
                'date_updated': integration.date_updated,
            })
        
        return Response(response_data, status=status.HTTP_200_OK)
            
    except Exception as e:
        logger.error(f"Error in list_integrations: {e}", exc_info=True)
        return Response({'msg': 'Internal server error'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
