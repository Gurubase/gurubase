import json
import logging
import random
import string
import time
from datetime import UTC, datetime, timedelta
from typing import Generator
from accounts.models import User
from django.conf import settings
from django.core.cache import caches
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.http import StreamingHttpResponse
from django.views.decorators.csrf import csrf_exempt
from integrations.bots.github.app_handler import GithubAppHandler
from integrations.models import WidgetId
from core.requester import GeminiRequester, OpenAIRequester, OllamaRequester, ZendeskRequester
from core.data_sources import CrawlService, YouTubeService
from core.serializers import WidgetIdSerializer, BingeSerializer, DataSourceSerializer, GuruTypeSerializer, GuruTypeInternalSerializer, QuestionCopySerializer, FeaturedDataSourceSerializer, APIKeySerializer, DataSourceAPISerializer, SettingsSerializer
from core.auth import auth, follow_up_examples_auth, jwt_auth, combined_auth, stream_combined_auth, api_key_auth, widget_id_auth
from core.gcp import replace_media_root_with_nginx_base_url
from core.models import CrawlState, FeaturedDataSource, Question, ContentPageStatistics, Settings, Binge, DataSource, GuruType, APIKey, GuruCreationForm
from accounts.models import User
from core.utils import (
    # Authentication & validation
    APIAskResponse, APIType, api_ask, check_binge_auth, validate_binge_follow_up,
    validate_guru_type, validate_image, 
    
    # Question & answer handling
    get_question_summary, 
    handle_failed_root_reanswer, is_question_dirty, search_question,
    stream_question_answer, stream_and_save,
    
    # Content formatting & generation
    format_references, format_trust_score, format_date_updated,
    generate_og_image, 
    
    # Data management
    create_binge_helper, create_custom_guru_type_slug,
    create_guru_type_object, upload_image_to_storage,
    
)
from core.guru_types import get_guru_type_object, get_guru_types, get_guru_type_object_by_maintainer, get_auth0_user
from core.exceptions import IntegrityError, PermissionError, NotFoundError
from rest_framework.decorators import api_view, parser_classes
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework import status
from rest_framework.decorators import api_view, parser_classes, throttle_classes
from rest_framework.pagination import PageNumberPagination
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from core.handlers.response_handlers import (
    APIResponseHandler,
    DataSourceResponseHandler,
)
from core.services.data_source_service import DataSourceService
from core.throttling import ConcurrencyThrottleApiKey
from integrations.strategy import get_context_handler

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
    from core.utils import get_default_settings
    times = {
        'payload_processing': 0,
        'existence_check': 0,
        'dirtiness_check': 0,
        'total': 0
    }

    user = request.user
    guru_type_object = get_guru_type_object(guru_type, user=user)

    if settings.ENV == 'selfhosted':
        default_settings = get_default_settings()
        valid = False
        if default_settings.ai_model_provider == Settings.AIProvider.OPENAI:
            valid = default_settings.is_openai_key_valid
            error_type = 'openai'
            reason = 'openai_key_invalid'
        elif default_settings.ai_model_provider == Settings.AIProvider.OLLAMA:
            valid = default_settings.is_ollama_url_valid and default_settings.is_ollama_base_model_valid and default_settings.is_ollama_embedding_model_valid
            error_type = 'ollama'
            if not default_settings.is_ollama_url_valid:
                reason = 'ollama_url_invalid'
            elif not (default_settings.is_ollama_base_model_valid and default_settings.is_ollama_embedding_model_valid):
                reason = 'ollama_model_invalid'
        if not valid:
            return Response({'msg': 'Invalid AI model provider settings', 'reason': reason, 'type': error_type}, status=490)

    
    endpoint_start = time.time()
    payload_start = time.time()
    try:
        data = request.data
        question = data.get('question')
        binge_id = data.get('binge_id')
        parent_question_slug = data.get('parent_question_slug')
    except Exception as e:
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
        
    if parent_question_slug:
        parent_question = search_question(
            user, 
            guru_type_object,
            binge,
            parent_question_slug,
            question
        )
        if not parent_question:
            return Response({'msg': "Parent question not found"}, status=status.HTTP_404_NOT_FOUND)
    else:
        parent_question = None
        
    times['payload_processing'] = time.time() - payload_start

    existence_start = time.time()
    
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
    times['existence_check'] = time.time() - existence_start

    # if existing_question:
    #     dirtiness_start = time.time()
    #     is_dirty = is_question_dirty(existing_question)
    #     times['dirtiness_check'] = time.time() - dirtiness_start
        
    #     if not is_dirty:
    #         response = {
    #             'question': existing_question.question,
    #             'question_slug': existing_question.slug,
    #             'description': existing_question.description,
    #             'user_question': existing_question.user_question,
    #             'valid_question': True,
    #             'completion_tokens': 0,
    #             'prompt_tokens': 0,
    #             'cached_prompt_tokens': 0,
    #             "jwt": generate_jwt(),
    #         }
    #         times['total'] = time.time() - endpoint_start
    #         return Response(response, status=status.HTTP_200_OK)

    answer, get_question_summary_times = get_question_summary(
        question, 
        guru_type_object, 
        binge, 
        short_answer=False,
        parent_question=parent_question
    )

    times['get_question_summary'] = get_question_summary_times

    # if existing_question:
    #     answer['question_slug'] = existing_question.slug

    times['total'] = time.time() - endpoint_start
    
    if settings.LOG_STREAM_TIMES:
        logger.info(f'Summary times: {times}')

    answer['times'] = times

    return Response(answer, status=status.HTTP_200_OK)


