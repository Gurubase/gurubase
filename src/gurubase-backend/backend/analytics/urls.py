from django.urls import path
from analytics import views as analytics_views

urlpatterns = [
    path('<str:guru_type>/table', analytics_views.analytics_table, name='analytics_table'),
    path('<str:guru_type>/histogram', analytics_views.analytics_histogram, name='analytics_histogram'),
    path('<str:guru_type>/stats', analytics_views.analytics_stats, name='analytics_stats'),
    path('<str:guru_type>/data-source-questions', analytics_views.data_source_questions, name='data_source_questions'),
    path('<str:guru_type>/export', analytics_views.export_analytics, name='export_analytics'),
    path('<str:guru_type>/export/api', analytics_views.export_analytics_api, name='export_analytics_api'),
]
