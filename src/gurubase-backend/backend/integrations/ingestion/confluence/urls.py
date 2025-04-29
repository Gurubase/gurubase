from django.urls import path
from .views import list_confluence_pages

urlpatterns = [
    path('pages/<int:integration_id>/', list_confluence_pages, name='list_confluence_pages'),
]