@api_view(['POST'])
@stream_combined_auth
@conditional_csrf_exempt
def answer(request, guru_type):
    user = request.user
    guru_type_object = get_guru_type_object(guru_type, user=user)

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
        summary_times = data.get('times')
        enhanced_question = data.get('enhanced_question')
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
        response, prompt, links, context_vals, context_distances, reranked_scores, trust_score, processed_ctx_relevances, ctx_rel_usage, before_stream_times = stream_question_answer(
            question, 
            guru_type_object, 
            user_intent, 
            answer_length, 
            user_question, 
            source,
            enhanced_question,
            parent_question, 
            user,
        )
        if not response:
            if not binge:  # Only notify root questions
                handle_failed_root_reanswer(question_slug, guru_type, user_question, question)
            return Response({'msg': "Can not answer the question because of the lack of context"}, status=status.HTTP_406_NOT_ACCEPTABLE)
    except Exception as e:
        logger.error(f'Error while getting answer: {e}', exc_info=True)
        return Response({'msg': "An error occurred while getting the answer"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    times = {}
    times['before_stream'] = before_stream_times
    if summary_times:
        times['summary'] = summary_times

    return StreamingHttpResponse(stream_and_save(
        user_question, 
        question, 
        guru_type_object, 
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
        enhanced_question,
        user,
        parent_question, 
        binge, 
        source,
    ), content_type='text/event-stream')


@api_view(['GET'])
@combined_auth
def question_detail(request, guru_type, slug):
    # This endpoint is only used for UI.
    user = request.user
    guru_type_object = get_guru_type_object(guru_type, user=user)

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

    
    question = search_question(
        user, 
        guru_type_object, 
        binge, 
        slug, 
        None, # Do not search questions by question text, as we want to ask the same question again. This is not the case for integrations or API, but only for UI.
        allow_maintainer_access=True
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
        'dirty': is_question_dirty(question),
        'date_updated': format_date_updated(question.date_updated),
        'date_created_meta': question.date_created,
        'date_updated_meta': question.date_updated,
        'follow_up_questions': question.follow_up_questions,
        'source': question.source
    }

    return Response(question_data)


@api_view(['GET'])
@combined_auth
def guru_types(request):
    # Default get all active guru types. If ?all=1, get all guru types.
    user = request.user
    get_all = request.query_params.get('all', '0')
    if get_all == '1':
        return Response(get_guru_types(only_active=False, user=user), status=status.HTTP_200_OK)
    else:
        return Response(get_guru_types(only_active=True, user=user), status=status.HTTP_200_OK)

@api_view(['GET'])
@combined_auth
def guru_type(request, slug):
    guru_type_object = get_guru_type_object(slug, user=request.user)
    serializer = GuruTypeInternalSerializer(guru_type_object)
    return Response(serializer.data, status=status.HTTP_200_OK)

@api_view(['GET'])
@jwt_auth
def my_gurus(request, guru_slug=None):
    try:
        if settings.ENV == 'selfhosted':
            user = None
        else:
            user = User.objects.get(auth0_id=request.auth0_id)

        if guru_slug:
            sub_query = GuruType.objects.filter(slug=guru_slug)
        else:
            sub_query = GuruType.objects.all()

        if sub_query.count() == 0 and guru_slug:
            return Response({'msg': 'Guru not found'}, status=status.HTTP_404_NOT_FOUND)

        if settings.ENV == 'selfhosted' or user.is_admin:
            user_gurus = sub_query.filter(active=True).order_by('-date_created')
        else:
            user_gurus = sub_query.filter(maintainers=user, active=True).order_by('-date_created')
        
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
                'github_repos': guru.github_repos,
                'index_repo': guru.index_repo,
                'youtube_limit': guru.youtube_count_limit,
                'website_limit': guru.website_count_limit,
                'pdf_size_limit_mb': guru.pdf_size_limit_mb,
                'jira_limit': guru.jira_count_limit,
                'zendesk_limit': guru.zendesk_count_limit,
                'widget_ids': WidgetIdSerializer(widget_ids, many=True).data,
                'github_repo_limit': guru.github_repo_count_limit
            })
        
        if guru_slug:
            return Response(gurus_data[0], status=status.HTTP_200_OK)
        else:
            return Response(gurus_data, status=status.HTTP_200_OK)
    except Exception as e:
        logger.error(f'Error while fetching user gurus: {e}', exc_info=True)
        return Response({'msg': str(e)}, status=500)


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
    validate_guru_type(guru_type)
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

