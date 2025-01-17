from corsheaders.signals import check_request_enabled
from django.urls import resolve
from urllib.parse import urlparse
from core.models import WidgetId
import logging

logger = logging.getLogger(__name__)

def cors_allow_api_keys(sender, request, **kwargs):
    """
    Signal handler to allow CORS for domains registered with widget IDs.
    Checks if the requesting origin matches any widget ID's domain_url.
    """
    try:
        # Get origin from headers
        origin = request.headers.get('origin')
        if not origin:
            return False

        # Parse origin to get domain
        parsed_origin = urlparse(origin)
        request_domain = f"{parsed_origin.scheme}://{parsed_origin.netloc}"
        
        # Check if this domain exists in any widget ID
        return WidgetId.objects.filter(domain_url=request_domain).exists()

    except Exception as e:
        # Log the error but don't block the request - let other CORS rules handle it
        logger.error(f"Error in CORS widget ID check: {str(e)}", exc_info=True)
        return False

# Connect the signal handler
check_request_enabled.connect(cors_allow_api_keys) 