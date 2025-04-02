from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from django.conf import settings
from rest_framework.response import Response
import logging
import redis

from core.github.models import GithubEvent
from core.github.app_handler import GithubAppHandler
from ..models import Integration

logger = logging.getLogger(__name__)

redis_client = redis.Redis(
    host=settings.REDIS_HOST,
    port=settings.REDIS_PORT,
    db=0,
    charset="utf-8",
    decode_responses=True,
)


class GitHubEventHandler(ABC):
    def __init__(self, integration: Integration, github_handler: GithubAppHandler):
        self.integration = integration
        self.github_handler = github_handler

    @staticmethod
    def find_github_event_type(data: dict) -> Optional[GithubEvent]:
        """Find the GitHub event type from the webhook payload.
        
        Args:
            data (dict): The webhook payload data
            
        Returns:
            Optional[GithubEvent]: The event type if found, None otherwise
        """
        if 'issue' in data:
            if 'comment' in data and data.get('action') == 'created':
                # Can be pr and issue comment
                if data.get('issue', {}).get('html_url', '').split('/')[-2] == 'issues':
                    # Issue comment
                    return GithubEvent.ISSUE_COMMENT
                else:
                    # Pr comment
                    return None
            elif data.get('action') == 'opened':
                return GithubEvent.ISSUE_OPENED
        elif 'discussion' in data:
            if 'comment' in data and data.get('action') == 'created':
                return GithubEvent.DISCUSSION_COMMENT
            elif data.get('action') == 'opened':
                return GithubEvent.DISCUSSION_OPENED
        return None

    @staticmethod
    def is_supported_event(event_type: Optional[GithubEvent]) -> bool:
        """Check if the event type is supported.
        
        Args:
            event_type (Optional[GithubEvent]): The event type to check
            
        Returns:
            bool: True if the event type is supported, False otherwise
        """
        supported_events = [
            GithubEvent.ISSUE_OPENED,
            GithubEvent.ISSUE_COMMENT,
            GithubEvent.DISCUSSION_OPENED,
            GithubEvent.DISCUSSION_COMMENT
        ]
        return event_type is not None and event_type in supported_events

    @abstractmethod
    def extract_event_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract relevant data from the webhook payload"""
        pass

    @abstractmethod
    def handle_response(self, response: Response, event_data: Dict[str, Any]) -> None:
        """Handle the API response and post it back to GitHub"""
        pass

class IssueEventHandler(GitHubEventHandler):
    def extract_event_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        return {
            'discussion_id': None,
            'body': data.get('issue', {}).get('body', ''),
            'user': data.get('issue', {}).get('user', {}).get('login', ''),
            'api_url': data.get('issue', {}).get('url'),
            'reply_to_id': None,
            'repository_name': data.get('repository', {}).get('name'),
        }

    def handle_response(self, response: Response, event_data: Dict[str, Any], bot_name: str) -> None:
        error_message = self.github_handler.format_github_answer(
            response.data,
            bot_name,
            event_data['body'],
            event_data['user'],
            success=response.status_code == 200
        )
        self.github_handler.respond_to_github_issue_event(
            event_data['api_url'],
            self.integration.external_id,
            error_message
        )

class IssueCommentEventHandler(GitHubEventHandler):
    def extract_event_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        return {
            'discussion_id': None,
            'body': data.get('comment', {}).get('body', ''),
            'user': data.get('comment', {}).get('user', {}).get('login', ''),
            'api_url': data.get('issue', {}).get('url'),
            'reply_to_id': None,
            'repository_name': data.get('repository', {}).get('name'),
        }

    def handle_response(self, response: Response, event_data: Dict[str, Any], bot_name: str) -> None:
        error_message = self.github_handler.format_github_answer(
            response.data,
            bot_name,
            event_data['body'],
            event_data['user'],
            success=response.status_code == 200
        )
        self.github_handler.respond_to_github_issue_event(
            event_data['api_url'],
            self.integration.external_id,
            error_message
        )

class DiscussionEventHandler(GitHubEventHandler):
    def extract_event_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        return {
            'discussion_id': data.get('discussion', {}).get('node_id'),
            'body': data.get('discussion', {}).get('body', ''),
            'user': data.get('discussion', {}).get('user', {}).get('login', ''),
            'api_url': None,
            'reply_to_id': None,
            'repository_name': data.get('repository', {}).get('name'),
        }

    def handle_response(self, response: Response, event_data: Dict[str, Any], bot_name: str) -> None:
        error_message = self.github_handler.format_github_answer(
            response.data,
            bot_name,
            event_data['body'],
            event_data['user'],
            success=response.status_code == 200
        )
        self._create_discussion_comment(event_data, error_message)


    def _create_discussion_comment(self, event_data: Dict[str, Any], response: str) -> None:
        if event_data['discussion_id']:
            self.github_handler.create_discussion_comment(
                discussion_id=event_data['discussion_id'],
                body=response,
                installation_id=self.integration.external_id,
                reply_to_id=event_data['reply_to_id']
            )

class DiscussionCommentEventHandler(GitHubEventHandler):
    def extract_event_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        return {
            'discussion_id': data.get('discussion', {}).get('node_id'),
            'body': data.get('comment', {}).get('body', ''),
            'user': data.get('comment', {}).get('user', {}).get('login', ''),
            'api_url': None,
            'reply_to_id': data.get('comment', {}).get('node_id'),
            'repository_name': data.get('repository', {}).get('name'),
        }

    def handle_response(self, response: Response, event_data: Dict[str, Any], bot_name: str) -> None:
        error_message = self.github_handler.format_github_answer(
            response.data,
            bot_name,
            event_data['body'],
            event_data['user'],
            success=response.status_code == 200
        )
        self._create_discussion_comment(event_data, error_message)

    def _create_discussion_comment(self, event_data: Dict[str, Any], response: str) -> None:
        if event_data['discussion_id']:
            try:
                parent_comment_id = self.github_handler.get_discussion_comment(
                    event_data['reply_to_id'],
                    self.integration.external_id
                )
                if parent_comment_id:
                    event_data['reply_to_id'] = parent_comment_id
                else:
                    event_data['reply_to_id'] = None
            except Exception as e:
                logger.error(f"Error fetching parent comment: {e}", exc_info=True)
                event_data['reply_to_id'] = None

            self.github_handler.create_discussion_comment(
                discussion_id=event_data['discussion_id'],
                body=response,
                installation_id=self.integration.external_id,
                reply_to_id=event_data['reply_to_id']
            )

class GitHubEventFactory:
    @staticmethod
    def get_handler(event_type: GithubEvent, integration: Integration, github_handler: GithubAppHandler) -> GitHubEventHandler:
        handlers = {
            GithubEvent.ISSUE_OPENED: IssueEventHandler,
            GithubEvent.ISSUE_COMMENT: IssueCommentEventHandler,
            GithubEvent.DISCUSSION_OPENED: DiscussionEventHandler,
            GithubEvent.DISCUSSION_COMMENT: DiscussionCommentEventHandler,
        }
        handler_class = handlers.get(event_type)
        if not handler_class:
            raise ValueError(f"No handler found for event type: {event_type}")
        return handler_class(integration, github_handler) 