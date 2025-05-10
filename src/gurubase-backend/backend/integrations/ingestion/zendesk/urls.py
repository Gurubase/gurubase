
from django.urls import path
from .views import list_zendesk_tickets, list_zendesk_articles

urlpatterns = [
    path('tickets/<int:integration_id>/', list_zendesk_tickets, name='list_zendesk_tickets'),
    path('articles/<int:integration_id>/', list_zendesk_articles, name='list_zendesk_articles'),
]
