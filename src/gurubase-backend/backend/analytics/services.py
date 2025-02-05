from django.db.models import Q
from core.models import Question, OutOfContextQuestion, DataSource, GithubFile
from .utils import get_date_range, calculate_percentage_change, format_filter_name

class AnalyticsService:
    @staticmethod
    def get_stats_for_period(guru_type, start_date, end_date):
        """Get statistics for a specific time period."""
        total_questions = Question.objects.filter(
            guru_type=guru_type,
            date_created__gte=start_date,
            date_created__lte=end_date
        ).count()
        
        out_of_context = OutOfContextQuestion.objects.filter(
            guru_type=guru_type,
            date_created__gte=start_date,
            date_created__lte=end_date
        ).count()
        
        questions = Question.objects.filter(
            guru_type=guru_type,
            date_created__gte=start_date,
            date_created__lte=end_date
        )
        
        referenced_links = set()
        for question in questions:
            for ref in question.references:
                link = ref.get('link')
                if link:
                    referenced_links.add(link)
        
        referenced_sources = DataSource.objects.filter(
            guru_type=guru_type,
            url__in=referenced_links
        ).count()

        referenced_github_files = GithubFile.objects.filter(
            link__in=referenced_links
        ).count()
        
        return total_questions, out_of_context, referenced_sources + referenced_github_files

    @staticmethod
    def get_stats_data(guru_type, interval='today'):
        """Get analytics statistics with comparison to previous period."""
        current_start_date, current_end_date = get_date_range(interval)
        
        current_total, current_out_of_context, current_referenced_sources = AnalyticsService.get_stats_for_period(
            guru_type, current_start_date, current_end_date
        )
        
        previous_start = current_start_date - (current_end_date - current_start_date)
        previous_total, previous_out_of_context, previous_referenced_sources = AnalyticsService.get_stats_for_period(
            guru_type, previous_start, current_start_date
        )
        
        return {
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

    @staticmethod
    def get_paginated_data(queryset, page, page_size=10):
        """Helper method to paginate queryset."""
        total_items = len(queryset) if isinstance(queryset, list) else queryset.count()
        total_pages = (total_items + page_size - 1) // page_size
        
        page = min(max(1, page), total_pages) if total_pages > 0 else 1
        
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        
        return {
            'items': queryset[start_idx:end_idx],
            'total_pages': total_pages,
            'current_page': page,
            'total_items': total_items
        }

    @staticmethod
    def get_available_filters(metric_type):
        """Get available filters based on metric type."""
        if metric_type in ['questions', 'out_of_context']:
            return [
                {'value': 'all', 'label': 'All'},
                {'value': 'user', 'label': 'Gurubase UI'},
                {'value': 'widget', 'label': 'Widget'},
                {'value': 'api', 'label': 'API'},
                {'value': 'discord', 'label': 'Discord'},
                {'value': 'slack', 'label': 'Slack'},
            ]
        elif metric_type == 'referenced_sources':
            return [
                {'value': 'all', 'label': 'All'},
                {'value': 'github_repo', 'label': 'Codebase'},
                {'value': 'pdf', 'label': 'PDF'},
                {'value': 'website', 'label': 'Website'},
                {'value': 'youtube', 'label': 'YouTube'},
            ]
        return []

    @staticmethod
    def get_data_source_questions(guru_type, data_source_url, filter_type=None, interval='today', page=1):
        """Get questions that reference a specific data source."""
        start_date, end_date = get_date_range(interval)
        
        try:
            data_source = DataSource.objects.get(guru_type=guru_type, url=data_source_url)
            is_github = False
        except DataSource.DoesNotExist:
            try:
                data_source = GithubFile.objects.get(link=data_source_url)
                is_github = True
            except GithubFile.DoesNotExist:
                return None
        
        base_query = Q(
            guru_type=guru_type,
            date_created__gte=start_date,
            date_created__lte=end_date
        )
        
        if is_github:
            base_query &= Q(references__contains=[{'link': data_source.link}])
        else:
            base_query &= Q(references__contains=[{'link': data_source_url}])
            
        queryset = Question.objects.filter(base_query).order_by('-date_created')
        
        if filter_type and filter_type != 'all':
            queryset = queryset.filter(source__iexact=filter_type)
            
        paginated_data = AnalyticsService.get_paginated_data(queryset, page)
        
        results = [{
            'date': item.date_created.isoformat(),
            'title': item.question,
            'link': item.frontend_url,
            'source': format_filter_name(item.source)
        } for item in paginated_data['items']]
        
        return {
            'results': results,
            'total_pages': paginated_data['total_pages'],
            'current_page': paginated_data['current_page'],
            'total_items': paginated_data['total_items'],
            'available_filters': AnalyticsService.get_available_filters('questions')
        } 