from django.urls import path
from .views import list_jira_issues

urlpatterns = [
    path('issues/<int:integration_id>/', list_jira_issues, name='list_jira_issues'),
]