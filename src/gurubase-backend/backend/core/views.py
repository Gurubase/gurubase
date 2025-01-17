from datetime import UTC, datetime, timedelta
import json
import logging
import time
from django.http import StreamingHttpResponse
from django.conf import settings
from django.core.cache import caches
from rest_framework.pagination import PageNumberPagination
from django.db.models import Q
from typing import Generator
from django.core.exceptions import ValidationError
from django.views.decorators.csrf import csrf_exempt
from core.requester import GeminiRequester, OpenAIRequester, RerankerRequester
from core.data_sources import PDFStrategy, WebsiteStrategy, YouTubeStrategy, GitHubRepoStrategy
from core.serializers import WidgetIdSerializer, BingeSerializer, DataSourceSerializer, GuruTypeSerializer, GuruTypeInternalSerializer, QuestionCopySerializer, FeaturedDataSourceSerializer
from core.auth import auth, jwt_auth, combined_auth, stream_combined_auth, api_key_auth
from core.gcp import replace_media_root_with_nginx_base_url
from core.models import FeaturedDataSource, Question, ContentPageStatistics, QuestionValidityCheckPricing, Summarization, WidgetId, Binge, DataSource, GuruType
from accounts.models import User
from core.utils import (
    # Authentication & validation
    check_binge_auth, generate_jwt, validate_binge_follow_up,
    validate_guru_type, validate_image, 
    
    # Question & answer handling
    get_question_summary, 
    handle_failed_root_reanswer, is_question_dirty, search_question,
    stream_question_answer, stream_and_save,
    
    # Content formatting & generation
    format_references, format_trust_score, format_date_updated,
    generate_og_image, 
    
    # Data management
    clean_data_source_urls, create_binge_helper, create_custom_guru_type_slug,
    create_guru_type_object, upload_image_to_storage,
    
)
from core.tasks import data_source_retrieval
from core.guru_types import get_guru_type_object, get_guru_types, get_guru_type_object_by_maintainer, get_auth0_user
from core.exceptions import PermissionError, NotFoundError
from rest_framework.decorators import api_view, parser_classes
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework import status

from core.tasks import data_source_retrieval
from core.auth import api_key_auth, auth, jwt_auth, combined_auth, stream_combined_auth, widget_id_auth
from core.data_sources import PDFStrategy, WebsiteStrategy, YouTubeStrategy, GitHubRepoStrategy
from core.exceptions import PermissionError, NotFoundError
from core.gcp import replace_media_root_with_nginx_base_url
from core.guru_types import get_guru_type_object, get_guru_types, get_guru_type_object_by_maintainer, get_auth0_user
from core.handlers.response_handlers import APIResponseHandler, DataSourceResponseHandler, WidgetResponseHandler
from core.models import FeaturedDataSource, Question, ContentPageStatistics, WidgetId, Binge, DataSource, GuruType
from core.requester import OpenAIRequester, RerankerRequester
from core.serializers import (
    BingeSerializer,
    DataSourceSerializer, 
    FeaturedDataSourceSerializer,
    GuruTypeInternalSerializer,
    GuruTypeSerializer,
    QuestionCopySerializer,
    WidgetIdSerializer,
)
from core.services.data_source_service import DataSourceService
from core.utils import (
    # Auth/validation
    APIAskResponse,
    APIType,
    api_ask,
    check_binge_auth,
    generate_jwt,
    validate_guru_type,
    validate_image,
    validate_binge_follow_up,

    # Question handling
    handle_failed_root_reanswer,
    is_question_dirty,
    search_question,
    get_question_summary,
    stream_question_answer,
    stream_and_save,

    # Guru type
    create_guru_type_object,
    create_custom_guru_type_slug,

    # Formatting/display
    format_references,
    format_trust_score,
    format_date_updated,

    # Storage/media
    upload_image_to_storage,
    generate_og_image,

    # Data sources
    clean_data_source_urls,

    # Binge
    create_binge_helper,
)

from accounts.models import User


logger = logging.getLogger(__name__)

def conditional_csrf_exempt(view_func):
    """Decorator to conditionally apply csrf_exempt based on settings"""
    if settings.ENV == 'selfhosted':
        return csrf_exempt(view_func)
    else:
        return view_func

@api_view(['POST'])
@combined_auth
def summary(request, guru_type):
    endpoint_start = time.time()
    
    validate_guru_type(guru_type)

    # reranker_requester = RerankerRequester()
    # if not reranker_requester.rerank_health_check():
    #     return Response({'msg': "Reranker is not healthy"}, status=status.HTTP_425_TOO_EARLY)

    payload_start = time.time()
    try:
        data = request.data
        question = data.get('question')
        binge_id = data.get('binge_id')
    except Exception as e:  # This broad exception is for demonstration; specify your exceptions.
        logger.error(f'Error parsing request data: {e}', exc_info=True)
        question = None
        
    if question is None:
        return Response({'msg': "Please provide a question in the request body"}, status=status.HTTP_400_BAD_REQUEST)
    
    if binge_id:
        try:
            binge = Binge.objects.get(id=binge_id)
            if not check_binge_auth(binge, request.user):
                return Response({'msg': 'User does not have access to this binge'}, status=status.HTTP_401_UNAUTHORIZED)
        except Binge.DoesNotExist:
            return Response({'msg': 'Binge not found'}, status=status.HTTP_404_NOT_FOUND)
    else:
        binge = None

    payload_time = time.time() - payload_start

    existence_check_start = time.time()
    guru_type_object = get_guru_type_object(guru_type)

    if not binge:
        # Only check existence for non-binge. We want to re-answer the binge questions again, and save them as separate questions.
        existing_question = search_question(
            request.user, 
            guru_type_object, 
            binge, 
            None, 
            question
        )
    else:
        existing_question = None

    if existing_question and not is_question_dirty(existing_question):
        response = {
            'question': existing_question.question,
            'question_slug': existing_question.slug,
            'description': existing_question.description,
            'user_question': existing_question.user_question,
            'valid_question': True,
            'completion_tokens': 0,
            'prompt_tokens': 0,
            'cached_prompt_tokens': 0,
            "jwt" : generate_jwt(),
        }
        existence_check_time = time.time() - existence_check_start
        times = {
            'payload_time': payload_time,
            'existence_check_time': existence_check_time,
            'endpoint_start': endpoint_start,
        }
        if settings.LOG_STREAM_TIMES:
            logger.info(f'Summary times: {times}')
        return Response(response, status=status.HTTP_200_OK)
    
    existence_check_time = time.time() - existence_check_start

    summary_start = time.time()
    answer = get_question_summary(question, guru_type, binge, widget=False)
    summary_time = time.time() - summary_start

    endpoint_time = time.time() - endpoint_start

    times = {
        'payload_time': payload_time,
        'existence_check_time': existence_check_time,
        'summary_time': summary_time,
        'endpoint_time': endpoint_time,
    }

    if existing_question:
        answer['question_slug'] = existing_question.slug
    
    if settings.LOG_STREAM_TIMES:
        logger.info(f'Summary times: {times}')

    return Response(answer, status=status.HTTP_200_OK)


