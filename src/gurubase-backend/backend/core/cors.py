from corsheaders.signals import check_request_enabled
from django.urls import resolve
from urllib.parse import urlparse
from core.models import WidgetId
import logging

logger = logging.getLogger(__name__)

def cors_allow_api_keys(sender, request, **kwargs):
    """
    Signal handler to allow CORS for domains registered with widget IDs.
    Checks if the requesting origin matches any widget ID's domain or wildcard pattern.
    """
    try:
        # Get origin from headers
        origin = request.headers.get('origin')
        if not origin:
            return False

        # Parse origin to get domain
        parsed_origin = urlparse(origin)
        request_domain = f"{parsed_origin.scheme}://{parsed_origin.netloc}"
        
        # First check for exact domain matches (more efficient query)
        if WidgetId.objects.filter(domain=request_domain, is_wildcard=False).exists():
            return True
            
        # Then check for wildcard patterns
        wildcard_patterns = WidgetId.objects.filter(is_wildcard=True).values_list('domain', flat=True)
        for pattern in wildcard_patterns:
            if WidgetId.domain_matches_pattern(request_domain, pattern):
                return True
                
        return False

    except Exception as e:
        # Log the error but don't block the request - let other CORS rules handle it
        logger.error(f"Error in CORS widget ID check: {str(e)}", exc_info=True)
        return False

# Connect the signal handler
check_request_enabled.connect(cors_allow_api_keys) 