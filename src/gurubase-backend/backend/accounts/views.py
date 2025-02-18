from rest_framework.response import Response
from rest_framework import status
from rest_framework.decorators import api_view
from accounts.models import User
from django.conf import settings
from functools import wraps
import logging
from django.utils import timezone

from core.requester import Auth0Requester
logger = logging.getLogger(__name__)
auth0_requester = Auth0Requester()


def auth_auth0(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        auth_token = request.headers.get('Authorization')
        if auth_token is None or auth_token != settings.AUTH0_MANAGEMENT_API_TOKEN:
            return Response({'msg': "Unauthorized"}, status=status.HTTP_401_UNAUTHORIZED)
        return view_func(request, *args, **kwargs)
    return wrapper

def get_auth_provider(connection_name):
    if connection_name == 'Username-Password-Authentication':
        return User.AuthProviders.EMAIL
    elif connection_name == 'google-oauth2':
        return User.AuthProviders.GOOGLE
    elif connection_name == 'github':
        return User.AuthProviders.GITHUB
    else:
        logger.error(f'Unknown auth provider: {connection_name}')
        return User.AuthProviders.EMAIL

@api_view(['POST'])
@auth_auth0
def auth0_user_login(request):
    # Example Request Body:
    # '{"auth0_id": "auth0|5f7c8ec7c33c6c004bbafe82", "email": "j+smith@example.com", "name": "John Smith", "picture": "http://www.gravatar.com/avatar/?d=identicon", "full_request": {"connection": {"id": "con_fpe5kj482KO1eOzQ", "metadata": {}, "name": "Username-Password-Authentication", "strategy": "auth0"}, "request": {"geoip": {"cityName": "Bellevue", "continentCode": "NA", "countryCode": "US", "countryCode3": "USA", "countryName": "United States of America", "latitude": 47.61793, "longitude": -122.19584, "subdivisionCode": "WA", "subdivisionName": "Washington", "timeZone": "America/Los_Angeles"}, "hostname": "dev-o0e6bx1accmw5dg4.example.com", "ip": "13.33.86.47", "language": "en", "method": "POST", "user_agent": "curl/7.64.1"}, "tenant": {"id": "dev-o0e6bx1accmw5dg4"}, "transaction": {"acr_values": [], "id": "", "locale": "", "login_hint": "test@test.com", "prompt": ["none"], "protocol": "oauth2-access-token", "redirect_uri": "http://someuri.com", "requested_scopes": [], "response_mode": "form_post", "response_type": ["id_token"], "state": "AABBccddEEFFGGTTasrs", "ui_locales": []}, "user": {"app_metadata": {}, "created_at": "2024-11-01T12:33:27.606Z", "email": "j+smith@example.com", "email_verified": true, "family_name": "Smith", "given_name": "John", "last_password_reset": "2024-11-01T12:33:27.606Z", "name": "John Smith", "nickname": "j+smith", "phoneNumber": "123-123-1234", "phone_number": "123-123-1234", "phone_verified": true, "picture": "http://www.gravatar.com/avatar/?d=identicon", "tenant": "dev-o0e6bx1accmw5dg4", "updated_at": "2024-11-01T12:33:27.606Z", "user_id": "auth0|5f7c8ec7c33c6c004bbafe82", "user_metadata": {}, "username": "j+smith"}, "configuration": {}, "secrets": {"AUTH0_MANAGEMENT_API_TOKEN": "ebdcad69aa2f6d6637761debf2f1bec02b023114bad350c3dce0769bd2ebb604", "BACKEND_URL": ""}}}'

    request_body = request.data

    auth0_id = request_body.get('auth0_id')
    email = request_body.get('email')
    name = request_body.get('name')
    picture = request_body.get('picture')
    connection_name = request_body.get('connection_name')   # google-oauth2, github, Username-Password-Authentication
    full_request = request_body.get('full_request')
    
    if 'identities' in full_request['user']:
        full_request['user'].pop('identities')
    
    if 'secrets' in full_request:
        full_request.pop('secrets')

    try:
        user = User.objects.filter(auth0_id=auth0_id, email=email).first()
        if not user:
            auth_provider = get_auth_provider(connection_name)
            if User.objects.filter(email=email).exists():
                auth0_requester.delete_user(auth0_id)
                existing_auth_provider = User.objects.filter(email=email).first().auth_provider
                formatted_auth_provider = existing_auth_provider.capitalize()
                return Response({"msg": f"This email is already registered with {formatted_auth_provider}. Please login with {formatted_auth_provider} or use a different email."}, status=status.HTTP_400_BAD_REQUEST)
            user = User.objects.create_auth0_user(auth0_id, email, name, picture, full_request, auth_provider, True)
            logger.info(f'Auth0 user created: {user.email}')
            return Response({"msg": "Auth0 user created"}, status=status.HTTP_200_OK)
        else:
            user.last_login = timezone.now()
            user.save()
            logger.info(f'Auth0 user already exists: {user.email}')
            return Response({"msg": "Auth0 user already exists"}, status=status.HTTP_200_OK)
    except Exception as e:
        logger.error(f'Error while authenticating user: {e}', exc_info=True)
        return Response({"msg": "An error occurred while authenticating the user"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
