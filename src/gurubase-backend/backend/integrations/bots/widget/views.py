
import logging
from typing import Generator
from django.conf import settings
from django.core.cache import caches
from core.auth import widget_id_auth
from core.gcp import replace_media_root_with_base_url
from core.models import Question, Binge
from core.utils import (
    # Authentication & validation
    APIType, api_ask,
    
    # Question & answer handling
    search_question,
    
    # Data management
    create_binge_helper
    
)
from rest_framework.response import Response
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from core.handlers.response_handlers import (
    WidgetResponseHandler,
)

logger = logging.getLogger(__name__)

@api_view(['POST'])
@widget_id_auth
def ask_widget(request):
    """
    Widget endpoint for answering questions.
    Supports both streaming and non-streaming responses.
    """
    # Initialize response handler
    response_handler = WidgetResponseHandler()
    
    # Get guru type
    guru_type_object = request.guru_type
    
    # Get request parameters
    question = request.data.get('question')
    binge_id = request.data.get('binge_id')
    parent_slug = request.data.get('parent_slug')
    fetch_existing = request.data.get('fetch_existing', False)

    # Initialize with default values
    binge = None
    parent = None

    # Handle binge if provided
    if binge_id:
        try:
            binge = Binge.objects.get(id=binge_id)
        except Binge.DoesNotExist:
            return response_handler.handle_error_response("Binge not found")

        if not parent_slug:
            return response_handler.handle_error_response("Parent question slug is required")

        try:
            parent = search_question(
                None, 
                guru_type_object, 
                binge, 
                parent_slug, 
                will_check_binge_auth=False,
                only_widget=True
            )
        except Exception as e:
            return response_handler.handle_error_response("Parent question does not exist")

        if not parent:
            return response_handler.handle_error_response("Parent question does not exist")

    # Set fetch_existing to True for non-binge questions
    # if not fetch_existing and not binge:
    #     fetch_existing = True


    # Get widget response
    widget_response = api_ask(
        question=question,
        guru_type=guru_type_object,
        binge=binge,
        parent=parent,
        fetch_existing=fetch_existing,
        api_type=APIType.WIDGET,
        user=None
    )
    
    # Handle error case
    if widget_response.error:
        return response_handler.handle_error_response(widget_response.error)
    
    # Handle existing question case
    if widget_response.is_existing:
        return Response(response_handler.format_question_response(widget_response.question_obj))
    
    # Handle streaming case
    if isinstance(widget_response.content, Generator):
        return response_handler.handle_stream_response(widget_response.content)
    
    # Handle any other cases
    return response_handler.handle_non_stream_response(widget_response.content)

@api_view(['POST'])
@widget_id_auth
def widget_create_binge(request):
    guru_type_object = request.guru_type
    root_slug = request.data.get('root_slug')

    if not root_slug:
        return Response({'msg': 'Root question slug is required'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        root_question = Question.objects.get(slug=root_slug, guru_type=guru_type_object, binge=None)
    except Question.DoesNotExist:
        return Response({'msg': 'Root question does not exist'}, status=status.HTTP_400_BAD_REQUEST)

    binge = create_binge_helper(guru_type_object, None, root_question)

    return Response({'id': str(binge.id), 'root_slug': root_slug}, status=status.HTTP_200_OK)


@api_view(['GET'])
@widget_id_auth
def get_guru_visuals(request):
    guru_type = request.guru_type
    response = {
        'colors': guru_type.colors,
        'icon_url': replace_media_root_with_base_url(guru_type.icon_url),
        'name': guru_type.name,
        'slug': guru_type.slug,
    }

    return Response(response, status=status.HTTP_200_OK)
