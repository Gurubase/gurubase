from django.conf import settings
from django.urls import path
from integrations.bots.slack import views as slack_views

urlpatterns = []

urlpatterns += [
    path('slack/events/', slack_views.slack_events, name='slack_events'),
]
