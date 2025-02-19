import logging
from django.conf import settings
import requests
from django.utils import timezone
from typing import Optional
from core.requester import WebshareRequester
from core.models import Proxy

logger = logging.getLogger(__name__)
webshare_requester = WebshareRequester()

def sync_proxies_with_webshare() -> None:
    """
    Synchronizes proxies with Webshare API.
    Adds new proxies, updates existing ones, and removes deleted ones.
    """
    response = webshare_requester.get_proxies()
    proxies = []

    if not response.ok:
        logger.error(f"Cannot get response: {response.status_code} - {response.reason}")
        return

    response_json = response.json()
    proxies += response_json['results']

    # Get all pages
    while response_json.get('next'):
        response = webshare_requester.get_proxies(response_json['next'])
        if not response.ok:
            logger.error(f"Cannot get response: {response.status_code} - {response.reason}")
            return
        response_json = response.json()
        proxies += response_json['results']

    # Get existing proxies from database
    db_proxy_port_set = set(
        f"{proxy['address']}:{proxy['port']}" 
        for proxy in Proxy.objects.filter(provider='webshare').values('address', 'port')
    )
    
    # Get proxies from API response
    webshare_proxy_port_set = set(
        f"{result['proxy_address']}:{result['port']}" 
        for result in proxies
    )

    # Find differences
    new_proxies = webshare_proxy_port_set - db_proxy_port_set
    proxies_to_delete = db_proxy_port_set - webshare_proxy_port_set
    existing_proxies = webshare_proxy_port_set.intersection(db_proxy_port_set)

    logger.info(
        f"New proxies: {len(new_proxies)} - "
        f"Existing proxies: {len(existing_proxies)} - "
        f"Proxies to delete: {len(proxies_to_delete)}"
    )

    # Update existing proxies
    for result in proxies:
        ip_port = f"{result['proxy_address']}:{result['port']}"
        if ip_port in existing_proxies:
            proxy = Proxy.objects.filter(
                address=result['proxy_address'],
                port=result['port'],
                provider='webshare'
            ).first()
            if proxy:
                update_proxy_if_changed(proxy=proxy, result=result)

        if ip_port in new_proxies:
            add_new_proxy(result=result)
            logger.info(f"New proxy added: {ip_port}")

    # Delete removed proxies
    for proxy_to_delete in proxies_to_delete:
        address, port = proxy_to_delete.split(":")
        proxy = Proxy.objects.filter(
            address=address,
            port=port,
            provider='webshare'
        ).first()
        if proxy:
            proxy.delete()
            logger.info(f"Proxy deleted: {proxy}")

def update_proxy_if_changed(proxy: Proxy, result: dict) -> None:
    """Updates proxy if any fields have changed"""
    if not (proxy.country == result['country_code'] and
            proxy.username == result['username'] and
            proxy.password == result['password'] and
            proxy.is_active == result['valid']):
        proxy.country = result['country_code']
        proxy.continent = get_continent_from_country(country_code=result['country_code'])
        proxy.username = result['username']
        proxy.password = result['password']
        proxy.is_active = result['valid']
        proxy.provider = 'webshare'
        proxy.save()

def add_new_proxy(result: dict) -> None:
    """Adds a new proxy to the database"""
    proxy = Proxy(
        address=result['proxy_address'],
        port=result['port'],
        country=result['country_code'],
        continent=get_continent_from_country(country_code=result['country_code']),
        username=result['username'],
        password=result['password'],
        provider='webshare',
        is_active=result['valid']
    )
    proxy.save()

def check_proxies(test_url: str, timeout: int = 10) -> None:
    """
    Checks all proxies against a test URL to verify they are working.
    Updates their status and response time.
    """
    proxies = Proxy.objects.all()
    for proxy in proxies:
        proxy_dict = {
            "http": f"http://{proxy.username}:{proxy.password}@{proxy.address}:{proxy.port}",
            "https": f"http://{proxy.username}:{proxy.password}@{proxy.address}:{proxy.port}",
        }
        
        try:
            response = requests.get(test_url, timeout=timeout, proxies=proxy_dict, verify=False)
            if response.ok:
                proxy.response_time = response.elapsed.total_seconds()
                proxy.is_active = True
            else:
                proxy.is_active = False
                logger.error(f"Proxy check failed - proxy: {proxy} - Status: {response.status_code}")
        except Exception as e:
            proxy.is_active = False
            logger.error(f"Proxy check failed - proxy: {proxy} - Error: {str(e)}")
        
        proxy.last_checked = timezone.now()
        proxy.save()

def get_random_proxy() -> Optional[str]:
    """Returns a random active proxy from the database"""
    proxy = Proxy.objects.filter(is_active=True, is_locked=False).order_by('?').first()
    if proxy:
        return f"http://{proxy.username}:{proxy.password}@{proxy.address}:{proxy.port}"
    return None

def get_continent_from_country(country_code: str) -> str:
    """Returns the continent for a given country code"""
    CONTINENT_COUNTRIES = {
        'NA': ['US', 'CA', 'MX'],  # North America
        'SA': ['BR', 'AR', 'CO'],  # South America
        'EU': ['GB', 'DE', 'FR', 'IT', 'ES'],  # Europe
        'AS': ['CN', 'JP', 'IN', 'KR'],  # Asia
        'AF': ['ZA', 'NG', 'EG'],  # Africa
        'OC': ['AU', 'NZ'],  # Oceania
    }
    
    for continent, countries in CONTINENT_COUNTRIES.items():
        if country_code in countries:
            return continent
    return "OTHER" 