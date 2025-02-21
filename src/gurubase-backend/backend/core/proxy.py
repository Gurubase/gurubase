import logging
from django.conf import settings
import requests
from django.utils import timezone
from typing import Optional
from core.requester import WebshareRequester

logger = logging.getLogger(__name__)
webshare_requester = WebshareRequester()

def get_random_proxies() -> list[dict]:
    """
    Returns a list of random proxies from the database.
    """
    proxies_response = webshare_requester.get_proxies()
    proxies = proxies_response['results']
    return proxies

def format_proxies(proxies: list[dict]) -> list[str]:
    """
    Formats a list of proxies into a list of strings.
    """
    return [f"http://{proxy['username']}:{proxy['password']}@{proxy['proxy_address']}:{proxy['port']}" for proxy in proxies]