def create_guru_type(name, domain_knowledge, intro_text, stackoverflow_tag, stackoverflow_source, github_repos, image, maintainer=None):
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
        github_repos = json.loads(github_repos)
    except Exception as e:
        logger.error(f'Error while parsing github repos: {e}', exc_info=True)
        raise ValueError('Github repos must be a list of strings')

    try:
        guru_type_object = create_guru_type_object(
            slug, name, intro_text, domain_knowledge, icon_url, 
            stackoverflow_tag, stackoverflow_source, github_repos, maintainer
        )
    except ValidationError as e:
        raise
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
            github_repos=data.get('github_repos', ""),
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
            github_repos=data.get('github_repos', ""),
            image=request.FILES.get('icon_image'),
            maintainer=user
        )
        return Response(GuruTypeSerializer(guru_type_object).data, status=status.HTTP_200_OK)
    except ValidationError as e:
        return Response({'msg': str(e.message_dict['msg'][0])}, status=status.HTTP_400_BAD_REQUEST)
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
    guru_type_object = get_guru_type_object(guru_type, only_active=False, user=request.user)

    pdf_files = request.FILES.getlist('pdf_files', [])
    youtube_urls = request.data.get('youtube_urls', '[]')
    website_urls = request.data.get('website_urls', '[]')
    github_urls = request.data.get('github_urls', '[]')
    pdf_privacies = request.data.get('pdf_privacies', '[]')
    jira_urls = request.data.get('jira_urls', '[]')
    zendesk_urls = request.data.get('zendesk_urls', '[]')
    confluence_urls = request.data.get('confluence_urls', '[]')
    try:
        if type(youtube_urls) == str:
            youtube_urls = json.loads(youtube_urls)
        if type(website_urls) == str:
            website_urls = json.loads(website_urls)
        if type(github_urls) == str:
            github_urls = json.loads(github_urls)
        if type(pdf_privacies) == str:
            pdf_privacies = json.loads(pdf_privacies)
        if type(jira_urls) == str:
            jira_urls = json.loads(jira_urls)
        if type(zendesk_urls) == str:
            zendesk_urls = json.loads(zendesk_urls)
        if type(confluence_urls) == str:
            confluence_urls = json.loads(confluence_urls)
    except Exception as e:
        logger.error(f'Error while parsing urls: {e}', exc_info=True)
        return Response({'msg': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    if not settings.BETA_FEAT_ON:
        jira_urls = []
        zendesk_urls = []
        confluence_urls = []

    if not pdf_files and not youtube_urls and not website_urls and not github_urls and not jira_urls and not zendesk_urls and not confluence_urls:
        return Response({'msg': 'No data sources provided'}, status=status.HTTP_400_BAD_REQUEST)

    service = DataSourceService(guru_type_object, request.user)
    
    try:
        # Validate limits
        service.validate_pdf_files(pdf_files, pdf_privacies)
        service.validate_url_limits(youtube_urls, 'youtube')
        service.validate_url_limits(website_urls, 'website')
        service.validate_url_limits(jira_urls, 'jira')
        service.validate_url_limits(zendesk_urls, 'zendesk')
        service.validate_url_limits(confluence_urls, 'confluence')

        if jira_urls:
            service.validate_integration('jira')
        if zendesk_urls:
            service.validate_integration('zendesk')
        if confluence_urls:
            service.validate_integration('confluence')

        # Create data sources
        results = service.create_data_sources(
            pdf_files=pdf_files,
            pdf_privacies=pdf_privacies,
            youtube_urls=youtube_urls,
            website_urls=website_urls,
            jira_urls=jira_urls,
            zendesk_urls=zendesk_urls,
            confluence_urls=confluence_urls
        )
        
        return Response({
            'msg': 'Data sources processing completed',
            'results': results
        }, status=status.HTTP_200_OK)
    except ValueError as e:
        return Response({'msg': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        logger.error(f'Error creating data sources: {e}', exc_info=True)
        return Response({'msg': 'Internal server error'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


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

    data_sources_queryset = DataSource.objects.filter(guru_type=guru_type_object).order_by('type', 'url')
    
    paginator = DataSourcePagination()
    paginated_data_sources = paginator.paginate_queryset(data_sources_queryset, request)
    serializer = DataSourceSerializer(paginated_data_sources, many=True)
    
    return paginator.get_paginated_response(serializer.data)

def delete_data_sources(request, guru_type):
    user = request.user
    guru_type_object = get_guru_type_object(guru_type, only_active=False, user=user)

    if 'ids' not in request.data:
        return Response({'msg': 'No data sources provided'}, status=status.HTTP_400_BAD_REQUEST)

    datasource_ids = request.data.get('ids', [])
    service = DataSourceService(guru_type_object, user)
    
    try:
        service.delete_data_sources(datasource_ids)
        return Response({'msg': 'Data sources deleted successfully'}, status=status.HTTP_200_OK)
    except ValueError as e:
        return Response({'msg': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        logger.error(f'Error deleting data sources: {e}', exc_info=True)
        return Response({'msg': 'Internal server error'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


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
    
    if request.method == 'POST':
        if settings.ENV == 'selfhosted':
            user = None
        else:
            user = request.user
        
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

        # Check Jira issue limits
        jira_urls = json.loads(request.data.get('jira_urls', '[]'))
        if jira_urls:
            is_allowed, error_msg = guru_type_obj.check_datasource_limits(user, jira_urls_count=len(jira_urls))
            if not is_allowed:
                return Response({'msg': error_msg}, status=status.HTTP_400_BAD_REQUEST)
        
        # Check Zendesk ticket limits
        zendesk_urls = json.loads(request.data.get('zendesk_urls', '[]'))
        if zendesk_urls:
            is_allowed, error_msg = guru_type_obj.check_datasource_limits(user, zendesk_urls_count=len(zendesk_urls))
            if not is_allowed:
                return Response({'msg': error_msg}, status=status.HTTP_400_BAD_REQUEST)

        # Check Confluence page limits
        confluence_urls = json.loads(request.data.get('confluence_urls', '[]'))
        if confluence_urls:
            is_allowed, error_msg = guru_type_obj.check_datasource_limits(user, confluence_urls_count=len(confluence_urls))
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
    
    service = DataSourceService(guru_type_object, request.user)
    
    try:
        service.reindex_data_sources(datasource_ids)
        return Response({'msg': 'Data sources reindexed successfully'}, status=status.HTTP_200_OK)
    except ValueError as e:
        return Response({'msg': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        logger.error(f'Error reindexing data sources: {e}', exc_info=True)
        return Response({'msg': 'Internal server error'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

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
    github_repos = data.get('github_repos', guru_type_object.github_repos)

    try:
        github_repos = json.loads(github_repos)
    except Exception as e:
        logger.error(f'Error while parsing github repos: {e}', exc_info=True)
        return Response({'msg': 'Github repos must be a list of strings'}, status=status.HTTP_400_BAD_REQUEST)
    
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
    guru_type_object.github_repos = github_repos
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
@combined_auth
def guru_type_status(request, guru_type):
    guru_type_object: GuruType = get_guru_type_object(guru_type, only_active=False, user=request.user)
    is_ready = guru_type_object.ready
    return Response({'ready': is_ready}, status=status.HTTP_200_OK)


@api_view(['GET'])
@auth
def export_datasources(request):
    guru_type = request.data.get('guru_type', None)
    if not guru_type:
        return Response({"msg": "guru_type is required"}, status=status.HTTP_400_BAD_REQUEST)
    try:
        guru_type_object = get_guru_type_object(guru_type, only_active=False)
    except Exception as e:
        return Response({"msg": "Guru type does not exist"}, status=status.HTTP_400_BAD_REQUEST)
    try:
        data = {
            'data_sources': list(DataSource.objects.filter(guru_type=guru_type_object).values()),
        }
        return Response(data, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({"msg": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@auth
def export_questions(request):
    guru_type = request.data.get('guru_type', None)
    if not guru_type:
        return Response({"msg": "guru_type is required"}, status=status.HTTP_400_BAD_REQUEST)
    try:
        guru_type_object = get_guru_type_object(guru_type, only_active=False)
    except Exception as e:
        return Response({"msg": "Guru type does not exist"}, status=status.HTTP_400_BAD_REQUEST)
    try:
        data = {
            'questions': list(Question.objects.filter(guru_type=guru_type_object).values()),
        }
        return Response(data, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({"msg": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@follow_up_examples_auth
def follow_up_examples(request, guru_type):
    user = request.user
    widget = request.widget if hasattr(request, 'widget') else False

    if not settings.GENERATE_FOLLOW_UP_EXAMPLES:
        return Response([], status=status.HTTP_200_OK)
    
    if widget:
        guru_type_object = GuruType.objects.get(slug=guru_type)
    else:
        guru_type_object = get_guru_type_object(guru_type, only_active=True, user=user)

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

    if binge and not widget and not check_binge_auth(binge, user):
        return Response({'msg': 'User does not have access to this binge'}, status=status.HTTP_401_UNAUTHORIZED)

        
    last_question = search_question(
        user, 
        guru_type_object, 
        binge, 
        question_slug, 
        question_text,
        only_widget=widget,
        will_check_binge_auth=not widget
    )
    if not last_question:
        return Response({'msg': 'Question does not exist'}, status=status.HTTP_400_BAD_REQUEST)
    
    if last_question.follow_up_questions:
        return Response(last_question.follow_up_questions, status=status.HTTP_200_OK)
    
    # Get question history
    questions = [{'question': last_question.question, 'user_question': last_question.user_question}]
    ptr = last_question
    while ptr.parent:
        questions.append({'question': ptr.parent.question, 'user_question': ptr.parent.user_question})
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
    if settings.ENV == 'selfhosted':
        requester = OpenAIRequester()
    else:
        requester = GeminiRequester(settings.LARGE_GEMINI_MODEL)

    follow_up_examples = requester.generate_follow_up_questions(
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
@combined_auth
def follow_up_graph(request, guru_type):
    user = request.user
    guru_type_obj = get_guru_type_object(guru_type, user=user)

    binge_id = request.query_params.get('binge_id')
    if not binge_id:
        return Response({'msg': 'Binge ID is required'}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        binge = Binge.objects.get(id=binge_id)
    except Binge.DoesNotExist:
        return Response({'msg': 'Binge does not exist'}, status=status.HTTP_400_BAD_REQUEST)
    
    if not check_binge_auth(binge, user):
        return Response({'msg': 'User does not have access to this binge'}, status=status.HTTP_401_UNAUTHORIZED)
    
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
    user = request.user
    guru_type_object = get_guru_type_object(guru_type, only_active=True, user=user)
    
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

    binges = Binge.objects.exclude(root_question__source__in=[Question.Source.DISCORD, Question.Source.SLACK, Question.Source.GITHUB])
    
    # Base queryset
    if settings.ENV == 'selfhosted' or user.is_admin:
        binges = binges.order_by('-last_used')
    else:
        binges = binges.filter(owner=user).order_by('-last_used')
    
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

@api_view(['GET', 'POST', 'DELETE'])
@jwt_auth
def api_keys(request):
    if settings.ENV == 'selfhosted':
        user = User.objects.get(email=settings.ROOT_EMAIL)
    else:
        user = request.user
    
    if request.method == 'GET':
        api_keys = APIKey.objects.filter(user=user, integration=False)
        return Response(APIKeySerializer(api_keys, many=True).data, status=status.HTTP_200_OK)
    elif request.method == 'POST':
        # Check if user has reached the limit
        existing_keys_count = APIKey.objects.filter(user=user, integration=False).count()
        if existing_keys_count >= 5:
            return Response({'msg': 'You have reached the maximum limit of 5 API keys'}, status=status.HTTP_400_BAD_REQUEST)
            
        key = "gb-" + "".join(random.choices(string.ascii_lowercase + string.digits, k=30))
        api_key = APIKey.objects.create(user=user, name=request.data.get('name'), key=key)
        return Response({'msg': 'API key created successfully', 'key': key}, status=status.HTTP_200_OK)
    elif request.method == 'DELETE':
        try:
            api_key = APIKey.objects.get(key=request.data.get('api_key'), user=user, integration=False)
            api_key.delete()
            return Response({'msg': 'API key deleted successfully'}, status=status.HTTP_200_OK)
        except APIKey.DoesNotExist:
            return Response({'msg': 'API key does not exist'}, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET'])
def health_check(request):
    return Response({'status': 'healthy'}, status=status.HTTP_200_OK)


@api_view(['POST', 'DELETE'])
@jwt_auth
def manage_widget_ids(request, guru_type):
    guru_type_object = get_guru_type_object(guru_type, only_active=False, user=request.user)

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



@parser_classes([MultiPartParser, FormParser])
@api_view(['GET', 'POST', 'DELETE'])
@api_key_auth
@throttle_classes([ConcurrencyThrottleApiKey])
def api_data_sources(request, guru_type):
    """
    Unified endpoint for managing data sources.
    GET: Retrieve data sources with pagination
    POST: Create new data sources (YouTube URLs, website URLs)
    DELETE: Delete specified data sources
    """
    response_handler = DataSourceResponseHandler()
    
    try:
        guru_type_object = get_guru_type_object_by_maintainer(guru_type, request)
    except PermissionError:
        return response_handler.handle_error_response('Forbidden', status.HTTP_403_FORBIDDEN)
    except NotFoundError:
        return response_handler.handle_error_response(f'Guru type {guru_type} not found', status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        class DataSourcePagination(PageNumberPagination):
            page_size = 1000
            page_size_query_param = 'page_size'
            max_page_size = 1000
            
        data_sources_queryset = DataSource.objects.filter(guru_type=guru_type_object).order_by('-date_created')
        paginator = DataSourcePagination()
        paginated_data_sources = paginator.paginate_queryset(data_sources_queryset, request)
        serializer = DataSourceAPISerializer(paginated_data_sources, many=True)
        return paginator.get_paginated_response(serializer.data)

    elif request.method == 'POST':
        # Simply call the existing create_data_sources function
        return create_data_sources(request, guru_type)

    elif request.method == 'DELETE':
        return delete_data_sources(request, guru_type) 

@api_view(['POST'])
@api_key_auth
@throttle_classes([ConcurrencyThrottleApiKey])
def api_answer(request, guru_type):
    """
    API endpoint for answering questions.
    Supports both streaming and non-streaming responses.
    Creates a binge for root questions and supports follow-up questions within a binge.
    """
    # Initialize response handler
    response_handler = APIResponseHandler()
    
    # Get guru type
    guru_type_object = get_guru_type_object(guru_type, user=request.user)
    
    # Get request parameters
    question = request.data.get('question')
    stream = request.data.get('stream', False)
    binge_id = request.data.get('session_id')
    fetch_existing = request.data.get('fetch_existing', False)
    user = request.user
    api_type = request.api_type  # This is now set by the api_key_auth decorator

    # Initialize with default values
    binge = None
    parent = None

    # Handle binge if provided
    if binge_id:
        try:
            binge = Binge.objects.get(id=binge_id)
        except Exception:
            return response_handler.handle_error_response("Session not found. Code: S-900")
        
        if not check_binge_auth(binge, user):
            return response_handler.handle_error_response("Session not found. Code: S-901")
        
        # Find the last question in the binge as the parent
        parent = Question.objects.filter(binge=binge).order_by('-date_updated').first()

    integration_context = None
    if api_type in [APIType.GITHUB, APIType.SLACK, APIType.DISCORD]:
        assert request.integration is not None
        context_handler = get_context_handler(api_type, request.integration)
        if context_handler:
            if api_type == APIType.SLACK:
                # For Slack, combine channel_id and thread_ts into api_url
                channel_id = request.data.get('channel_id')
                thread_ts = request.data.get('thread_ts')
                if channel_id and thread_ts:
                    api_url = f"{channel_id}:{thread_ts}"
                else:
                    api_url = channel_id
            elif api_type == APIType.DISCORD:
                # For Discord, combine channel_id and thread_id into api_url
                channel_id = request.data.get('channel_id')
                thread_id = request.data.get('thread_id')
                if channel_id and thread_id:
                    api_url = f"{channel_id}:{thread_id}"
                elif channel_id:
                    api_url = f"{channel_id}:None"
                elif thread_id:
                    api_url = f"None:{thread_id}"
                else:
                    api_url = None
            elif api_type == APIType.GITHUB:
                api_url = request.data.get('github_api_url')
                
            integration_context = context_handler.get_context(api_url, request.integration.external_id)

    # Get API response
    api_response = api_ask(
        question=question,
        guru_type=guru_type_object,
        binge=binge,
        parent=parent,
        fetch_existing=fetch_existing,
        api_type=api_type,
        user=user,
        integration_context=integration_context
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
        elif binge and not binge.root_question:
            # Used in Slack and Discord bots
            binge.root_question = api_response.question_obj
            binge.save()
        return Response(response_data)
    
    # Handle streaming case
    if isinstance(api_response.content, Generator):
        if stream:
            return response_handler.handle_stream_response(api_response.content)
        
        # Process non-streaming response for generator content
        for _ in api_response.content:
            pass

        # Fetch updated question
        if not question:
            question = api_response.question
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

# @api_view(['PUT'])
# @api_key_auth
# @throttle_classes([ConcurrencyThrottleApiKey])
# def api_update_data_source_privacy(request, guru_type):
#     """Update privacy settings for data sources."""
#     response_handler = DataSourceResponseHandler()
    
#     try:
#         guru_type_object = get_guru_type_object_by_maintainer(guru_type, request)
#     except (PermissionError, NotFoundError) as e:
#         return response_handler.handle_error_response(str(e), status.HTTP_403_FORBIDDEN)

#     try:
#         service = DataSourceService(guru_type_object, request.user)
#         data_sources = request.data
#         if len(data_sources) == 0:
#             return response_handler.handle_error_response('No data sources provided', status.HTTP_400_BAD_REQUEST)
        
#         service.update_privacy_settings(data_sources)
#         return response_handler.handle_success_response('Data sources updated successfully')
#     except ValueError as e:
#         return response_handler.handle_error_response(str(e))
#     except Exception as e:
#         return response_handler.handle_error_response(f'Unexpected error: {str(e)}')


@api_view(['POST'])
@api_key_auth
@throttle_classes([ConcurrencyThrottleApiKey])
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
        if len(datasource_ids) == 0:
            return response_handler.handle_error_response('No data sources provided', status.HTTP_400_BAD_REQUEST)
        
        service.reindex_data_sources(datasource_ids)
        return response_handler.handle_success_response('Data sources reindexed successfully')
    except ValueError as e:
        return response_handler.handle_error_response(str(e))
    except Exception as e:
        return response_handler.handle_error_response(f'Unexpected error: {str(e)}')

@api_view(['GET', 'PUT'])
@jwt_auth
def manage_settings(request):
    """
    GET: Retrieve current settings (excluding sensitive data like API keys)
    PUT: Update settings
    """
    from core.utils import get_default_settings
    settings_obj = get_default_settings()

    if request.method == 'GET':
        settings_obj.save() # Save to trigger validation
        settings_obj.refresh_from_db()
        serializer = SettingsSerializer(settings_obj)
        return Response(serializer.data)

    elif request.method == 'PUT':
        serializer = SettingsSerializer(settings_obj, data=request.data, partial=True)
        if serializer.is_valid():
            if not request.data.get('openai_api_key_written'):
                serializer.validated_data['openai_api_key'] = settings_obj.openai_api_key
            if not request.data.get('firecrawl_api_key_written'):
                serializer.validated_data['firecrawl_api_key'] = settings_obj.firecrawl_api_key
            if not request.data.get('youtube_api_key_written'):
                serializer.validated_data['youtube_api_key'] = settings_obj.youtube_api_key
            
            try:
                serializer.save()
                return Response(serializer.data)
            except ValidationError as e:
                logger.error(f"Validation error in manage_settings: {e}", exc_info=True)
                return Response(
                    {'errors': e.message_dict if hasattr(e, 'message_dict') else {'error': str(e)}},
                    status=status.HTTP_400_BAD_REQUEST
                )
            except IntegrityError as e:
                logger.error(f"Integrity error in manage_settings: {e}", exc_info=True)
                return Response({'msg': str(e)}, status=status.HTTP_400_BAD_REQUEST)
            except Exception as e:
                logger.error(f"Error in manage_settings: {e}", exc_info=True)
                return Response({'msg': 'Internal server error'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@auth
def parse_sitemap(request):
    """
    Parse URLs from a sitemap XML file.
    If given a sitemap index, it will fetch and parse all referenced sitemaps.
    Expects a POST request with a 'sitemap_url' parameter that ends with .xml
    Returns a list of all URLs found across all sitemaps.
    """
    sitemap_url = request.data.get('sitemap_url')
    
    if not sitemap_url:
        return Response({'msg': 'Sitemap URL is required'}, status=status.HTTP_400_BAD_REQUEST)
        
    if not sitemap_url.endswith('.xml'):
        return Response({'msg': 'Sitemap URL must end with .xml'}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        # Validate URL format
        from urllib.parse import urlparse
        parsed_url = urlparse(sitemap_url)
        if not all([parsed_url.scheme, parsed_url.netloc]):
            return Response({'msg': 'Invalid URL format'}, status=status.HTTP_400_BAD_REQUEST)
            
        def fetch_and_parse_sitemap(url):
            """Helper function to fetch and parse a single sitemap."""
            try:
                response = requests.get(url, timeout=10)
                response.raise_for_status()
                return ET.fromstring(response.content)
            except Exception as e:
                logger.error(f"Error fetching sitemap {url}: {e}", exc_info=True)
                return None

        def extract_urls_from_sitemap(root):
            """Extract URLs from a standard sitemap."""
            if not root:
                return []
                
            namespaces = {'ns': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
            urls = []
            
            # Find all URL elements
            loc_elements = root.findall('.//ns:url/ns:loc', namespaces)
            for loc in loc_elements:
                url = loc.text.strip()
                urls.append(url)
                
            return urls

        def process_sitemap_index(root):
            """Process a sitemap index and return all URLs from referenced sitemaps."""
            if not root:
                return []
                
            namespaces = {'ns': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
            all_urls = []
            
            # Find all sitemap references
            sitemap_elements = root.findall('.//ns:sitemap/ns:loc', namespaces)
            
            for sitemap in sitemap_elements:
                sitemap_url = sitemap.text.strip()
                # Fetch and parse the referenced sitemap
                sitemap_root = fetch_and_parse_sitemap(sitemap_url)
                if sitemap_root is not None:
                    # Extract URLs from this sitemap
                    urls = extract_urls_from_sitemap(sitemap_root)
                    all_urls.extend(urls)
            
            return all_urls

        # Fetch and parse the initial sitemap/index
        import requests
        from xml.etree import ElementTree as ET
        
        root = fetch_and_parse_sitemap(sitemap_url)
        if not root:
            return Response({'msg': 'Error fetching sitemap'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        # Determine if this is a sitemap index or regular sitemap
        urls = []
        if root.tag.endswith('sitemapindex'):
            # Process sitemap index
            urls = process_sitemap_index(root)
        elif root.tag.endswith('urlset'):
            # Process regular sitemap
            urls = extract_urls_from_sitemap(root)
        else:
            return Response({
                'msg': 'Invalid sitemap format. Root element must be <urlset> or <sitemapindex>.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if not urls:
            return Response({
                'msg': 'No URLs found in the sitemap(s)',
                'urls': [],
                'total_urls': 0
            }, status=status.HTTP_200_OK)
        
        return Response({
            'urls': urls,
            'total_urls': len(urls)
        }, status=status.HTTP_200_OK)
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching sitemap: {e}", exc_info=True)
        return Response({'msg': 'Error fetching sitemap'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    except ET.ParseError as e:
        logger.error(f"Error parsing XML: {e}", exc_info=True)
        return Response({'msg': 'Invalid XML format'}, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        logger.error(f"Unexpected error parsing sitemap: {e}", exc_info=True)
        return Response({'msg': 'Error processing sitemap'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@jwt_auth
def start_crawl_admin(request, guru_slug):
    try:
        data, return_status = CrawlService.start_crawl(
            guru_slug,
            request.user,
            request.data.get('url'),
            source=CrawlState.Source.UI
        )
    except Exception as e:
        return Response({'msg': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    return Response(data, status=return_status)

@api_view(['POST'])
@api_key_auth
@throttle_classes([ConcurrencyThrottleApiKey])
def start_crawl_api(request, guru_slug):
    try:
        data, return_status = CrawlService.start_crawl(
            guru_slug,
            request.user,
            request.data.get('url'),
            source=CrawlState.Source.API
        )
    except Exception as e:
        return Response({'msg': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    return Response(data, status=return_status)

@api_view(['POST'])
@jwt_auth
def stop_crawl_admin(request, crawl_id):
    try:
        data, return_status = CrawlService.stop_crawl(
            request.user,
            crawl_id
        )
    except Exception as e:
        return Response({'msg': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    return Response(data, status=return_status)

@api_view(['POST'])
@api_key_auth
@throttle_classes([ConcurrencyThrottleApiKey])
def stop_crawl_api(request, crawl_id):
    try:
        data, return_status = CrawlService.stop_crawl(
            request.user,
            crawl_id
        )
    except Exception as e:
        return Response({'msg': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    return Response(data, status=return_status)

@api_view(['GET'])
@jwt_auth
def get_crawl_status_admin(request, crawl_id):
    try:
        data, return_status = CrawlService.get_crawl_status(
            request.user,
            crawl_id
        )
    except Exception as e:
        return Response({'msg': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    return Response(data, status=return_status)

@api_view(['GET'])
@api_key_auth
@throttle_classes([ConcurrencyThrottleApiKey])
def get_crawl_status_api(request, crawl_id):
    try:
        data, return_status = CrawlService.get_crawl_status(
            request.user,
            crawl_id
        )
    except Exception as e:
        return Response({'msg': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    return Response(data, status=return_status)

@api_view(['POST'])
@combined_auth
def submit_guru_creation_form(request):
    """
    Handle submission of guru creation forms.
    """
    try:
        name = request.data.get('name')
        email = request.data.get('email')
        github_repo = request.data.get('github_repo')
        docs_url = request.data.get('docs_url')
        use_case = request.data.get('use_case')
        source = request.data.get('source', 'unknown')

        if not all([name, email, docs_url]):
            return Response({
                'error': 'Missing required fields. Please provide name, email, and documentation root url.'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Create form submission
        GuruCreationForm.objects.create(
            name=name,
            email=email,
            github_repo=github_repo,
            docs_url=docs_url,
            use_case=use_case,
            source=source
        )

        return Response({
            'message': 'Your guru creation request has been submitted successfully.'
        }, status=status.HTTP_201_CREATED)

    except Exception as e:
        logger.error(f'Error processing guru creation form: {e}', exc_info=True)
        return Response({
            'error': 'An error occurred while processing your request.'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@jwt_auth
def fetch_youtube_playlist_admin(request):
    url = request.data.get('url')
    if not url:
        return Response({'error': 'URL is required'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        data, return_status = YouTubeService.fetch_playlist(url)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    return Response(data, status=return_status)

@api_view(['POST'])
@api_key_auth
@throttle_classes([ConcurrencyThrottleApiKey])
def fetch_youtube_playlist_api(request):
    url = request.data.get('url')
    if not url:
        return Response({'error': 'URL is required'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        data, return_status = YouTubeService.fetch_playlist(url)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    return Response(data, status=return_status)

@api_view(['POST'])
@jwt_auth
def fetch_youtube_channel_admin(request):
    url = request.data.get('url')
    if not url:
        return Response({'error': 'URL is required'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        data, return_status = YouTubeService.fetch_channel(url)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    return Response(data, status=return_status)

@api_view(['POST'])
@api_key_auth
@throttle_classes([ConcurrencyThrottleApiKey])
def fetch_youtube_channel_api(request):
    url = request.data.get('url')
    if not url:
        return Response({'error': 'URL is required'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        data, return_status = YouTubeService.fetch_channel(url)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    return Response(data, status=return_status)


@api_view(['POST'])
@jwt_auth
def validate_ollama_url(request):
    """
    Validate if an Ollama URL is accessible and return available models
    """
    url = request.data.get('url')
    if not url:
        return Response({'error': 'URL is required'}, status=400)
    
    requester = OllamaRequester(url)
    is_healthy, models, error = requester.check_ollama_health()
    
    if not is_healthy:
        return Response({
            'is_valid': False,
            'error': error
        }, status=400)
    
    return Response({
        'is_valid': True,
        'models': models
    })
