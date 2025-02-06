from datetime import UTC, datetime, timedelta

def get_date_range(interval):
    """
    Helper function to get date range based on interval.
    
    Args:
        interval (str): One of 'today', 'yesterday', '7d', '30d', '3m', '6m', '12m'
        
    Returns:
        tuple: (start_date, end_date) both as timezone-aware datetimes
    """
    now = datetime.now(UTC)
    end_date = now
    
    if interval == 'today':
        start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
    elif interval == 'yesterday':
        end_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
        start_date = end_date - timedelta(days=1)
    elif interval == '7d':
        start_date = now - timedelta(days=7)
    elif interval == '30d':
        start_date = now - timedelta(days=30)
    elif interval == '3m':
        start_date = now - timedelta(days=90)  # Approximately 3 months
    elif interval == '6m':
        start_date = now - timedelta(days=180)  # Approximately 6 months
    elif interval == '12m':
        start_date = now - timedelta(days=365)  # Approximately 1 year
    else:  # Default to today
        start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
    
    return start_date, end_date

def calculate_percentage_change(current_value, previous_value):
    """Calculate percentage change between two values."""
    if previous_value == 0:
        return 0 if current_value == 0 else 100
    return round(((current_value - previous_value) / previous_value) * 100, 2)

def format_filter_name_for_display(name):
    """Format filter name to be Title Case."""
    name_mapping = {
        'user': 'Gurubase UI',
        'github_repo': 'Codebase',
        'pdf': 'PDF',
        'website': 'Website',
        'youtube': 'YouTube',
        'widget question': 'Widget'
    }
    
    return name_mapping.get(name.lower(), name.lower().replace('_', ' ').title())

def get_histogram_increment(start_date, end_date, interval):
    """Calculate appropriate time increment for histogram data."""
    total_duration = end_date - start_date
    
    if interval in ['today', 'yesterday']:
        return timedelta(hours=1), lambda current, next_slot: {'date_point': current.isoformat()}
    
    days_total = total_duration.days or 1
    if days_total <= 30:
        return timedelta(days=1), lambda current, next_slot: {'date_point': current.isoformat()}
    
    days_per_group = max(days_total // 30, 1)
    increment = timedelta(days=days_per_group)
    
    def format_range(current, next_slot):
        if next_slot.date() > current.date():
            range_end = next_slot - timedelta(days=1)
            range_end = range_end.replace(hour=23, minute=59, second=59)
            return {
                'date_start': current.isoformat(),
                'date_end': range_end.isoformat()
            }
        return {'date_point': current.isoformat()}
    
    return increment, format_range

def map_filter_to_source(filter_type):
    """
    Maps a filter type to its corresponding Question source value.
    
    Args:
        filter_type (str): The filter type from the request (e.g., 'widget', 'discord', 'api')
        
    Returns:
        str: The corresponding Question.Source value
    """
    if not filter_type or filter_type == 'all':
        return None
        
    source_map = {
        'widget': 'WIDGET QUESTION',
        'summary': 'SUMMARY QUESTION',
        'raw': 'RAW_QUESTION',
        'user': 'USER',
        'reddit': 'REDDIT',
        'api': 'API',
        'discord': 'DISCORD',
        'slack': 'SLACK'
    }
    
    return source_map.get(filter_type.lower(), filter_type.upper()) 