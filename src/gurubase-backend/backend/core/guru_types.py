from core.serializers import GuruTypeInternalSerializer
from core.models import GuruType
from accounts.models import User
from core.exceptions import PermissionError, NotFoundError, GuruNotFoundError
from django.conf import settings
import logging
from django.db.models import Q

logger = logging.getLogger(__name__)

def generate_milvus_collection_name(name):
    name = name.replace(' ', '_').lower()
    name = name.replace('-', '_')
    
    return f'{name}_collection'

    
def generate_typesense_collection_name(name):
    name = name.replace(' ', '_').lower()
    name = name.replace('-', '_')
    return name


def get_guru_type_prompt_map(guru_type, only_active=True):
    try:
        if only_active:
            guru_type_obj = GuruType.objects.get(slug=guru_type, active=True)
        else:
            guru_type_obj = GuruType.objects.get(slug=guru_type)
    except GuruType.DoesNotExist:
        raise ValueError(f'Guru type {guru_type} does not exist')
    
    return guru_type_obj.prompt_map


def get_guru_type_names(only_active=True):
    if only_active:
        return [guru_type.slug for guru_type in GuruType.objects.filter(active=True)]
    return [guru_type.slug for guru_type in GuruType.objects.all()]


def get_guru_types(only_active=True, user=None):
    filters = Q()
    if only_active:
        filters &= Q(active=True)
    if user is None or user.is_anonymous:
        filters &= Q(private=False)
    elif not user.is_admin:
        # For non-admin users, show public gurus OR gurus they maintain
        filters &= (Q(private=False) | Q(maintainers=user))
    
    guru_types = GuruType.objects.filter(filters).order_by('id')
    serializer = GuruTypeInternalSerializer(guru_types, many=True)
    return serializer.data


def get_guru_type_object(guru_type, only_active=True, user=None):
    filters = Q(slug=guru_type)
    if only_active:
        filters &= Q(active=True)
    
    if user is None or user.is_anonymous:
        filters &= Q(private=False)
    elif not user.is_admin:
        # For non-admin users, only allow access to public gurus or gurus they maintain
        filters &= (Q(private=False) | Q(maintainers=user))
    
    try:
        return GuruType.objects.get(filters)
    except GuruType.DoesNotExist:
        raise GuruNotFoundError({'msg': f'Guru type {guru_type} is not found'})

def get_guru_type_object_without_filters(guru_type):
    try:
        return GuruType.objects.get(slug=guru_type)
    except GuruType.DoesNotExist:
        raise GuruNotFoundError({'msg': f'Guru type {guru_type} is not found'})

def get_auth0_user(auth0_id):
    if settings.ENV == 'selfhosted':
        return None

    user = User.objects.filter(auth0_id=auth0_id).first()
    if not user:
        logger.warning(f'User with auth0_id {auth0_id} does not exist')
        raise PermissionError(f'User with auth0_id {auth0_id} does not exist')
    return user

def get_guru_type_object_by_maintainer(guru_type, request):
    if settings.ENV == 'selfhosted':
        return GuruType.objects.filter(slug=guru_type).first()

    user = get_auth0_user(request.auth0_id)
    if user.is_admin:
        guru_type_object = GuruType.objects.filter(slug=guru_type).first()
    else:
        guru_type_object = GuruType.objects.filter(slug=guru_type).first()
        if not guru_type_object:
            logger.warning(f'Guru type {guru_type} not found')
            raise NotFoundError(f'Guru type {guru_type} not found')
        if not guru_type_object.maintainers.filter(id=user.id).exists():
            logger.warning(f'User {request.auth0_id} is not a maintainer of guru type {guru_type}')
            raise PermissionError(f'User {request.auth0_id} is not a maintainer of guru type {guru_type}')

    if not guru_type_object:
        logger.warning(f'Guru type {guru_type} not found')
        raise NotFoundError(f'Guru type {guru_type} not found')
    return guru_type_object
