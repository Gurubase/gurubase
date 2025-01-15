import logging
from django.conf import settings
from accounts.models import User
from rest_framework.response import Response
from rest_framework import status
from functools import wraps
from django.conf import settings
from rest_framework.response import Response
from rest_framework import status
from jwt import PyJWKClient
import jwt
from core.utils import decode_jwt
from core.models import APIKey, WidgetId

logger = logging.getLogger(__name__)

def auth(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        auth_token = request.headers.get('Authorization')
        if auth_token is None or auth_token != settings.AUTH_TOKEN:
            return Response({'msg': "Unauthorized"}, status=status.HTTP_401_UNAUTHORIZED)
        return view_func(request, *args, **kwargs)
    return wrapper

def jwt_auth(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if settings.ENV == 'selfhosted':
            return view_func(request, *args, **kwargs)
        # request.user = User.objects.all().first()
        # return view_func(request, *args, **kwargs)
        auth_header = request.headers.get('Authorization', '')
        if not auth_header.startswith('Bearer '):
            return Response({'error': 'Invalid authorization header'}, status=401)
        
        token = auth_header.split(' ')[1]

        try:
            # Fetch Auth0 public keys
            jwks_url = f'{settings.AUTH0_DOMAIN}.well-known/jwks.json'
            jwks_client = PyJWKClient(jwks_url)
            signing_key = jwks_client.get_signing_key_from_jwt(token)
            
            # Decode and validate the token
            payload = jwt.decode(
                token,
                signing_key.key,
                algorithms=['RS256'],
                audience=settings.AUTH0_AUDIENCE,
                issuer=settings.AUTH0_DOMAIN
            )
            
            # Add the auth0_id to the request object
            auth0_id = payload['sub']
            if not auth0_id:
                return Response({'error': 'Auth0 ID is required'}, status=status.HTTP_400_BAD_REQUEST)
            
            # Optionally verify user exists in your database
            user = User.objects.filter(auth0_id=auth0_id).first()
            if not user:
                return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
                
            request.auth0_id = auth0_id
            request.user = user
            return view_func(request, *args, **kwargs)
            
        except jwt.ExpiredSignatureError:
            return Response({'error': 'Token has expired'}, status=401)
        except Exception as e:
            logger.error(f'Error while verifying jwt: {str(e)}', exc_info=True)
            return Response({'error': 'Authentication failed'}, status=401)
            
    return wrapper

def combined_auth(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        # return view_func(request, *args, **kwargs)
        # First try JWT auth
        auth_header = request.headers.get('Authorization', '')
        
        # If it's a Bearer token, try JWT auth
        if auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]
            try:
                # Fetch Auth0 public keys
                jwks_url = f'{settings.AUTH0_DOMAIN}.well-known/jwks.json'
                jwks_client = PyJWKClient(jwks_url)
                signing_key = jwks_client.get_signing_key_from_jwt(token)
                
                # Decode and validate the token
                payload = jwt.decode(
                    token,
                    signing_key.key,
                    algorithms=['RS256'],
                    audience=settings.AUTH0_AUDIENCE,
                    issuer=settings.AUTH0_DOMAIN
                )
                
                auth0_id = payload['sub']
                if not auth0_id:
                    return Response({'error': 'Auth0 ID is required'}, status=status.HTTP_400_BAD_REQUEST)
                
                user = User.objects.filter(auth0_id=auth0_id).first()
                if not user:
                    return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
                    
                request.auth0_id = auth0_id
                request.user = user
                
            except (Exception) as e:
                # If JWT auth fails, try normal auth
                if not auth_header == settings.AUTH_TOKEN:
                    return Response({'error': 'Authentication failed'}, status=401)
        
        return view_func(request, *args, **kwargs)
            
    return wrapper

def stream_combined_auth(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if settings.ENV == 'selfhosted':
            return view_func(request, *args, **kwargs)
        # return view_func(request, *args, **kwargs)
        # First try JWT auth
        auth_header = request.headers.get('Authorization', '')
        
        # If it's a Bearer token, try JWT auth
        if auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]
            try:
                # Fetch Auth0 public keys
                jwks_url = f'{settings.AUTH0_DOMAIN}.well-known/jwks.json'
                jwks_client = PyJWKClient(jwks_url)
                signing_key = jwks_client.get_signing_key_from_jwt(token)
                
                # Decode and validate the token
                payload = jwt.decode(
                    token,
                    signing_key.key,
                    algorithms=['RS256'],
                    audience=settings.AUTH0_AUDIENCE,
                    issuer=settings.AUTH0_DOMAIN
                )
                
                auth0_id = payload['sub']
                if not auth0_id:
                    return Response({'error': 'Auth0 ID is required'}, status=status.HTTP_400_BAD_REQUEST)
                
                user = User.objects.filter(auth0_id=auth0_id).first()
                if not user:
                    return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
                    
                request.auth0_id = auth0_id
                request.user = user
                
            except (Exception) as e:
                # If JWT auth fails, try normal auth
                try:
                    if not decode_jwt(token):
                        return Response({'msg': "Unauthorized"}, status=status.HTTP_401_UNAUTHORIZED)
                except Exception as e:
                    # except jwt.ExpiredSignatureError or etc.:
                    logger.error(f'Failed to verify jwt on answer endpoint, exception: {e}', exc_info=True)
                    return Response({'msg': "Unauthorized"}, status=status.HTTP_401_UNAUTHORIZED)

            return view_func(request, *args, **kwargs)
        
        else:
            return Response({'error': 'Authentication failed'}, status=401)
        
        return Response({'error': 'Authentication failed'}, status=401)
            
    return wrapper

def widget_id_auth(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        widget_id = request.headers.get('Authorization')
        if not widget_id:
            return Response({'msg': 'Widget ID is required'}, status=status.HTTP_401_UNAUTHORIZED)
        
        widget_id_obj = WidgetId.validate_key(widget_id)
        if not widget_id_obj:
            return Response({'msg': 'Invalid Widget ID'}, status=status.HTTP_401_UNAUTHORIZED)
        
        # Optional: Validate domain if present
        if widget_id_obj.domain_url:
            origin = request.headers.get('Origin')
            if not origin or not origin.rstrip('/').endswith(widget_id_obj.domain_url):
                return Response({'msg': 'Invalid domain'}, status=status.HTTP_401_UNAUTHORIZED)
        
        request.guru_type = widget_id_obj.guru_type
        return view_func(request, *args, **kwargs)
    return wrapper


def api_key_auth(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        api_key = request.headers.get('X-API-KEY')
        if not api_key:
            return Response({'msg': 'API key is required'}, status=status.HTTP_401_UNAUTHORIZED)
        
        api_key_obj = APIKey.validate_key(api_key)
        if not api_key_obj:
            return Response({'msg': 'Invalid API key'}, status=status.HTTP_401_UNAUTHORIZED)
        
        request.user = api_key_obj.user
        request.auth0_id = api_key_obj.user.auth0_id
        return view_func(request, *args, **kwargs)
    return wrapper
