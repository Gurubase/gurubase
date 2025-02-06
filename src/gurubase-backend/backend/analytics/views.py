import logging
from core.models import Question, OutOfContextQuestion, DataSource, GithubFile
import time

from rest_framework.response import Response
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.exceptions import ValidationError

from core.auth import (
    jwt_auth,
)
from core.models import (
    DataSource,
    Question,
)
from .decorators import guru_type_required
from .services import AnalyticsService
from .utils import get_date_range, get_histogram_increment, format_filter_name, map_filter_to_source

logger = logging.getLogger(__name__)

# Create your views here.
@api_view(['GET'])
@jwt_auth
@guru_type_required
def analytics_stats(request, guru_type):
    """Get analytics stat cards data for a specific time period."""
    
    try:
        interval = request.query_params.get('interval', 'today')
        
        stats_data = AnalyticsService.get_stats_data(guru_type, interval)
        
        return Response({'data': stats_data}, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({'msg': 'Internal server error'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@jwt_auth
@guru_type_required
def analytics_histogram(request, guru_type):
    """Get analytics histogram data for a specific metric type and time period."""
    
    try:
        metric_type = request.query_params.get('metric_type')
        interval = request.query_params.get('interval', 'today')
        
        if not metric_type:
            raise ValidationError('Metric type is required')
            
        if metric_type not in ['questions', 'out_of_context']:
            raise ValidationError('Invalid metric type')
        
        start_date, end_date = get_date_range(interval)
        increment, format_data_point = get_histogram_increment(start_date, end_date, interval)
        
        result = []
        current = start_date
        
        metric_map = {
            'questions': 0,
            'out_of_context': 1,
            'referenced_sources': 2
        }
        
        while current < end_date:
            next_slot = min(current + increment, end_date)
            slot_stats = AnalyticsService.get_stats_for_period(guru_type, current, next_slot)
            
            value = slot_stats[metric_map[metric_type]]
            data_point = format_data_point(current, next_slot)
            data_point['value'] = value
            
            result.append(data_point)
            current = next_slot
        
        return Response({'data': result}, status=status.HTTP_200_OK)
    except ValidationError as e:
        return Response({'msg': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return Response({'msg': 'Internal server error'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@jwt_auth
@guru_type_required
def analytics_table(request, guru_type):
    """Get analytics table data for a specific metric type with pagination."""
    
    try:
        metric_type = request.query_params.get('metric_type')
        interval = request.query_params.get('interval', 'today')
        filter_type = request.query_params.get('filter_type')
        search_query = request.query_params.get('search', '').strip()
        
        try:
            page = max(1, int(request.query_params.get('page', 1)))
        except ValueError:
            page = 1
        
        if not metric_type:
            raise ValidationError('Metric type is required')
            
        if metric_type not in ['questions', 'out_of_context', 'referenced_sources']:
            raise ValidationError('Invalid metric type')
        
        # Get date range for the interval
        start_date, end_date = get_date_range(interval)
        
        # Get available filters for the metric type
        available_filters = AnalyticsService.get_available_filters(metric_type)
        
        # Build base queryset
        if metric_type == 'questions':
            queryset = Question.objects.filter(
                guru_type=guru_type,
                date_created__gte=start_date,
                date_created__lte=end_date
            )
            
            if filter_type and filter_type != 'all':
                source_value = map_filter_to_source(filter_type)
                if source_value:
                    queryset = queryset.filter(source__iexact=source_value)
                    
            if search_query:
                queryset = queryset.filter(question__icontains=search_query)
                
            queryset = queryset.order_by('-date_created')
            paginated_data = AnalyticsService.get_paginated_data(queryset, page)
            
            results = [{
                'date': item.date_created.isoformat(),
                'type': format_filter_name(item.source),
                'title': item.question,
                'link': item.frontend_url
            } for item in paginated_data['items']]
            
        elif metric_type == 'out_of_context':
            queryset = OutOfContextQuestion.objects.filter(
                guru_type=guru_type,
                date_created__gte=start_date,
                date_created__lte=end_date
            )
            
            if filter_type and filter_type != 'all':
                source_value = map_filter_to_source(filter_type)
                if source_value:
                    queryset = queryset.filter(source__iexact=source_value)
                    
            if search_query:
                queryset = queryset.filter(question__icontains=search_query)
                
            queryset = queryset.order_by('-date_created')
            paginated_data = AnalyticsService.get_paginated_data(queryset, page)
            
            results = [{
                'date': item.date_created.isoformat(),
                'type': format_filter_name(item.source),
                'title': item.question,
            } for item in paginated_data['items']]
            
        else:  # referenced_sources
            # Get questions with references
            questions = Question.objects.filter(
                guru_type=guru_type,
                date_created__gte=start_date,
                date_created__lte=end_date
            ).values('references')
            
            # Extract referenced links and count occurrences
            reference_counts = {}
            referenced_links = []
            
            for question in questions:
                for ref in question.get('references', []):
                    link = ref.get('link')
                    if not link:
                        continue
                    referenced_links.append(link)
                    reference_counts[link] = reference_counts.get(link, 0) + 1
            
            # Get data sources based on filter
            if filter_type == 'all' or not filter_type:
                data_sources = list(DataSource.objects.filter(
                    guru_type=guru_type,
                    url__in=referenced_links
                ))
                github_files = list(GithubFile.objects.filter(
                    link__in=referenced_links
                ).select_related('data_source'))
            elif filter_type == 'github_repo':
                data_sources = []
                github_files = list(GithubFile.objects.filter(
                    link__in=referenced_links
                ).select_related('data_source'))
            else:
                data_sources = list(DataSource.objects.filter(
                    guru_type=guru_type,
                    url__in=referenced_links,
                    type__iexact=filter_type
                ))
                github_files = []
            
            # Combine and sort results
            combined_sources = []
            
            for ds in data_sources:
                combined_sources.append({
                    'date': ds.date_created.isoformat(),
                    'type': format_filter_name(ds.type),
                    'title': ds.title or ds.url,
                    'link': ds.url,
                    'reference_count': reference_counts.get(ds.url, 0)
                })
            
            for gf in github_files:
                combined_sources.append({
                    'date': gf.data_source.date_created.isoformat(),
                    'type': 'Codebase',
                    'title': gf.title,
                    'link': gf.link,
                    'reference_count': reference_counts.get(gf.link, 0)
                })
            
            # Sort by reference count
            combined_sources.sort(key=lambda x: x['reference_count'], reverse=True)
            
            # Apply search filter to titles if search query exists
            if search_query:
                combined_sources = [
                    source for source in combined_sources 
                    if search_query.lower() in source['title'].lower()
                ]
            
            # Paginate the sorted results
            paginated_data = AnalyticsService.get_paginated_data(combined_sources, page)
            results = paginated_data['items']
        
        response_data = {
            'results': results,
            'total_pages': paginated_data['total_pages'],
            'current_page': paginated_data['current_page'],
            'total_items': paginated_data['total_items'],
            'available_filters': available_filters
        }
        
        return Response(response_data, status=status.HTTP_200_OK)
    except ValidationError as e:
        return Response({'msg': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return Response({'msg': 'Internal server error'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@jwt_auth
@guru_type_required
def data_source_questions(request, guru_type):
    """Get paginated list of questions that reference a specific data source."""
    try:
        data_source_url = request.query_params.get('url')
        filter_type = request.query_params.get('filter_type')
        interval = request.query_params.get('interval', 'today')
        
        if not data_source_url:
            raise ValidationError('Data source URL is required')

        try:
            page = max(1, int(request.query_params.get('page', 1)))
        except ValueError:
            page = 1
            
        result = AnalyticsService.get_data_source_questions(
            guru_type, data_source_url, filter_type, interval, page
        )
        
        if result is None:
            return Response({'msg': 'Data source not found'}, status=status.HTTP_404_NOT_FOUND)
            
        return Response(result, status=status.HTTP_200_OK)
    except ValidationError as e:
        return Response({'msg': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        logger.error(f"Error in data_source_questions: {str(e)}", exc_info=True)
        return Response({'msg': 'Internal server error'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
