from functools import wraps
from rest_framework.response import Response
from rest_framework import status
from core.exceptions import NotFoundError, PermissionError
from core.guru_types import get_guru_type_object_by_maintainer

def guru_type_required(view_func):
    """Decorator to handle common guru type validation and error handling."""
    @wraps(view_func)
    def wrapper(request, guru_type, *args, **kwargs):
        try:
            guru_type_object = get_guru_type_object_by_maintainer(guru_type, request)
            return view_func(request, guru_type_object, *args, **kwargs)
        except PermissionError:
            return Response({'msg': 'Forbidden'}, status=status.HTTP_403_FORBIDDEN)
        except NotFoundError:
            return Response({'msg': f'Guru type {guru_type} not found'}, status=status.HTTP_404_NOT_FOUND)
    return wrapper 