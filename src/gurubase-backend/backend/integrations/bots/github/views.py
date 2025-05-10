from rest_framework.test import APIRequestFactory
from django.conf import settings
from django.core.cache import caches

from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from core.utils import create_fresh_binge
from core.views import api_answer
from integrations.bots.github.exceptions import GithubAppHandlerError
from integrations.models import Integration

from .event_handler import GitHubEventFactory, GitHubEventHandler
from .app_handler import GithubAppHandler
import logging

logger = logging.getLogger(__name__)


@api_view(['GET', 'POST'])
def github_webhook(request):
    if request.method != 'POST':
        return Response({'message': 'Webhook received'}, status=status.HTTP_200_OK)

    body = request.body
    data = request.data
    installation_id = data.get('installation', {}).get('id')
    
    if not installation_id:
        logger.error("No installation ID found in webhook payload")
        return Response({'message': 'No installation ID found'}, status=status.HTTP_400_BAD_REQUEST)

    # Try to get integration from cache first
    cache = caches['alternate']
    cache_key = f"github_integration:{installation_id}"
    integration = cache.get(cache_key)
    
    if not integration:
        try:
            # If not in cache, get from database
            integration = Integration.objects.get(type=Integration.Type.GITHUB, external_id=installation_id)
            # Set cache timeout to 0. This is because dynamic updates are not immediately reflected
            # And this may result in bad UX, and false positive bug reports
            cache.set(cache_key, integration, timeout=0)
        except Integration.DoesNotExist:
            logger.error(f"No integration found for installation {installation_id}", exc_info=True)
            return Response({'message': 'No integration found'}, status=status.HTTP_400_BAD_REQUEST)

    assert integration is not None

    bot_name = integration.github_bot_name
    github_handler = GithubAppHandler(integration)
    # Verify GitHub webhook signature
    try:
        signature_header = request.headers.get('x-hub-signature-256')
        github_handler.verify_signature(body, signature_header)
    except GithubAppHandlerError as e:
        logger.error(f"GitHub webhook signature verification failed: {e}")
        return Response({'message': 'Invalid signature'}, status=status.HTTP_403_FORBIDDEN)

    try:
        # Get event type and validate
        event_type = GitHubEventHandler.find_github_event_type(data)
        if not GitHubEventHandler.is_supported_event(event_type):
            return Response({'message': 'Webhook received'}, status=status.HTTP_200_OK)

        # Get the appropriate event handler
        event_handler = GitHubEventFactory.get_handler(event_type, integration, github_handler)
        
        # Extract event data
        event_data = event_handler.extract_event_data(data)
        
        # Find the appropriate channel
        channel = None
        for channel_itr in integration.channels:
            if channel_itr['name'] == event_data['repository_name']:
                channel = channel_itr
                break

        if not channel:
            logger.error(f"No channel found for repository {event_data['repository_name']}", exc_info=True)
            return Response({'message': 'No channel found'}, status=status.HTTP_400_BAD_REQUEST)

        # Check if we should answer
        if not github_handler.will_answer(event_data['body'], bot_name, event_type, channel['mode']):
            return Response({'message': 'Webhook received'}, status=status.HTTP_200_OK)

        # Create a new binge
        binge = create_fresh_binge(integration.guru_type, None)
        guru_type = integration.guru_type.slug
        
        # Create request using APIRequestFactory
        factory = APIRequestFactory()
        
        # Prepare payload for the API
        payload = {
            'question': github_handler.cleanup_user_question(event_data['body'], bot_name),
            'stream': False,
            'short_answer': True,
            'fetch_existing': False,
            'session_id': binge.id
        }

        if event_data['api_url']:
            payload['github_api_url'] = event_data['api_url']
        
        # Create request with API key from integration
        request = factory.post(
            f'/api/v1/{guru_type}/answer/',
            payload,
            HTTP_X_API_KEY=integration.api_key.key,
            format='json'
        )

        # Call api_answer directly
        response = api_answer(request, guru_type)
        
        # Handle the response using the event handler
        event_handler.handle_response(response, event_data, bot_name)

    except Exception as e:
        logger.error(f"Error processing GitHub webhook: {e}", exc_info=True)
        return Response({'message': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
    return Response({'message': 'Webhook received'}, status=status.HTTP_200_OK)
