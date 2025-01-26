from django.conf import settings
from django.urls import path, re_path
from django.contrib import admin
from core import views as core_views
from django.contrib.sitemaps import views
from django.conf.urls import include

from django.conf.urls.static import static

urlpatterns = []
if settings.ENV == 'production':
    urlpatterns += [
        path('admin_vbaujyrk9p8ysb07/', admin.site.urls),
    ]
else:
    urlpatterns += [
        path('admin/', admin.site.urls),
    ]

urlpatterns += [
    path('accounts/', include('accounts.urls')),
    re_path(r'(?P<guru_type>[\w-]+)/question/(?P<slug>[\w-]+)/?$', core_views.question_detail, name="question_detail"),
    
    path('guru_types/', core_views.guru_types, name="guru_types"),
    path('guru_type/<str:slug>/', core_views.guru_type, name="guru_type"),
    path('<str:guru_type>/default_questions/', core_views.default_questions, name="default-questions"),
    path('<str:guru_type>/record_visit/', core_views.record_page_visit, name='record_visit'),
    path('<str:guru_type>/record_vote/', core_views.record_vote, name='record_vote'),
    path('processed_raw_questions/', core_views.get_processed_raw_questions, name='processed_raw_questions'),
    path('<str:guru_type>/resources/', core_views.get_guru_type_resources, name='get_guru_type_resources'),
    path('guru_types/create/', core_views.create_guru_type_internal, name='create_guru_type_internal'),
    path('<str:guru_type>/data_sources/', core_views.data_sources, name='data_sources'),
    path('<str:guru_type>/data_sources/update/', core_views.update_data_sources, name='update_data_sources'),
    path('<str:guru_type>/featured_datasources/', core_views.add_featured_ds_via_api, name='featured_datasources_via_api'), # Temporary endpoint to add featured datasourse via API
    path('guru_types/status/<str:guru_type>/', core_views.guru_type_status, name='guru_type_status'),
    path('export_datasources/', core_views.export_datasources, name='export_datasources'),
    path('export_questions/', core_views.export_questions, name='export_questions'),
    
    # JWT Auth Enabled Endpoints
    path('<str:guru_type>/data_sources_frontend/', core_views.data_sources_frontend, name='data_sources_frontend'),
    path('<str:guru_type>/data_sources_reindex/', core_views.data_sources_reindex, name='data_sources_reindex'),
    path('guru_types/update/<str:guru_type>/', core_views.update_guru_type, name='update_guru_type'),
    path('guru_types/delete/<str:guru_type>/', core_views.delete_guru_type, name='delete_guru_type'),
    path('<str:guru_type>/resources/detailed/', core_views.get_data_sources_detailed, name='get_data_sources_detailed'),
    path('my_gurus/', core_views.my_gurus, name='my_gurus'),
    path('<str:guru_type>/follow_up/examples/', core_views.follow_up_examples, name='follow_up_examples'),
    path('<str:guru_type>/follow_up/graph/', core_views.follow_up_graph, name='follow_up_graph'),
    path('<str:guru_type>/follow_up/binge/', core_views.create_binge, name='create_binge'),
    path('binge-history/', core_views.get_binges, name='get_binges'),
    path('api_keys/', core_views.api_keys, name='api_keys'),
    path('guru_types/create_frontend/', core_views.create_guru_type_frontend, name='create_guru_type_frontend'),
    path('health/', core_views.health_check, name='health_check'),
    path('widget/ask/', core_views.ask_widget, name='ask_widget'),
    path('widget/binge/', core_views.widget_create_binge, name='widget_create_binge'),
    path('<str:guru_type>/widget_ids/', core_views.manage_widget_ids, name='manage_widget_ids'),
    path('widget/guru/', core_views.get_guru_visuals, name='get_guru_visuals'),
    
    # API v1 Endpoints
    path('api/v1/<str:guru_type>/answer/', core_views.api_answer, name='api-answer'),
    path('api/v1/<str:guru_type>/data-sources/', core_views.api_data_sources, name='api-data-sources'),
    path('api/v1/<str:guru_type>/data-sources/reindex/', core_views.api_reindex_data_sources, name='api-reindex-data-sources'),
    # path('api/v1/<str:guru_type>/data-sources/privacy/', core_views.api_update_data_source_privacy, name='api-update-data-source-privacy'),

    path('slack/events/', core_views.slack_events, name='slack_events'),
    path('<str:guru_type>/integrations/', core_views.list_integrations, name='list_integrations'),
    path('<str:guru_type>/integrations/<str:integration_type>/', core_views.manage_integration, name='get_integration'),
    path('integrations/test_message/', core_views.send_test_message, name='send_test_message'),
    path('integrations/create/', core_views.create_integration, name='create_integration'),
    path('<str:guru_type>/integrations/<str:integration_type>/channels/', core_views.list_channels, name='list_channels'),
]

if settings.STREAM_ENABLED:
    urlpatterns += [
        path('<str:guru_type>/summary/', core_views.summary, name="summary"),
        path('<str:guru_type>/answer/', core_views.answer, name="answer"),
    ]
    if settings.ENV == 'selfhosted':
        urlpatterns += [
            path('api/<str:guru_type>/answer/', core_views.answer, name="answer-api"),
        ]

if settings.ENV != 'selfhosted':
    from core.sitemaps import get_sitemaps
    from django.views.decorators.cache import cache_page
    sitemaps = get_sitemaps()
    urlpatterns += [
        path(
            "sitemap.xml",
            cache_page(3600)(views.index),
            {"sitemaps": sitemaps},
            name="django.contrib.sitemaps.views.index",
        ),
        path(
            "sitemap/sitemap-<section>.xml",
            cache_page(3600)(views.sitemap),
            {"sitemaps": sitemaps},
            name="django.contrib.sitemaps.views.sitemap",
        ),
    ]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
