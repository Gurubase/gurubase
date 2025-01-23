import logging
from django.core.cache import caches
from django.conf import settings
from rest_framework.throttling import SimpleRateThrottle
from core.models import APIKey

logger = logging.getLogger(__name__)

class ConcurrencyThrottleApiKey(SimpleRateThrottle):
    cache = caches["alternate"] # redis, see settings.py
    rate = settings.API_CONCURRENCY_THROTTLE_RATE    # do not delete, required for initial self.num_requests and self.duration calculation in SimpleRateThrottle

    def get_cache_key(self, request, view):
        api_key = request.META.get('HTTP_X_API_KEY')
        if not api_key:
            api_key = request.META.get('X-API-KEY')

        if not api_key:
            return "9999"   # anonym

        try:
            APIKey.objects.get(key=api_key)
        except Exception:
            return "9999"

        return f"api_key:{api_key}"
