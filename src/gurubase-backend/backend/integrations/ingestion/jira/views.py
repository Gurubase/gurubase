import logging
from integrations.models import Integration
from core.requester import JiraRequester
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
def list_jira_issues(request, integration_id):
    """
    List Jira issues for a specific integration using a JQL query.
    Requires integration_id in the path and accepts 'jql' as a query parameter.
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
    if integration.type != Integration.Type.JIRA:
        return Response({'msg': 'This integration is not a Jira integration.'}, status=status.HTTP_400_BAD_REQUEST)

    # Get JQL from query params, default if not provided
    jql_query = request.data.get('jql')
    if not jql_query:
        jql_query = 'ORDER BY created DESC'

    try:
        jira_requester = JiraRequester(integration)
        issues = jira_requester.list_issues(jql_query=jql_query)
        return Response({'issues': issues, 'issue_count': len(issues)}, status=status.HTTP_200_OK)
    except ValueError as e:
        # Handle specific errors from JiraRequester
        error_str = str(e)
        if "Invalid Jira credentials" in error_str:
             return Response({'msg': 'Invalid Jira credentials.'}, status=status.HTTP_401_UNAUTHORIZED)
        elif "Jira API access forbidden" in error_str:
             return Response({'msg': 'Jira API access forbidden. Check user permissions or API key scope.'}, status=status.HTTP_403_FORBIDDEN)
        else:
             logger.error(f"Error listing Jira issues for integration {integration_id}: {e}", exc_info=True)
             return Response({'msg': f'Failed to list Jira issues: {error_str}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    except Exception as e:
        logger.error(f"Unexpected error listing Jira issues for integration {integration_id}: {e}", exc_info=True)
        return Response({'msg': 'An unexpected error occurred.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)