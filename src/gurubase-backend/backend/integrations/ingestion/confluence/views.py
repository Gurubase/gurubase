import logging
from django.conf import settings
from django.core.cache import caches
from integrations.models import Integration
from core.requester import ConfluenceRequester
from core.auth import jwt_auth

from core.guru_types import get_guru_type_object_by_maintainer
from core.exceptions import PermissionError, NotFoundError
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

logger = logging.getLogger(__name__)

@api_view(['POST'])
@jwt_auth
def list_confluence_pages(request, integration_id):
    """
    List Confluence pages with optional filtering.
    
    This endpoint handles both spaces and pages, functioning as a combined endpoint:
    - If cql parameter is provided, returns pages matching the query
    - If no parameters are provided, returns all pages
    
    Requires integration_id in the path.
    Optional POST body parameters:
    - cql: Confluence Query Language for filtering pages
    """
    try:
        integration = Integration.objects.get(id=integration_id)
    except Integration.DoesNotExist:
        return Response({'msg': 'Integration not found'}, status=status.HTTP_404_NOT_FOUND)

    # Validate user permission (e.g., maintainer or admin)
    try:
        get_guru_type_object_by_maintainer(integration.guru_type.slug, request)
    except PermissionError:
        return Response({'msg': 'Forbidden'}, status=status.HTTP_403_FORBIDDEN)
    except NotFoundError:
        # This shouldn't happen if integration exists, but good practice
        return Response({'msg': 'Associated Guru type not found'}, status=status.HTTP_404_NOT_FOUND)

    # Validate integration type
    if integration.type != Integration.Type.CONFLUENCE:
        return Response({'msg': 'This integration is not a Confluence integration.'}, status=status.HTTP_400_BAD_REQUEST)

    # Extract parameters from request data with defaults
    cql = request.data.get('query')

    try:
        confluence_requester = ConfluenceRequester(integration)
        result = confluence_requester.list_pages(
            cql=cql 
        )
        return Response(result, status=status.HTTP_200_OK)
    except ValueError as e:
        # Handle specific errors from ConfluenceRequester
        error_str = str(e)
        if "Invalid Confluence credentials" in error_str:
             return Response({'msg': 'Invalid Confluence credentials.'}, status=status.HTTP_401_UNAUTHORIZED)
        elif "Confluence API access forbidden" in error_str:
             return Response({'msg': 'Confluence API access forbidden. Check user permissions or API token scope.'}, status=status.HTTP_403_FORBIDDEN)
        else:
             logger.error(f"Error listing Confluence content for integration {integration_id}: {e}", exc_info=True)
             return Response({'msg': f'Failed to list Confluence pages: {error_str}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    except Exception as e:
        logger.error(f"Unexpected error listing Confluence content for integration {integration_id}: {e}", exc_info=True)
        return Response({'msg': 'An unexpected error occurred.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
