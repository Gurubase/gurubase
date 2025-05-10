
from django.conf import settings
from django.urls import path
from integrations.bots.github.views import github_webhook
urlpatterns = []

urlpatterns += [
    path('github/', github_webhook, name='github_webhook'),
]

if settings.ENV == 'selfhosted':
    urlpatterns += [
        path('api/github/', github_webhook, name='github_webhook'),
    ]
