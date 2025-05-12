import logging
from django.conf import settings
from django.core.cache import caches
from core.utils import create_fresh_binge
from integrations.models import Integration, Thread
from core.auth import jwt_auth

from core.guru_types import get_guru_type_object_by_maintainer
from core.exceptions import PermissionError, NotFoundError
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from integrations.factory import IntegrationFactory
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

@api_view(['POST'])
@jwt_auth
def send_test_message(request):
    """Send a test message to a specific channel using the specified integration."""
    integration_id = request.data.get('integration_id')
    channel_id = request.data.get('channel_id')

    if not integration_id or not channel_id:
        return Response({'msg': 'Integration ID and channel ID are required'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        integration = Integration.objects.get(id=integration_id)
    except Integration.DoesNotExist:
        return Response({'msg': 'Integration not found'}, status=status.HTTP_404_NOT_FOUND)

    try:
        # Get the appropriate strategy for the integration type
        strategy = IntegrationFactory.get_strategy(integration.type, integration)
        success = strategy.send_test_message(channel_id)
        
        if success:
            return Response({'msg': 'Test message sent successfully'}, status=status.HTTP_200_OK)
        else:
            return Response({'msg': 'Failed to send test message'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    except Exception as e:
        logger.error(f"Error sending test message: {e}", exc_info=True)
        return Response({'msg': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET', 'POST'])
@jwt_auth
def manage_channels(request, guru_type, integration_type):
    """Get or update channels for a specific integration type of a guru type."""
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
        integration = Integration.objects.get(
            guru_type=guru_type_object,
            type=integration_type
        )
    except Integration.DoesNotExist:
        return Response(status=status.HTTP_204_NO_CONTENT)

    if request.method == 'POST':
        try:
            channels = request.data.get('channels', [])
            integration.channels = channels

            if 'allow_dm' in request.data:
                integration.allow_dm = request.data['allow_dm']

            integration.save()
            
            return Response({
                'id': integration.id,
                'type': integration.type,
                'guru_type': integration.guru_type.slug,
                'channels': integration.channels,
                'allow_dm': integration.allow_dm
            })
        except Exception as e:
            logger.error(f"Error updating channels: {e}", exc_info=True)
            return Response({'msg': 'Internal server error'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    try:
        # Get channels from API
        strategy = IntegrationFactory.get_strategy(integration_type, integration)
        api_channels = strategy.list_channels()

        processed_channels = []
        if integration_type == 'GITHUB':
            # Create a map of channel IDs to their allowed status from DB
            db_channels_map = {
                channel['id']: channel['mode']
                for channel in integration.channels
            }
            # Process each API channel
            for channel in api_channels:
                channel['mode'] = db_channels_map.get(channel['id'], 'auto')
                processed_channels.append(channel)

            # Save the new channels, we save them in retrieval because it is set on GitHub settings. We only read what is set. We can't update them.
            integration.channels = processed_channels
            integration.save()
        elif integration_type == 'SLACK':
            return Response({
                'channels': api_channels,
                'allow_dm': integration.allow_dm
            })
        else:
            # Create a map of channel IDs to their allowed status from DB
            db_channels_map = {
                channel['id']: channel['allowed']
                for channel in integration.channels
            }
            # Process each API channel
            for channel in api_channels:
                # If channel exists in DB, use its allowed status
                # Otherwise, default to False for new channels
                channel['allowed'] = db_channels_map.get(channel['id'], False)
                processed_channels.append(channel)
        
        return Response({
            'channels': processed_channels,
            'allow_dm': integration.allow_dm            
        })
    except Exception as e:
        if 'too many requests' in str(e).lower():
            return Response({'msg': 'Listing channels encountered a rate limit. Please try again later.'}, status=status.HTTP_429_TOO_MANY_REQUESTS)
        logger.error(f"Error listing channels: {e}", exc_info=True)
        keyword = 'repositories' if integration_type == 'GITHUB' else 'channels'
        return Response({'msg': f'Error listing {keyword}. Please make sure the integration is valid.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


def get_or_create_thread_binge(thread_id: str, integration: Integration) -> tuple[Thread, Binge]:
    """Get or create a thread and its associated binge."""
    binge = create_fresh_binge(integration.guru_type, None)
    return None, binge
    # try:
    #     thread = Thread.objects.get(thread_id=thread_id, integration=integration)
    #     return thread, thread.binge
    # except Thread.DoesNotExist:
    #     # Create new binge without a root question
    #     binge = create_fresh_binge(integration.guru_type, None)
    #     thread = Thread.objects.create(
    #         thread_id=thread_id,
    #         binge=binge,
    #         integration=integration
    #     )
    #     return thread, binge