@api_view(['POST'])
@stream_combined_auth
@conditional_csrf_exempt
def answer(request, guru_type):
    endpoint_start = time.time()
    
    if settings.ENV == 'selfhosted':
        user = None
    else:
        if request.user.is_anonymous:
            user = None
        else:
            user = request.user

    
    # jwt_start = time.time()
    # auth_jwt_token = request.headers.get('Authorization')
    # try:
    #     decode_jwt(auth_jwt_token)
    # except Exception as e:
    #     # except jwt.ExpiredSignatureError or etc.:
    #     logger.error(f'Failed to verify jwt on answer endpoint, exception: {e}', exc_info=True)
    #     return Response({'msg': "Unauthorized"}, status=status.HTTP_401_UNAUTHORIZED)
    
    validate_guru_type(guru_type)

    # jwt_time = time.time() - jwt_start
    
    payload_start = time.time()
    try:
        data = request.data
        user_question = data.get('user_question')
        question = data.get('question')
        description = data.get('description')
        question_slug = data.get('question_slug')
        completion_tokens = data.get('completion_tokens')
        cached_prompt_tokens = data.get('cached_prompt_tokens')
        prompt_tokens = data.get('prompt_tokens')
        user_intent = data.get('user_intent')
        answer_length = data.get('answer_length')
        parent_question_slug = data.get('parent_question_slug')
        binge_id = data.get('binge_id')
        source = data.get('source', Question.Source.USER.value)   # RAW_QUESTION, USER, REDDIT, SUMMARY_QUESTION
    except Exception as e:
        logger.error(f'Error parsing request data: {e}', exc_info=True)
        question = None

    if binge_id:
        try:
            binge = Binge.objects.get(id=binge_id)
        except Binge.DoesNotExist:
            return Response({'msg': 'Binge not found'}, status=status.HTTP_404_NOT_FOUND)
    else:
        binge = None
        
    if binge and not check_binge_auth(binge, user):
        return Response({'msg': 'User does not have access to this binge'}, status=status.HTTP_401_UNAUTHORIZED)
        
    if question is None or description is None or question_slug is None:
        return Response({'msg': "Please provide all the required fields (question, description, question_slug) in the request body"}, status=status.HTTP_400_BAD_REQUEST)

    if parent_question_slug:
        guru_type_object = get_guru_type_object(guru_type)
        parent_question = search_question(
            user, 
            guru_type_object,
            binge,
            parent_question_slug,
            None
        )
        if not parent_question:
            return Response({'msg': "Parent question not found"}, status=status.HTTP_404_NOT_FOUND)
    else:
        parent_question = None
        
    if binge and not check_binge_auth(binge, user):
        return Response({'msg': 'User does not have access to this binge'}, status=status.HTTP_401_UNAUTHORIZED)

    if settings.ENV != 'selfhosted':
        valid, msg = validate_binge_follow_up(parent_question, binge, user)
        if not valid:
            return Response({'msg': msg}, status=status.HTTP_405_METHOD_NOT_ALLOWED)

    # existing_question = check_if_question_exists(question, guru_type)
    # if existing_question:
    #     def stream_data():
    #        # Split the content into chunks. Here we assume each chunk is a line.
    #         content_chunks = existing_question.content.split('\n')
    #         for chunk in content_chunks:
    #             yield f"{chunk}\n"
    #             # Simulate delay between chunks
    #             time.sleep(0.1)
    #     return StreamingHttpResponse(stream_data(),content_type='text/event-stream')

    payload_time = time.time() - payload_start    
    stream_obj_start = time.time()
    try:
        response, prompt, links, context_vals, context_distances, reranked_scores, trust_score, processed_ctx_relevances, ctx_rel_usage = stream_question_answer(
            question, 
            guru_type, 
            user_intent, 
            answer_length, 
            user_question, 
            parent_question, 
            user
        )
        if not response:
            if not binge:  # Only notify root questions
                handle_failed_root_reanswer(question_slug, guru_type, user_question, question)
            return Response({'msg': "Can not answer the question because of the lack of context"}, status=status.HTTP_406_NOT_ACCEPTABLE)
    except Exception as e:
        logger.error(f'Error while getting answer: {e}', exc_info=True)
        return Response({'msg': "An error occurred while getting the answer"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    stream_obj_time = time.time() - stream_obj_start
    
    times = {
        # 'jwt_time': jwt_time,
        'payload_time': payload_time,
        'stream_obj_time': stream_obj_time,
        'endpoint_start': endpoint_start,
    }

    return StreamingHttpResponse(stream_and_save(
        user_question, 
        question, 
        guru_type, 
        question_slug, 
        description, 
        response, 
        prompt, 
        links, 
        completion_tokens, 
        prompt_tokens, 
        cached_prompt_tokens, 
        context_vals, 
        context_distances, 
        times, 
        reranked_scores, 
        trust_score, 
        processed_ctx_relevances,
        ctx_rel_usage,
        user,
        parent_question, 
        binge, 
        source), content_type='text/event-stream')


@api_view(['GET'])
@combined_auth
def question_detail(request, guru_type, slug):
    # validate_guru_type(guru_type)
    
    user = request.user
    
    question_text = request.query_params.get('question')
    
    binge_id = request.query_params.get('binge_id')
    if binge_id:
        try:
            binge = Binge.objects.get(id=binge_id)
        except Binge.DoesNotExist:
            return Response({'msg': 'Binge not found'}, status=status.HTTP_404_NOT_FOUND)
    else:
        binge = None

    if binge and not check_binge_auth(binge, user):
        return Response({'msg': 'User does not have access to this binge'}, status=status.HTTP_401_UNAUTHORIZED)

    guru_type_object = get_guru_type_object(guru_type)
    question = search_question(
        user, 
        guru_type_object, 
        binge, 
        slug, 
        question_text
    )
    if not question:
        return Response({'msg': 'Question does not exist'}, status=status.HTTP_404_NOT_FOUND)

    similar_questions = question.similar_questions

    question_data = {
        'slug': question.slug,
        'parent_slug': question.parent.slug if question.parent else None,
        'question': question.question,
        'content': question.content,
        'description': question.description,
        'references': format_references(question.references),
        'noindex': not question.add_to_sitemap,
        'trust_score': format_trust_score(question.trust_score),
        'similar_questions': similar_questions,
        'og_image_url': question.og_image_url,
        # 'dirty': is_question_dirty(question),
        'dirty': False,
        'date_updated': format_date_updated(question.date_updated),
        'date_created_meta': question.date_created,
        'date_updated_meta': question.date_updated,
        'follow_up_questions': question.follow_up_questions
    }

    return Response(question_data)


@api_view(['GET'])
@auth
def guru_types(request):
    # Default get all active guru types. If ?all=1, get all guru types.
    get_all = request.query_params.get('all', '0')
    if get_all == '1':
        return Response(get_guru_types(only_active=False), status=status.HTTP_200_OK)
    else:
        return Response(get_guru_types(only_active=True), status=status.HTTP_200_OK)

@api_view(['GET'])
@auth
def guru_type(request, slug):
    guru_type_object = get_guru_type_object(slug)
    serializer = GuruTypeInternalSerializer(guru_type_object)
    return Response(serializer.data, status=status.HTTP_200_OK)

@api_view(['GET'])
@jwt_auth
def my_gurus(request):
    try:
        if settings.ENV == 'selfhosted':
            user = None
        else:
            user = User.objects.get(auth0_id=request.auth0_id)

        if settings.ENV == 'selfhosted' or user.is_admin:
            user_gurus = GuruType.objects.filter(active=True).order_by('-date_created')
        
        else:
            user_gurus = GuruType.objects.filter(maintainers=user, active=True).order_by('-date_created')
        
        gurus_data = []
        for guru in user_gurus:

            widget_ids = WidgetId.objects.filter(guru_type=guru)

            if settings.ENV == 'selfhosted':
                icon_url = replace_media_root_with_nginx_base_url(guru.icon_url)
            else:
                icon_url = guru.icon_url            

            gurus_data.append({
                'id': guru.id,
                'name': guru.name,
                'slug': guru.slug,
                'icon': icon_url,
                'icon_url': icon_url,
                'domain_knowledge': guru.domain_knowledge,
                'github_repo': guru.github_repo,
                'index_repo': guru.index_repo,
                'youtubeCount': 0,
                'pdfCount': 0,
                'websiteCount': 0,
                'widget_ids': WidgetIdSerializer(widget_ids, many=True).data
            })
        
        return Response(gurus_data)
    except Exception as e:
        logger.error(f'Error while fetching user gurus: {e}', exc_info=True)
        return Response({'error': str(e)}, status=500)


@api_view(['GET'])
@auth
def default_questions(request, guru_type):
    try:
        questions = Question.objects.filter(default_question=True, guru_type__slug=guru_type).values('slug', 'question', 'description')
    except Exception as e:
        logger.error(f'Error while fetching default questions: {e}', exc_info=True)
        return Response({'msg': "An error occurred while fetching default questions"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    return Response(questions, status=status.HTTP_200_OK)


@api_view(['POST'])
@auth
def record_page_visit(request, guru_type):
    return Response(status=status.HTTP_200_OK)
    content_slug = request.data.get('content_slug')
    fingerprint = request.data.get('fingerprint')
    
    if not content_slug or not fingerprint:
        return Response({'msg': 'content_slug and fingerprint are required'}, status=status.HTTP_400_BAD_REQUEST)

    validate_guru_type(guru_type)

    cache_key = f"visit:{guru_type}:{content_slug}:{fingerprint}"
    cache = caches['alternate']

    # Check if this fingerprint has visited in the last hour
    if not cache.get(cache_key):
        try:
            question = Question.objects.get(slug=content_slug, guru_type__slug=guru_type)
            stats, created = ContentPageStatistics.objects.get_or_create(question=question)
            stats.view_count += 1
            stats.save()

            # Set cache to expire in 1 hour
            cache.set(cache_key, True, 1 * 60 * 60)
        except Question.DoesNotExist:
            return Response({'msg': 'Question not found'}, status=status.HTTP_404_NOT_FOUND)

    return Response(status=status.HTTP_200_OK)


@api_view(['POST'])
@auth
def record_vote(request, guru_type):

    content_slug = request.data.get('content_slug')
    vote_type = request.data.get('vote_type')  # 'upvote' or 'downvote'
    fingerprint = request.data.get('fingerprint')

    if not content_slug or vote_type not in ['upvote', 'downvote'] or not fingerprint:
        return Response({'msg': 'Invalid parameters'}, status=status.HTTP_400_BAD_REQUEST)

    validate_guru_type(guru_type)

    cache_key = f"vote:{guru_type}:{content_slug}:{fingerprint}"
    cache = caches['alternate']

    # Check if this fingerprint has voted in the last 24 hours
    if not cache.get(cache_key):
        try:
            question = Question.objects.get(slug=content_slug, guru_type__slug=guru_type)
            stats, created = ContentPageStatistics.objects.get_or_create(question=question)
            
            if vote_type == 'upvote':
                stats.upvotes += 1
            elif vote_type == 'downvote':
                stats.downvotes += 1
            else:
                return Response({'msg': 'Invalid vote type'}, status=status.HTTP_400_BAD_REQUEST)
            
            stats.save()

            # Set cache to expire in 24 hours
            cache.set(cache_key, True, 24 * 60 * 60)

            return Response(status=status.HTTP_200_OK)
        except Question.DoesNotExist:
            return Response({'msg': 'Question not found'}, status=status.HTTP_404_NOT_FOUND)
    else:
        return Response(status=status.HTTP_200_OK)

        
@api_view(['GET'])
@auth
def get_processed_raw_questions(request):
    page_num = request.query_params.get('page_num')
    page_size = 100

    if not page_num:
        return Response({'msg': 'Page num must be included'}, status=status.HTTP_400_BAD_REQUEST)
    try:
        page_num = int(page_num)
    except ValueError:
        return Response({'msg': 'Page num must be an integer'}, status=status.HTTP_400_BAD_REQUEST)
    
    raw_questions = Question.objects.filter(source=Question.Source.RAW_QUESTION).order_by('date_created')
    start = (page_num - 1) * page_size
    end = page_num * page_size
    raw_questions = raw_questions[start:end]
    serializer = QuestionCopySerializer(raw_questions, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(['GET'])
@auth
def og_image_generate(request,question_id):
    url, success = generate_og_image(question_id)
    if success:
        return Response({'msg': "OG Image generated", "url": "not implemented yet"}, status=status.HTTP_200_OK)
    else:
        return Response({'msg': "Error generating OG Image"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@auth
def get_guru_type_resources(request, guru_type):
    try:
        resources = []

        # Add featured data sources first
        featured_data_sources = FeaturedDataSource.objects.filter(guru_type__slug=guru_type, active=True)
        serializer = FeaturedDataSourceSerializer(featured_data_sources, many=True)
        
        for data_source in serializer.data:
            resources.append({
                "title": data_source['title'],
                "description": data_source['description'],
                "icon": data_source['icon_url'],
                "url": data_source['url']
            })

        response_data = {
            'guru_type': guru_type,
            'total_resources': len(resources),
            'resources': resources
        }

        return Response(response_data, status=status.HTTP_200_OK)

    except GuruType.DoesNotExist:
        logger.warning(f'Guru type "{guru_type}" not found')
        return Response({'msg': f'Guru type "{guru_type}" not found'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f'Error while getting guru type resources: {e}', exc_info=True)
        return Response({'msg': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

def create_guru_type(name, domain_knowledge, intro_text, stackoverflow_tag, stackoverflow_source, github_repo, image, maintainer=None):
    """Utility function to handle guru type creation logic"""
    if not name or len(name) < 2:
        raise ValueError('Guru type name must be at least 2 characters')
    if len(name) > 18:
        raise ValueError('Guru type name must not exceed 18 characters')

    error, split = validate_image(image)
    if error:
        raise ValueError(error)

    name_without_extension = split[0].replace(' ', '_')
    extension = split[1]

    error, icon_url = upload_image_to_storage(image, name_without_extension, extension)
    if error:
        raise ValueError(error)

    try:
        slug = create_custom_guru_type_slug(name)
    except Exception as e:
        logger.error(f'Error while slugifying the name: {e}', exc_info=True)
        raise ValueError(e.args[0])

    if len(slug) < 2:
        raise ValueError('Guru type name must be at least 2 characters')
    
    if GuruType.objects.filter(slug=slug).exists():
        raise ValueError(f'Guru type {slug} already exists')

    try:
        guru_type_object = create_guru_type_object(
            slug, name, intro_text, domain_knowledge, icon_url, 
            stackoverflow_tag, stackoverflow_source, github_repo, maintainer
        )
    except Exception as e:
        logger.error(f'Error while creating guru type: {e}', exc_info=True)
        raise ValueError(e.args[0])
        
    return guru_type_object

@api_view(['POST'])
@auth
def create_guru_type_internal(request):
    data = request.data
    try:
        guru_type_object = create_guru_type(
            name=data.get('name'),
            domain_knowledge=data.get('domain_knowledge'),
            intro_text=data.get('intro_text'),
            stackoverflow_tag=data.get('stackoverflow_tag', ""),
            stackoverflow_source=data.get('stackoverflow_source', False),
            github_repo=data.get('github_repo', ""),
            image=request.FILES.get('icon_image'),
        )
        return Response(GuruTypeSerializer(guru_type_object).data, status=status.HTTP_200_OK)
    except ValueError as e:
        return Response({'msg': str(e)}, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@jwt_auth
def create_guru_type_frontend(request):
    try:
        if settings.ENV == 'selfhosted':
            user = None
        else:
            user = get_auth0_user(request.auth0_id)
            if not user.is_admin:
                raise PermissionError(f'User {user.auth0_id} is not an admin')
    except PermissionError:
        return Response({'msg': 'Forbidden'}, status=status.HTTP_403_FORBIDDEN)
    
    data = request.data
    try:
        guru_type_object = create_guru_type(
            name=data.get('name'),
            domain_knowledge=data.get('domain_knowledge'),
            intro_text=data.get('intro_text'),
            stackoverflow_tag=data.get('stackoverflow_tag', ""),
            stackoverflow_source=data.get('stackoverflow_source', False),
            github_repo=data.get('github_repo', ""),
            image=request.FILES.get('icon_image'),
            maintainer=user
        )
        return Response(GuruTypeSerializer(guru_type_object).data, status=status.HTTP_200_OK)
    except ValueError as e:
        return Response({'msg': str(e)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@auth
def add_featured_ds_via_api(request, guru_type):
    if not guru_type:
        return Response({'msg': 'Guru type is required'}, status=status.HTTP_400_BAD_REQUEST)
    
    guru_type_object = get_guru_type_object(guru_type, only_active=False)
    
    featured_datasources = json.loads(request.data.get('featured_datasources'))
    for fds in featured_datasources:
        fds_type = fds.get('type')
        if fds_type not in [ds_type[0] for ds_type in DataSource.Type.choices]:
            return Response({'msg': 'Invalid type'}, status=status.HTTP_400_BAD_REQUEST)
        FeaturedDataSource.objects.create(
            guru_type=guru_type_object,
            type=fds_type,
            title=fds.get('title'),
            description=fds.get('description'),
            icon_url=fds.get('icon_url'),
            url=fds.get('url')
        )
    
    return Response({'msg': 'Featured data source added successfully'}, status=status.HTTP_200_OK)
    
    

    
@parser_classes([MultiPartParser, FormParser])
def create_data_sources(request, guru_type):
    guru_type_object = get_guru_type_object(guru_type, only_active=False)

    pdf_files = request.FILES.getlist('pdf_files', [])
    youtube_urls = request.data.get('youtube_urls', '[]')
    website_urls = request.data.get('website_urls', '[]')
    github_urls = request.data.get('github_urls', '[]')
    pdf_privacies = request.data.get('pdf_privacies', '[]')
    
    try:
        youtube_urls = json.loads(youtube_urls)
        website_urls = json.loads(website_urls)
        github_urls = json.loads(github_urls)
        pdf_privacies = json.loads(pdf_privacies)
    except Exception as e:
        logger.error(f'Error while parsing urls: {e}', exc_info=True)
        return Response({'msg': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    if not pdf_files and not youtube_urls and not website_urls and not github_urls:
        return Response({'msg': 'No data sources provided'}, status=status.HTTP_400_BAD_REQUEST)

    results = []
    strategies = {
        'pdf': PDFStrategy(),
        'youtube': YouTubeStrategy(),
        'website': WebsiteStrategy(),
        'github': GitHubRepoStrategy()
    }

    for i, pdf_file in enumerate(pdf_files):
        results.append(strategies['pdf'].create(guru_type_object, pdf_file, pdf_privacies[i]))

    youtube_urls = clean_data_source_urls(youtube_urls)
    for youtube_url in youtube_urls:
        results.append(strategies['youtube'].create(guru_type_object, youtube_url))

    website_urls = clean_data_source_urls(website_urls)
    for website_url in website_urls:
        results.append(strategies['website'].create(guru_type_object, website_url))

    github_urls = clean_data_source_urls(github_urls)
    for github_url in github_urls:
        results.append(strategies['github'].create(guru_type_object, github_url))
    
    data_source_retrieval.delay(guru_type_slug=guru_type_object.slug)

    return Response({
        'msg': 'Data sources processing completed',
        'results': results
    }, status=status.HTTP_200_OK)

    
@api_view(['GET'])
@jwt_auth
def get_data_sources_detailed(request, guru_type):
    class DataSourcePagination(PageNumberPagination):
        page_size = 10_000
        page_size_query_param = 'page_size'
        max_page_size = 10_000

    try:
        guru_type_object = get_guru_type_object_by_maintainer(guru_type, request)
    except PermissionError:
        return Response({'msg': 'Forbidden'}, status=status.HTTP_403_FORBIDDEN)
    except NotFoundError:
        return Response({'msg': f'Guru type {guru_type} not found'}, status=status.HTTP_404_NOT_FOUND)

    validate_guru_type(guru_type, only_active=False)
    data_sources_queryset = DataSource.objects.filter(guru_type=guru_type_object).order_by('type', 'url')
    
    paginator = DataSourcePagination()
    paginated_data_sources = paginator.paginate_queryset(data_sources_queryset, request)
    serializer = DataSourceSerializer(paginated_data_sources, many=True)
    
    return paginator.get_paginated_response(serializer.data)


def delete_data_sources(request, guru_type):
    guru_type_object = get_guru_type_object(guru_type, only_active=False)

    if 'ids' not in request.data:
        return Response({'msg': 'No data sources provided'}, status=status.HTTP_400_BAD_REQUEST)

    ids = request.data.get('ids', [])

    logger.info(f'Deleting {guru_type} data sources: {ids}')

    DataSource.objects.filter(guru_type=guru_type_object, id__in=ids).delete()

    return Response({
        'msg': 'Data sources deleted successfully'
    }, status=status.HTTP_200_OK)


@api_view(["POST"])
@jwt_auth
def update_data_sources(request, guru_type):
    guru_type_object = get_guru_type_object_by_maintainer(guru_type, request)
    data_sources = request.data.get('data_sources', [])

    # Group data sources by private value for bulk update
    private_ids = []
    non_private_ids = []
    for ds in data_sources:
        if ds.get('private', False):
            private_ids.append(ds['id'])
        else:
            non_private_ids.append(ds['id'])

    # Perform bulk updates
    if private_ids:
        DataSource.objects.filter(
            id__in=private_ids,
            guru_type=guru_type_object,
            type=DataSource.Type.PDF
        ).update(private=True)

    if non_private_ids:
        DataSource.objects.filter(
            id__in=non_private_ids,
            guru_type=guru_type_object,
            type=DataSource.Type.PDF
        ).update(private=False)

    return Response({'msg': 'Data sources updated successfully'}, status=status.HTTP_200_OK)

@api_view(['POST'])
@auth
def data_sources(request, guru_type):
    validate_guru_type(guru_type, only_active=False)
    return create_data_sources(request, guru_type)

@api_view(['POST', 'DELETE'])
@jwt_auth
def data_sources_frontend(request, guru_type):
    try:
        guru_type_obj = get_guru_type_object_by_maintainer(guru_type, request)
    except PermissionError:
        return Response({'msg': 'Forbidden'}, status=status.HTTP_403_FORBIDDEN)
    except NotFoundError:
        return Response({'msg': f'Guru type {guru_type} not found'}, status=status.HTTP_404_NOT_FOUND)
    
    validate_guru_type(guru_type, only_active=False)
    
    if request.method == 'POST':
        if settings.ENV == 'selfhosted':
            user = None
        else:
            user = get_auth0_user(request.auth0_id)
        
        # Check PDF file limits
        pdf_files = request.FILES.getlist('pdf_files', [])
        for pdf_file in pdf_files:
            is_allowed, error_msg = guru_type_obj.check_datasource_limits(user, file=pdf_file)
            if not is_allowed:
                return Response({'msg': error_msg}, status=status.HTTP_400_BAD_REQUEST)
                
        # Check website limits
        website_urls = json.loads(request.data.get('website_urls', '[]'))
        if website_urls:
            is_allowed, error_msg = guru_type_obj.check_datasource_limits(user, website_urls_count=len(website_urls))
            if not is_allowed:
                return Response({'msg': error_msg}, status=status.HTTP_400_BAD_REQUEST)
                
        # Check YouTube limits
        youtube_urls = json.loads(request.data.get('youtube_urls', '[]'))
        if youtube_urls:
            is_allowed, error_msg = guru_type_obj.check_datasource_limits(user, youtube_urls_count=len(youtube_urls))
            if not is_allowed:
                return Response({'msg': error_msg}, status=status.HTTP_400_BAD_REQUEST)

        # Check GitHub repo limits
        github_urls = json.loads(request.data.get('github_urls', '[]'))
        if github_urls:
            is_allowed, error_msg = guru_type_obj.check_datasource_limits(user, github_urls_count=len(github_urls))
            if not is_allowed:
                return Response({'msg': error_msg}, status=status.HTTP_400_BAD_REQUEST)
        
        return create_data_sources(request, guru_type)
    elif request.method == 'DELETE':
        return delete_data_sources(request, guru_type)

@api_view(['POST'])
@jwt_auth
def data_sources_reindex(request, guru_type):
    try:
        guru_type_object = get_guru_type_object_by_maintainer(guru_type, request)
    except PermissionError:
        return Response({'msg': 'Forbidden'}, status=status.HTTP_403_FORBIDDEN)
    except NotFoundError:
        return Response({'msg': f'Guru type {guru_type} not found'}, status=status.HTTP_404_NOT_FOUND)
    
    datasource_ids = request.data.get('ids', [])
    if not datasource_ids:
        return Response({'msg': 'No data sources provided'}, status=status.HTTP_400_BAD_REQUEST)
    
    datasources = DataSource.objects.filter(id__in=datasource_ids, guru_type=guru_type_object)
    if not datasources:
        return Response({'msg': 'No data sources found to reindex'}, status=status.HTTP_404_NOT_FOUND)
    
    for datasource in datasources:
        datasource.reindex()

    data_source_retrieval.delay(guru_type_slug=guru_type_object.slug)
    
    return Response({'msg': 'Data sources reindexed successfully'}, status=status.HTTP_200_OK)
@api_view(['PUT'])
@jwt_auth
def update_guru_type(request, guru_type):
    try:
        guru_type_object = get_guru_type_object_by_maintainer(guru_type, request)
    except PermissionError:
        return Response({'msg': 'Forbidden'}, status=status.HTTP_403_FORBIDDEN)
    except NotFoundError:
        return Response({'msg': f'Guru type {guru_type} not found'}, status=status.HTTP_404_NOT_FOUND)

    data = request.data
    domain_knowledge = data.get('domain_knowledge', guru_type_object.prompt_map['domain_knowledge'])
    intro_text = data.get('intro_text', guru_type_object.intro_text)
    github_repo = data.get('github_repo', guru_type_object.github_repo)
    
    # Handle image upload if provided
    image = request.FILES.get('icon_image')
    if image:
        error, split = validate_image(image)
        if error:
            return Response({'msg': error}, status=status.HTTP_400_BAD_REQUEST)

        name_without_extension = split[0].replace(' ', '_')
        extension = split[1]

        error, icon_url = upload_image_to_storage(image, name_without_extension, extension)
        if error:
            return Response({'msg': error}, status=status.HTTP_400_BAD_REQUEST)
        guru_type_object.icon_url = icon_url

    # Update other fields
    guru_type_object.domain_knowledge = domain_knowledge
    guru_type_object.intro_text = intro_text
    guru_type_object.github_repo = github_repo
    try:
        guru_type_object.save()
    except ValidationError as e:
        return Response({'msg': str(e.message_dict['msg'][0])}, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        logger.error(f'Error while updating guru type: {e}', exc_info=True)
        return Response({'msg': 'Error updating guru type'}, status=status.HTTP_400_BAD_REQUEST)
    
    return Response(GuruTypeInternalSerializer(guru_type_object).data, status=status.HTTP_200_OK)


@api_view(['DELETE'])
@jwt_auth
def delete_guru_type(request, guru_type):
    try:
        guru_type_object = get_guru_type_object_by_maintainer(guru_type, request)
    except PermissionError:
        return Response({'msg': 'Forbidden'}, status=status.HTTP_403_FORBIDDEN)
    except NotFoundError:
        return Response({'msg': f'Guru type {guru_type} not found'}, status=status.HTTP_404_NOT_FOUND)

    try:
        guru_type_object.delete()
    except Exception as e:
        logger.error(f'Error while deleting guru type: {e}', exc_info=True)
        return Response({'msg': 'Error deleting guru type'}, status=status.HTTP_400_BAD_REQUEST)

    return Response({'msg': 'Guru type deleted successfully'}, status=status.HTTP_200_OK)

@api_view(['GET'])
@auth
def guru_type_status(request, guru_type):
    guru_type_object: GuruType = get_guru_type_object(guru_type, only_active=False)
    is_ready = guru_type_object.ready
    return Response({'ready': is_ready}, status=status.HTTP_200_OK)


@api_view(['GET'])
@auth
def export_datasources(request):
    guru_type = request.data.get('guru_type', None)
    if not guru_type:
        return Response({"error": "guru_type is required"}, status=status.HTTP_400_BAD_REQUEST)
    try:
        guru_type_object = get_guru_type_object(guru_type, only_active=False)
    except Exception as e:
        return Response({"error": "Guru type does not exist"}, status=status.HTTP_400_BAD_REQUEST)
    try:
        data = {
            'data_sources': list(DataSource.objects.filter(guru_type=guru_type_object).values()),
        }
        return Response(data, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@auth
def export_questions(request):
    guru_type = request.data.get('guru_type', None)
    if not guru_type:
        return Response({"error": "guru_type is required"}, status=status.HTTP_400_BAD_REQUEST)
    try:
        guru_type_object = get_guru_type_object(guru_type, only_active=False)
    except Exception as e:
        return Response({"error": "Guru type does not exist"}, status=status.HTTP_400_BAD_REQUEST)
    try:
        data = {
            'questions': list(Question.objects.filter(guru_type=guru_type_object).values()),
        }
        return Response(data, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@combined_auth
def follow_up_examples(request, guru_type):
    user = request.user
    
    if not settings.GENERATE_FOLLOW_UP_EXAMPLES:
        return Response([], status=status.HTTP_200_OK)
    
    validate_guru_type(guru_type, only_active=True)
    
    binge_id = request.data.get('binge_id')
    question_slug = request.data.get('question_slug')
    question_text = request.data.get('question')
    
    if not question_slug and not question_text:
        return Response({'msg': 'Question slug is required'}, status=status.HTTP_400_BAD_REQUEST)

    if binge_id:
        try:
            binge = Binge.objects.get(id=binge_id)
        except Binge.DoesNotExist:
            return Response({'msg': 'Binge does not exist'}, status=status.HTTP_400_BAD_REQUEST)
    else:
        binge = None

    if binge and not check_binge_auth(binge, user):
        return Response({'msg': 'User does not have access to this binge'}, status=status.HTTP_401_UNAUTHORIZED)

    guru_type_object = get_guru_type_object(guru_type, only_active=True)
        
    last_question = search_question(
        user, 
        guru_type_object, 
        binge, 
        question_slug, 
        question_text
    )
    if not last_question:
        return Response({'msg': 'Question does not exist'}, status=status.HTTP_400_BAD_REQUEST)
    
    if last_question.follow_up_questions:
        return Response(last_question.follow_up_questions, status=status.HTTP_200_OK)
    
    # Get question history
    questions = [last_question.question]
    ptr = last_question
    while ptr.parent:
        questions.append(ptr.parent.question)
        ptr = ptr.parent
    questions.reverse()  # Put in chronological order
    
    # Get relevant contexts from the last question
    contexts = []
    if last_question.processed_ctx_relevances and 'kept' in last_question.processed_ctx_relevances:
        for ctx in last_question.processed_ctx_relevances['kept']:
            # Skip GitHub repo contexts
            try:
                # Extract metadata using regex pattern that matches any context number
                context_parts = ctx['context'].split('\nContext ')
                metadata_text = context_parts[1].split(' Text:')[0]
                metadata_json = metadata_text.split('Metadata:\n')[1].replace("'", '"')
                metadata = json.loads(metadata_json)
                if metadata.get('type') == 'GITHUB_REPO':
                    continue
            except (json.JSONDecodeError, IndexError, KeyError):
                pass  # If we can't parse metadata, include the context
            contexts.append(ctx['context'])
    
    if not contexts:
        return Response([], status=status.HTTP_200_OK)
    
    # Generate follow-up questions using Gemini
    gemini_requester = GeminiRequester(settings.LARGE_GEMINI_MODEL)
    follow_up_examples = gemini_requester.generate_follow_up_questions(
        questions=questions,
        last_content=last_question.content,
        guru_type=guru_type_object,
        contexts=contexts
    )
    
    # Save and return the generated questions
    last_question.follow_up_questions = follow_up_examples
    last_question.save()
    
    return Response(follow_up_examples, status=status.HTTP_200_OK)


@api_view(['GET'])
@jwt_auth
def follow_up_graph(request, guru_type):
    user = request.user
    validate_guru_type(guru_type, only_active=True)

    binge_id = request.query_params.get('binge_id')
    if not binge_id:
        return Response({'msg': 'Binge ID is required'}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        binge = Binge.objects.get(id=binge_id)
    except Binge.DoesNotExist:
        return Response({'msg': 'Binge does not exist'}, status=status.HTTP_400_BAD_REQUEST)
    
    if not check_binge_auth(binge, user):
        return Response({'msg': 'User does not have access to this binge'}, status=status.HTTP_401_UNAUTHORIZED)
    
    guru_type_obj = get_guru_type_object(guru_type)

    graph_nodes = Question.objects.filter(binge=binge, guru_type=guru_type_obj)
    
    # Format the response
    graph_data = []
    for node in graph_nodes:
        node_data = {
            'id': node.id,
            'slug': node.slug,
            'question': node.question,
            'parent_id': node.parent.id if node.parent else None,
            'date_created': node.date_created.isoformat(),
        }
        graph_data.append(node_data)
        
    last_usage = binge.last_used
    
    if settings.ENV == 'selfhosted':
        binge_outdated = False
    else:
        binge_outdated = last_usage < datetime.now(UTC) - timedelta(seconds=settings.FOLLOW_UP_QUESTION_TIME_LIMIT_SECONDS)

    result = {
        'question_count': len(graph_nodes),
        'graph_data': graph_data,
        'binge_outdated': binge_outdated,
    }
    
    return Response(result, status=status.HTTP_200_OK)

    
@api_view(['POST'])
@jwt_auth
def create_binge(request, guru_type):
    if settings.ENV == 'selfhosted':
        user = None
    else:
        if request.user.is_anonymous:
            user = None
        else:
            user = request.user
    
    validate_guru_type(guru_type, only_active=True)
    
    guru_type_object = get_guru_type_object(guru_type, only_active=True)
    
    root_slug = request.data.get('root_slug')
    if not root_slug:
        return Response({'msg': 'Root slug is required'}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        root_question = Question.objects.get(slug=root_slug, guru_type=guru_type_object, binge=None)
    except Question.DoesNotExist:
        return Response({'msg': 'Root question does not exist'}, status=status.HTTP_400_BAD_REQUEST)
    
    binge = create_binge_helper(guru_type_object, user, root_question)
    
    return Response({'id': str(binge.id), 'root_slug': root_slug}, status=status.HTTP_200_OK)


@api_view(['GET'])
@jwt_auth
def get_binges(request):
    user = request.user
    today = datetime.now(UTC).date()
    week_ago = today - timedelta(days=7)
    
    page_num = request.query_params.get('page_num', 1)
    search_query = request.query_params.get('search_query', '').strip()
    
    try:
        page_num = int(page_num)
    except ValueError:
        return Response({'msg': 'Page number must be an integer'}, status=status.HTTP_400_BAD_REQUEST)
    
    page_size = settings.BINGE_HISTORY_PAGE_SIZE
    
    # Base queryset
    if settings.ENV == 'selfhosted' or user.is_admin:
        binges = Binge.objects.all().order_by('-last_used')
    else:
        binges = Binge.objects.filter(owner=user).order_by('-last_used')
    
    # Apply search filter if search query exists
    if search_query:
        binges = binges.filter(
            Q(root_question__question__icontains=search_query) |
            Q(root_question__user_question__icontains=search_query) |
            Q(root_question__slug__icontains=search_query)
        )
    
    # Get paginated binges
    page_start = page_size * (page_num - 1)
    page_end = page_start + page_size
    
    paginated_binges = binges[page_start:page_end]
    if len(binges[page_end:]) > 0:
        has_more = True
    else:
        has_more = False
    
    # Group paginated binges by time periods
    grouped_binges = {
        'today': [],
        'last_week': [], 
        'older': []
    }

    for binge in paginated_binges:
        binge_date = binge.last_used.date()
        if binge_date == today:
            grouped_binges['today'].append(binge)
        elif week_ago <= binge_date < today:
            grouped_binges['last_week'].append(binge)
        else:
            grouped_binges['older'].append(binge)

    binges = grouped_binges

    response = {
        'today': BingeSerializer.serialize_binges(binges['today']),
        'last_week': BingeSerializer.serialize_binges(binges['last_week']),
        'older': BingeSerializer.serialize_binges(binges['older']),
        'has_more': has_more,
    }

    return Response(response, status=status.HTTP_200_OK)

@api_view(['GET'])
def health_check(request):
    return Response({'status': 'healthy'}, status=status.HTTP_200_OK)


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


@api_view(['POST', 'DELETE'])
@jwt_auth
def manage_widget_ids(request, guru_type):
    guru_type_object = get_guru_type_object(guru_type, only_active=False)

    if request.method == 'POST':
        domain_url = request.data.get('domain_url')
        if not domain_url:
            return Response({'msg': 'Domain URL is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            key = guru_type_object.generate_widget_id(domain_url)
            return Response({'widget_id': key}, status=status.HTTP_200_OK)
        except ValidationError as e:
            return Response({'msg': str(e.messages[0])}, status=status.HTTP_400_BAD_REQUEST)

    elif request.method == 'DELETE':
        widget_id = request.data.get('widget_id')
        if not widget_id:
            return Response({'msg': 'Widget ID is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            widget_id_obj = WidgetId.objects.get(guru_type=guru_type_object, key=widget_id)
        except WidgetId.DoesNotExist:
            return Response({'msg': 'Widget ID does not exist'}, status=status.HTTP_400_BAD_REQUEST)
        
        widget_id_obj.delete()
        return Response({'msg': 'Widget ID deleted successfully'}, status=status.HTTP_200_OK)


@api_view(['GET'])
@widget_id_auth
def get_guru_visuals(request):
    guru_type = request.guru_type
    response = {
        'colors': guru_type.colors,
        'icon_url': guru_type.icon_url,
        'name': guru_type.name,
        'slug': guru_type.slug,
    }

    return Response(response, status=status.HTTP_200_OK)


@api_view(['POST'])
@api_key_auth
def api_answer(request, guru_type):
    """
    API endpoint for answering questions.
    Supports both streaming and non-streaming responses.
    Creates a binge for root questions and supports follow-up questions within a binge.
    """
    # Initialize response handler
    response_handler = APIResponseHandler()
    
    # Get guru type
    try:
        guru_type_object = get_guru_type_object(guru_type)
    except Exception as e:
        return response_handler.handle_error_response(e)
    
    # Get request parameters
    question = request.data.get('question')
    stream = request.data.get('stream', False)
    binge_id = request.data.get('session_id')
    fetch_existing = request.data.get('fetch_existing', False)
    user = request.user

    # Initialize with default values
    binge = None
    parent = None

    # Handle binge if provided
    if binge_id:
        try:
            binge = Binge.objects.get(id=binge_id)
        except Binge.DoesNotExist:
            return response_handler.handle_error_response("Binge not found")
        
        if not check_binge_auth(binge, user):
            return response_handler.handle_error_response("Binge not found")
        
        # Find the last question in the binge as the parent
        parent = Question.objects.filter(binge=binge).order_by('-date_updated').first()

    # Get API response
    api_response = api_ask(
        question=question,
        guru_type=guru_type_object,
        binge=binge,
        parent=parent,
        fetch_existing=fetch_existing,
        api_type=APIType.API,
        user=user
    )
    
    # Handle error case
    if api_response.error:
        return response_handler.handle_error_response(api_response.error)
    
    # Handle existing question case
    if api_response.is_existing:
        if stream:
            return response_handler.handle_stream_response(api_response.content)
        response_data = response_handler.format_question_response(api_response.question_obj)
        # Create binge if it's a root question and no binge exists
        if not binge and not parent:
            binge = create_binge_helper(guru_type_object, user, api_response.question_obj)
            response_data['session_id'] = str(binge.id)
        return Response(response_data)
    
    # Handle streaming case
    if isinstance(api_response.content, Generator):
        if stream:
            return response_handler.handle_stream_response(api_response.content)
        
        # Process non-streaming response for generator content
        for _ in api_response.content:
            pass

        # Fetch updated question
        try:
            result = search_question(
                user=user,
                guru_type_object=guru_type_object,
                binge=binge,
                slug=None,
                question=question,
                will_check_binge_auth=False,
                include_api=True
            )
            api_response = APIAskResponse.from_existing(result)
            response_data = response_handler.format_question_response(api_response.question_obj)
            # Create binge if it's a root question and no binge exists
            if not binge and not parent:
                binge = create_binge_helper(guru_type_object, user, api_response.question_obj)
                response_data['session_id'] = str(binge.id)
            return Response(response_data)
        except Exception as e:
            return response_handler.handle_error_response(e)
    
    # Handle any other cases
    return response_handler.handle_non_stream_response(api_response.content)


@parser_classes([MultiPartParser, FormParser])
@api_view(['POST'])
@api_key_auth
def api_create_data_sources(request, guru_type):
    """Create new data sources. Supports PDFs, YouTube URLs, and website URLs."""
    response_handler = DataSourceResponseHandler()
    
    try:
        guru_type_object = get_guru_type_object_by_maintainer(guru_type, request)
    except (PermissionError, NotFoundError) as e:
        return response_handler.handle_error_response(str(e), status.HTTP_403_FORBIDDEN)

    try:
        service = DataSourceService(guru_type_object, request.user)
        
        # Get and validate inputs
        pdf_files = request.FILES.getlist('pdf_files', [])
        pdf_privacies = json.loads(request.data.get('pdf_privacies', '[]'))
        youtube_urls = json.loads(request.data.get('youtube_urls', '[]'))
        website_urls = json.loads(request.data.get('website_urls', '[]'))

        # Validate all inputs
        service.validate_pdf_files(pdf_files, pdf_privacies)
        service.validate_url_limits(youtube_urls, 'youtube')
        service.validate_url_limits(website_urls, 'website')

        # Create data sources
        results = service.create_data_sources(pdf_files, pdf_privacies, youtube_urls, website_urls)

        return response_handler.handle_success_response(
            'Data sources processing completed',
            {'results': results}
        )
    except ValueError as e:
        return response_handler.handle_error_response(str(e))
    except Exception as e:
        return response_handler.handle_error_response(f'Unexpected error: {str(e)}')


@api_view(['PUT'])
@api_key_auth
def api_update_data_source_privacy(request, guru_type):
    """Update privacy settings for data sources."""
    response_handler = DataSourceResponseHandler()
    
    try:
        guru_type_object = get_guru_type_object_by_maintainer(guru_type, request)
    except (PermissionError, NotFoundError) as e:
        return response_handler.handle_error_response(str(e), status.HTTP_403_FORBIDDEN)

    try:
        service = DataSourceService(guru_type_object, request.user)
        data_sources = request.data.get('data_sources', [])
        
        service.update_privacy_settings(data_sources)
        return response_handler.handle_success_response('Data sources updated successfully')
    except ValueError as e:
        return response_handler.handle_error_response(str(e))
    except Exception as e:
        return response_handler.handle_error_response(f'Unexpected error: {str(e)}')


@api_view(['POST'])
@api_key_auth
def api_reindex_data_sources(request, guru_type):
    """Reindex specified data sources."""
    response_handler = DataSourceResponseHandler()
    
    try:
        guru_type_object = get_guru_type_object_by_maintainer(guru_type, request)
    except (PermissionError, NotFoundError) as e:
        return response_handler.handle_error_response(str(e), status.HTTP_403_FORBIDDEN)

    try:
        service = DataSourceService(guru_type_object, request.user)
        datasource_ids = request.data.get('ids', [])
        
        service.reindex_data_sources(datasource_ids)
        return response_handler.handle_success_response('Data sources reindexed successfully')
    except ValueError as e:
        return response_handler.handle_error_response(str(e))
    except Exception as e:
        return response_handler.handle_error_response(f'Unexpected error: {str(e)}')


@api_view(['DELETE'])
@api_key_auth
def api_delete_data_sources(request, guru_type):
    """Delete specified data sources."""
    response_handler = DataSourceResponseHandler()
    
    try:
        guru_type_object = get_guru_type_object_by_maintainer(guru_type, request)
    except (PermissionError, NotFoundError) as e:
        return response_handler.handle_error_response(str(e), status.HTTP_403_FORBIDDEN)

    return delete_data_sources(request, guru_type) 


@api_view(['GET'])
@api_key_auth
def api_retrieve_data_sources(request, guru_type):
    """Retrieve data sources for a guru type with pagination."""
    response_handler = DataSourceResponseHandler()
    
    class DataSourcePagination(PageNumberPagination):
        page_size = 10_000
        page_size_query_param = 'page_size'
        max_page_size = 10_000

    try:
        guru_type_object = get_guru_type_object_by_maintainer(guru_type, request)
    except PermissionError:
        return response_handler.handle_error_response('Forbidden', status.HTTP_403_FORBIDDEN)
    except NotFoundError:
        return response_handler.handle_error_response(f'Guru type {guru_type} not found', status.HTTP_404_NOT_FOUND)

    validate_guru_type(guru_type, only_active=False)
    data_sources_queryset = DataSource.objects.filter(guru_type=guru_type_object).order_by('type', 'url')
    
    paginator = DataSourcePagination()
    paginated_data_sources = paginator.paginate_queryset(data_sources_queryset, request)
    serializer = DataSourceSerializer(paginated_data_sources, many=True)
    
    return paginator.get_paginated_response(serializer.data) 