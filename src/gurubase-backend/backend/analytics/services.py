from django.db.models import Q, Count, Prefetch
from django.core.cache import cache
from core.models import Question, OutOfContextQuestion, DataSource, GithubFile
from .utils import get_date_range, calculate_percentage_change, format_filter_name_for_display, map_filter_to_source
import hashlib
import json
import time
class AnalyticsService:
    CACHE_TTL = 300  # 5 minutes cache

    @staticmethod
    def _get_cache_key(prefix, *args):
        """Generate a cache key based on prefix and arguments."""
        key = f"analytics_{prefix}_{'_'.join(str(arg) for arg in args)}"
        return hashlib.md5(key.encode()).hexdigest()

    @staticmethod
    def get_stats_for_period(guru_type, start_date, end_date):
        """Get statistics for a specific time period with caching."""
        cache_key = AnalyticsService._get_cache_key('stats', guru_type.id, start_date.isoformat(), end_date.isoformat())
        cached_data = cache.get(cache_key)
        
        if cached_data:
            return cached_data

        questions_start = time.time()
        # Optimize queries using annotations and single database hits
        questions = Question.objects.filter(
            guru_type=guru_type,
            date_created__gte=start_date,
            date_created__lte=end_date
        )
        
        total_questions = questions.count()
        questions_end = time.time()
        
        out_of_context_start = time.time()
        out_of_context = OutOfContextQuestion.objects.filter(
            guru_type=guru_type,
            date_created__gte=start_date,
            date_created__lte=end_date
        ).count()
        out_of_context_end = time.time()
        
        # Extract unique referenced links in a single pass
        referenced_links_start = time.time()
        referenced_links = set()
        for refs in questions.values_list('references', flat=True):
            if refs:
                for ref in refs:
                    link = ref.get('link')
                    if link:
                        referenced_links.add(link)

        # Optimize data source queries using IN clause
        referenced_sources = DataSource.objects.filter(
            guru_type=guru_type,
            url__in=referenced_links
        ).count()

        referenced_github_files = GithubFile.objects.filter(
            link__in=referenced_links
        ).count()

        referenced_links_end = time.time()
        
        result = (total_questions, out_of_context, referenced_sources + referenced_github_files)
        cache.set(cache_key, result, AnalyticsService.CACHE_TTL)
        return result

    @staticmethod
    def get_stats_data(guru_type, interval='today'):
        """Get analytics statistics with comparison to previous period."""
        cache_key = AnalyticsService._get_cache_key('stats_data', guru_type.id, interval)
        cached_data = cache.get(cache_key)
        
        if cached_data:
            return cached_data

        current_start_date, current_end_date = get_date_range(interval)
        
        current_total, current_out_of_context, current_referenced_sources = AnalyticsService.get_stats_for_period(
            guru_type, current_start_date, current_end_date
        )
        
        previous_start = current_start_date - (current_end_date - current_start_date)
        previous_total, previous_out_of_context, previous_referenced_sources = AnalyticsService.get_stats_for_period(
            guru_type, previous_start, current_start_date
        )
        
        result = {
            'total_questions': {
                'value': current_total,
                'percentage_change': calculate_percentage_change(current_total, previous_total)
            },
            'out_of_context': {
                'value': current_out_of_context,
                'percentage_change': calculate_percentage_change(current_out_of_context, previous_out_of_context)
            },
            'referenced_sources': {
                'value': current_referenced_sources,
                'percentage_change': calculate_percentage_change(current_referenced_sources, previous_referenced_sources)
            }
        }
        
        cache.set(cache_key, result, AnalyticsService.CACHE_TTL)
        return result

    @staticmethod
    def get_paginated_data(queryset, page, page_size=10):
        """Helper method to paginate queryset with optimized counting."""
        if isinstance(queryset, list):
            total_items = len(queryset)
        else:
            # Use optimized count() for querysets
            total_items = queryset.count()
        
        total_pages = (total_items + page_size - 1) // page_size
        page = min(max(1, page), total_pages) if total_pages > 0 else 1
        
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        
        # Use optimized slicing for querysets
        items = queryset[start_idx:end_idx]
        
        return {
            'items': items,
            'total_pages': total_pages,
            'current_page': page,
            'total_items': total_items
        }

    @staticmethod
    def get_available_filters(metric_type):
        """Get available filters based on metric type with caching."""
        cache_key = AnalyticsService._get_cache_key('filters', metric_type)
        cached_filters = cache.get(cache_key)
        
        if cached_filters:
            return cached_filters

        if metric_type in ['questions', 'out_of_context']:
            filters = [
                {'value': 'all', 'label': 'All'},
                {'value': 'user', 'label': 'Gurubase UI'},
                {'value': 'widget', 'label': 'Widget'},
                {'value': 'api', 'label': 'API'},
                {'value': 'discord', 'label': 'Discord'},
                {'value': 'slack', 'label': 'Slack'},
            ]
        elif metric_type == 'referenced_sources':
            filters = [
                {'value': 'all', 'label': 'All'},
                {'value': 'github_repo', 'label': 'Codebase'},
                {'value': 'pdf', 'label': 'PDF'},
                {'value': 'website', 'label': 'Website'},
                {'value': 'youtube', 'label': 'YouTube'},
            ]
        else:
            filters = []
            
        cache.set(cache_key, filters, AnalyticsService.CACHE_TTL * 4)  # Cache filters longer as they rarely change
        return filters

    @staticmethod
    def get_data_source_questions(guru_type, data_source_url, filter_type, interval, page, search_query=None, sort_order='desc'):
        """Get questions that reference a specific data source with search and sort functionality."""
        cache_key = AnalyticsService._get_cache_key('data_source_questions', 
            guru_type.id, data_source_url, filter_type or 'all', interval, page, search_query, sort_order)
        cached_data = cache.get(cache_key)
        
        if cached_data:
            return cached_data

        start_date, end_date = get_date_range(interval)
        
        try:
            data_source = DataSource.objects.get(guru_type=guru_type, url=data_source_url)
            is_github = False
        except DataSource.DoesNotExist:
            try:
                data_source = GithubFile.objects.select_related('data_source').get(link=data_source_url)
                is_github = True
            except GithubFile.DoesNotExist:
                return None
        
        # Build the base queryset
        queryset = Question.objects.filter(
            guru_type=guru_type,
            date_created__gte=start_date,
            date_created__lte=end_date,
            references__contains=[{'link': data_source_url}]
        )
        
        # Apply filter type if specified
        if filter_type and filter_type != 'all':
            source_value = map_filter_to_source(filter_type)
            if source_value:
                queryset = queryset.filter(source__iexact=source_value)
        
        # Apply search filter if query exists
        if search_query:
            queryset = queryset.filter(question__icontains=search_query)
        
        # Apply sorting
        order_by = 'date_created' if sort_order == 'asc' else '-date_created'
        queryset = queryset.order_by(order_by)
        
        paginated_data = AnalyticsService.get_paginated_data(queryset, page)
        
        results = [{
            'date': item.date_created.isoformat(),
            'title': item.question,
            'link': item.frontend_url,
            'source': format_filter_name_for_display(item.source)
        } for item in paginated_data['items']]
        
        result = {
            'results': results,
            'total_pages': paginated_data['total_pages'],
            'current_page': paginated_data['current_page'],
            'total_items': paginated_data['total_items'],
            'available_filters': AnalyticsService.get_available_filters('questions')
        }
        
        cache.set(cache_key, result, AnalyticsService.CACHE_TTL)
        return result 