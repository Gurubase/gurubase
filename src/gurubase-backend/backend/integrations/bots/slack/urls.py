from django.conf import settings
from django.urls import path
from integrations.bots.slack import views as slack_views

urlpatterns = []

urlpatterns += [
    path('events/', slack_views.slack_events, name='slack_events'),
    path('add_channels/<str:guru_type>/', slack_views.add_channels, name='slack_add_channels'),
]
