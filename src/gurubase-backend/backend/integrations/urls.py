from django.conf import settings
from django.urls import path, include
from integrations import views as integration_views
from integrations.bots import views as bots_views

urlpatterns = []

urlpatterns += [

    # Bots
    path('test_message/', bots_views.send_test_message, name='send_test_message'),
    path('<str:guru_type>/<str:integration_type>/channels/', bots_views.manage_channels, name='manage_channels'),
    path('slack/', include('integrations.bots.slack.urls')),
    path('github/', include('integrations.bots.github.urls')),
    path('widget/', include('integrations.bots.widget.urls')),

    # Ingestion
    path('confluence/', include('integrations.ingestion.confluence.urls')),
    path('jira/', include('integrations.ingestion.jira.urls')),
    path('zendesk/', include('integrations.ingestion.zendesk.urls')),

    path('create/', integration_views.create_integration, name='create_integration'),
    path('<str:guru_type>/', integration_views.list_integrations, name='list_integrations'),
    path('<str:guru_type>/<str:integration_type>/', integration_views.manage_integration, name='manage_integration'),
]


