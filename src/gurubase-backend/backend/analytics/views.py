import logging
import traceback
from django.http import HttpResponse
from datetime import datetime

from rest_framework.response import Response
from rest_framework import status
from rest_framework.decorators import api_view, throttle_classes
from rest_framework.exceptions import ValidationError
from core.throttling import ConcurrencyThrottleApiKey

from core.auth import (
    api_key_auth,
    jwt_auth,
)
from .decorators import guru_type_required
from .services import AnalyticsService
from .utils import get_date_range, get_histogram_increment, format_filter_name_for_display, map_filter_to_source

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
        logger.error(f"Error in analytics_stats: {traceback.format_exc()}", exc_info=True)
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
        logger.error(f"Error in analytics_histogram: {traceback.format_exc()}", exc_info=True)
        return Response({'msg': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        logger.error(f"Error in analytics_histogram: {traceback.format_exc()}", exc_info=True)
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
        sort_order = request.query_params.get('sort_order', 'desc').lower()
        start_time = request.query_params.get('start_time', '').strip()
        end_time = request.query_params.get('end_time', '').strip()
        
        if sort_order not in ['asc', 'desc']:
            sort_order = 'desc'
        
        try:
            page = max(1, int(request.query_params.get('page', 1)))
        except ValueError:
            page = 1
        
        if not metric_type:
            raise ValidationError('Metric type is required')
            
        if metric_type not in ['questions', 'out_of_context', 'referenced_sources']:
            raise ValidationError('Invalid metric type')
        
        # Get date range - use custom range if provided, otherwise use interval
        if start_time and end_time:
            try:
                start_date = datetime.fromisoformat(start_time)
                end_date = datetime.fromisoformat(end_time)
                if start_date > end_date:
                    raise ValidationError('Start time must be before end time')
            except ValueError:
                raise ValidationError('Invalid date format. Use ISO format (YYYY-MM-DDTHH:MM:SS)')
        else:
            start_date, end_date = get_date_range(interval)
        
        # Get available filters for the metric type
        available_filters = AnalyticsService.get_available_filters(metric_type)
        
        # Get filtered data based on metric type
        if metric_type == 'questions':
            queryset = AnalyticsService._get_filtered_questions(
                guru_type, start_date, end_date, filter_type, search_query, sort_order
            )
            paginated_data = AnalyticsService.get_paginated_data(queryset, page)
            
            results = [{
                'date': item.date_created.isoformat(),
                'type': format_filter_name_for_display(item.source),
                'title': item.user_question,
                'truncated_title': item.user_question[:75] + '...' if len(item.user_question) > 75 else item.user_question,
                'link': item.frontend_url,
                'trust_score': int(item.trust_score * 100)
            } for item in paginated_data['items']]
            
        elif metric_type == 'out_of_context':
            queryset = AnalyticsService._get_filtered_out_of_context(
                guru_type, start_date, end_date, filter_type, search_query, sort_order
            )
            paginated_data = AnalyticsService.get_paginated_data(queryset, page)
            
            results = [{
                'date': item.date_created.isoformat(),
                'type': format_filter_name_for_display(item.source),
                'title': item.user_question,
                'truncated_title': item.user_question[:75] + '...' if len(item.user_question) > 75 else item.user_question,
            } for item in paginated_data['items']]
            
        else:  # referenced_sources
            sources = AnalyticsService._get_filtered_referenced_sources(
                guru_type, start_date, end_date, filter_type, search_query, sort_order
            )
            
            # Format results for table display
            results = [{
                'date': source['date'],
                'type': source['type'],
                'title': source['title'],
                'truncated_title': source['title'][:60] + '...' if len(source['title']) > 60 else source['title'],
                'link': source['url'],
                'reference_count': source['reference_count']
            } for source in sources]
            
            # Paginate the results
            paginated_data = AnalyticsService.get_paginated_data(results, page)
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
        logger.error(f"Error in analytics_table: {traceback.format_exc()}", exc_info=True)
        return Response({'msg': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        logger.error(f"Error in analytics_table: {traceback.format_exc()}", exc_info=True)
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
        search_query = request.query_params.get('search', '').strip()
        sort_order = request.query_params.get('sort_order', 'desc').lower()
        
        if sort_order not in ['asc', 'desc']:
            sort_order = 'desc'
        
        if not data_source_url:
            raise ValidationError('Data source URL is required')

        try:
            page = max(1, int(request.query_params.get('page', 1)))
        except ValueError:
            page = 1
            
        result = AnalyticsService.get_data_source_questions(
            guru_type, 
            data_source_url, 
            filter_type, 
            interval, 
            page,
            search_query,
            sort_order
        )
        
        if result is None:
            return Response({'msg': 'Data source not found'}, status=status.HTTP_404_NOT_FOUND)
            
        return Response(result, status=status.HTTP_200_OK)
    except ValidationError as e:
        logger.error(f"Error in data_source_questions: {traceback.format_exc()}", exc_info=True)
        return Response({'msg': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        logger.error(f"Error in data_source_questions: {traceback.format_exc()}", exc_info=True)
        return Response({'msg': 'Internal server error'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@jwt_auth
@guru_type_required
def export_analytics(request, guru_type):
    """Export analytics data in Excel format with multiple sheets."""
    try:
        export_type = request.data.get('export_type', 'xlsx')
        interval = request.data.get('interval', 'today')
        
        # Get filters from query params, defaulting to 'all' if not specified
        filters = {
            'questions': request.data.get('filters', {}).get('questions', 'all'),
            'out_of_context': request.data.get('filters', {}).get('out_of_context', 'all'),
            'referenced_sources': request.data.get('filters', {}).get('referenced_sources', 'all')
        }
        
        # Get the formatted data to export
        export_data = AnalyticsService.export_analytics_data(guru_type, export_type, interval, filters)
        
        if not export_data:
            return Response({'msg': 'No data found to export'}, status=status.HTTP_404_NOT_FOUND)
        
        # Set content type and filename based on export type
        content_types = {
            'xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'csv': 'application/zip',  # Changed to zip for CSV exports
            'json': 'application/json'
        }
        file_extensions = {
            'xlsx': 'xlsx',
            'csv': 'zip',  # Changed to zip for CSV exports
            'json': 'json'
        }
        
        content_type = content_types.get(export_type)
        file_extension = file_extensions.get(export_type)
        
        # Set filename based on export type
        filename = f'analytics_{guru_type}_{interval}_{int(datetime.now().timestamp())}.{file_extension}'
            
        # Create response and set headers
        response = HttpResponse(export_data, content_type=content_type)
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        response['Access-Control-Expose-Headers'] = 'Content-Disposition'  # Explicitly expose the header for CORS
        
        return response
        
    except ValidationError as e:
        logger.error(f"Error in export_analytics: {traceback.format_exc()}", exc_info=True)
        return Response({'msg': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        logger.error(f"Error in export_analytics: {traceback.format_exc()}", exc_info=True)
        return Response({'msg': 'Internal server error'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@api_key_auth
@throttle_classes([ConcurrencyThrottleApiKey])
@guru_type_required
def export_analytics_api(request, guru_type):
    """Export analytics data in specified format through API endpoint."""
    try:
        export_type = request.data.get('export_type', 'xlsx')
        interval = request.data.get('interval', 'today')
        
        # Get filters from query params, defaulting to 'all' if not specified
        filters = {
            'questions': request.data.get('filters', {}).get('questions', 'all'),
            'out_of_context': request.data.get('filters', {}).get('out_of_context', 'all'),
            'referenced_sources': request.data.get('filters', {}).get('referenced_sources', 'all')
        }
        
        # Get the formatted data to export
        export_data = AnalyticsService.export_analytics_data(guru_type, export_type, interval, filters)
        
        if not export_data:
            return Response({'msg': 'No data found to export'}, status=status.HTTP_404_NOT_FOUND)
        
        # Set content type and filename based on export type
        content_types = {
            'xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'csv': 'application/zip',  # Changed to zip for CSV exports
            'json': 'application/json'
        }
        file_extensions = {
            'xlsx': 'xlsx',
            'csv': 'zip',  # Changed to zip for CSV exports
            'json': 'json'
        }
        
        content_type = content_types.get(export_type)
        file_extension = file_extensions.get(export_type)
        
        # Set filename based on export type
        filename = f'analytics_{guru_type}_{interval}_{int(datetime.now().timestamp())}.{file_extension}'
            
        # Create response and set headers
        response = HttpResponse(export_data, content_type=content_type)
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        response['Access-Control-Expose-Headers'] = 'Content-Disposition'
        
        return response
        
    except ValidationError as e:
        logger.error(f"Error in export_analytics_api: {traceback.format_exc()}", exc_info=True)
        return Response({'msg': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        logger.error(f"Error in export_analytics_api: {traceback.format_exc()}", exc_info=True)
        return Response({'msg': 'Internal server error'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
