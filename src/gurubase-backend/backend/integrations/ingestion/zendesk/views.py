import logging
from django.conf import settings
from django.core.cache import caches
from core.requester import ZendeskRequester
from integrations.models import Integration
from core.auth import jwt_auth

from core.guru_types import get_guru_type_object_by_maintainer
from core.exceptions import PermissionError, NotFoundError
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
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
    Binge,
)

logger = logging.getLogger(__name__)
@api_view(['GET'])
@jwt_auth
def list_zendesk_tickets(request, integration_id):
    """
    List Zendesk tickets for a specific integration.
    Requires integration_id in the path.
    """
    try:
        integration = Integration.objects.get(id=integration_id)
    except Integration.DoesNotExist:
        return Response({'msg': 'Integration not found'}, status=status.HTTP_404_NOT_FOUND)

    # Validate user permission (e.g., maintainer or admin)
    try:
        get_guru_type_object_by_maintainer(integration.guru_type.slug, request)
    except PermissionError:
        return Response({'msg': 'Forbidden'}, status=status.HTTP_406_NOT_ACCEPTABLE)
    except NotFoundError:
        return Response({'msg': 'Associated Guru type not found'}, status=status.HTTP_404_NOT_FOUND)

    # Validate integration type
    if integration.type != Integration.Type.ZENDESK:
        return Response({'msg': 'This integration is not a Zendesk integration.'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        zendesk_requester = ZendeskRequester(integration)
        tickets = zendesk_requester.list_tickets()
        return Response({'tickets': tickets, 'ticket_count': len(tickets)}, status=status.HTTP_200_OK)
    except ValueError as e:
        # Handle specific errors from ZendeskRequester
        error_str = str(e)
        if "Zendesk credentials" in error_str:
            return Response({'msg': 'Missing or invalid Zendesk credentials.'}, status=status.HTTP_401_UNAUTHORIZED)
        elif "Authentication failed" in error_str:
            return Response({'msg': 'Zendesk authentication failed. Check email and API token.'}, status=status.HTTP_401_UNAUTHORIZED)
        elif "Permission denied" in error_str:
            return Response({'msg': 'Zendesk permission denied. Check API token scope.'}, status=status.HTTP_406_NOT_ACCEPTABLE)
        elif "Resource not found" in error_str or "invalid Zendesk domain" in error_str:
            return Response({'msg': 'Zendesk resource not found or invalid domain.'}, status=status.HTTP_404_NOT_FOUND)
        elif "rate limit exceeded" in error_str:
            return Response({'msg': 'Zendesk API rate limit exceeded.'}, status=status.HTTP_429_TOO_MANY_REQUESTS)
        else:
             logger.error(f"Error listing Zendesk tickets for integration {integration_id}: {e}", exc_info=True)
             return Response({'msg': f'Failed to list Zendesk tickets: {error_str}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    except Exception as e:
        logger.error(f"Unexpected error listing Zendesk tickets for integration {integration_id}: {e}", exc_info=True)
        return Response({'msg': 'An unexpected error occurred.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@jwt_auth
def list_zendesk_articles(request, integration_id):
    """
    List Zendesk help center articles for a specific integration.
    Requires integration_id in the path.
    """
    try:
        integration = Integration.objects.get(id=integration_id)
    except Integration.DoesNotExist:
        return Response({'msg': 'Integration not found'}, status=status.HTTP_404_NOT_FOUND)

    # Validate user permission (e.g., maintainer or admin)
    try:
        get_guru_type_object_by_maintainer(integration.guru_type.slug, request)
    except PermissionError:
        return Response({'msg': 'Forbidden'}, status=status.HTTP_406_NOT_ACCEPTABLE)
    except NotFoundError:
        return Response({'msg': 'Associated Guru type not found'}, status=status.HTTP_404_NOT_FOUND)

    # Validate integration type
    if integration.type != Integration.Type.ZENDESK:
        return Response({'msg': 'This integration is not a Zendesk integration.'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        zendesk_requester = ZendeskRequester(integration)
        articles = zendesk_requester.list_articles()
        return Response({'articles': articles, 'article_count': len(articles)}, status=status.HTTP_200_OK)
    except ValueError as e:
        # Handle specific errors from ZendeskRequester
        error_str = str(e)
        if "Zendesk credentials" in error_str:
            return Response({'msg': 'Missing or invalid Zendesk credentials.'}, status=status.HTTP_401_UNAUTHORIZED)
        elif "Authentication failed" in error_str:
            return Response({'msg': 'Zendesk authentication failed. Check email and API token.'}, status=status.HTTP_401_UNAUTHORIZED)
        elif "Permission denied" in error_str:
            return Response({'msg': 'Zendesk permission denied. Check API token scope.'}, status=status.HTTP_406_NOT_ACCEPTABLE)
        elif "Resource not found" in error_str or "invalid Zendesk domain" in error_str:
            return Response({'msg': 'Zendesk resource not found or invalid domain.'}, status=status.HTTP_404_NOT_FOUND)
        elif "rate limit exceeded" in error_str:
            return Response({'msg': 'Zendesk API rate limit exceeded.'}, status=status.HTTP_429_TOO_MANY_REQUESTS)
        else:
             logger.error(f"Error listing Zendesk articles for integration {integration_id}: {e}", exc_info=True)
             return Response({'msg': f'Failed to list Zendesk articles: {error_str}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    except Exception as e:
        logger.error(f"Unexpected error listing Zendesk articles for integration {integration_id}: {e}", exc_info=True)
        return Response({'msg': 'An unexpected error occurred.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
