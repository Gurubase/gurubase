from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from django.conf import settings
from rest_framework.response import Response
import logging
import redis

from core.github.models import GithubEvent
from core.github.app_handler import GithubAppHandler
from core.github.exceptions import (
    GithubEventError, GithubEventTypeError, GithubEventDataError,
    GithubEventHandlerError, GithubAPIError, GithubGraphQLError
)
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
        if not integration:
            raise GithubEventHandlerError("Integration is required")
        if not github_handler:
            raise GithubEventHandlerError("GitHub handler is required")
        self.integration = integration
        self.github_handler = github_handler

    @staticmethod
    def find_github_event_type(data: dict) -> Optional[GithubEvent]:
        """Find the GitHub event type from the webhook payload."""
        if not data:
            raise GithubEventDataError("Webhook payload data is required")

        try:
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
        except Exception as e:
            logger.error(f"Error determining GitHub event type: {e}")
            raise GithubEventTypeError(f"Failed to determine GitHub event type: {str(e)}")

    @staticmethod
    def is_supported_event(event_type: Optional[GithubEvent]) -> bool:
        """Check if the event type is supported."""
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
        try:
            if not data.get('issue'):
                raise GithubEventDataError("Issue data is missing from webhook payload")

            issue_data = data['issue']
            if not issue_data.get('url'):
                raise GithubEventDataError("Issue URL is missing")

            return {
                'discussion_id': None,
                'body': issue_data.get('body', ''),
                'user': issue_data.get('user', {}).get('login', ''),
                'api_url': issue_data.get('url'),
                'reply_to_id': None,
                'repository_name': data.get('repository', {}).get('name'),
            }
        except GithubEventDataError:
            raise
        except Exception as e:
            logger.error(f"Error extracting issue event data: {e}")
            raise GithubEventDataError(f"Failed to extract issue event data: {str(e)}")

    def handle_response(self, response: Response, event_data: Dict[str, Any], bot_name: str) -> None:
        try:
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
        except Exception as e:
            logger.error(f"Error handling issue response: {e}")
            raise GithubEventHandlerError(f"Failed to handle issue response: {str(e)}")

class IssueCommentEventHandler(GitHubEventHandler):
    def extract_event_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        try:
            if not data.get('comment') or not data.get('issue'):
                raise GithubEventDataError("Comment or issue data is missing from webhook payload")

            comment_data = data['comment']
            issue_data = data['issue']
            if not issue_data.get('url'):
                raise GithubEventDataError("Issue URL is missing")

            return {
                'discussion_id': None,
                'body': comment_data.get('body', ''),
                'user': comment_data.get('user', {}).get('login', ''),
                'api_url': issue_data.get('url'),
                'reply_to_id': None,
                'repository_name': data.get('repository', {}).get('name'),
            }
        except GithubEventDataError:
            raise
        except Exception as e:
            logger.error(f"Error extracting issue comment event data: {e}")
            raise GithubEventDataError(f"Failed to extract issue comment event data: {str(e)}")

    def handle_response(self, response: Response, event_data: Dict[str, Any], bot_name: str) -> None:
        try:
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
        except Exception as e:
            logger.error(f"Error handling issue comment response: {e}")
            raise GithubEventHandlerError(f"Failed to handle issue comment response: {str(e)}")

class DiscussionEventHandler(GitHubEventHandler):
    def extract_event_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        try:
            if not data.get('discussion'):
                raise GithubEventDataError("Discussion data is missing from webhook payload")

            discussion_data = data['discussion']
            if not discussion_data.get('node_id'):
                raise GithubEventDataError("Discussion node ID is missing")

            return {
                'discussion_id': discussion_data.get('node_id'),
                'body': discussion_data.get('body', ''),
                'user': discussion_data.get('user', {}).get('login', ''),
                'api_url': None,
                'reply_to_id': None,
                'repository_name': data.get('repository', {}).get('name'),
            }
        except GithubEventDataError:
            raise
        except Exception as e:
            logger.error(f"Error extracting discussion event data: {e}")
            raise GithubEventDataError(f"Failed to extract discussion event data: {str(e)}")

    def handle_response(self, response: Response, event_data: Dict[str, Any], bot_name: str) -> None:
        try:
            error_message = self.github_handler.format_github_answer(
                response.data,
                bot_name,
                event_data['body'],
                event_data['user'],
                success=response.status_code == 200
            )
            self._create_discussion_comment(event_data, error_message)
        except Exception as e:
            logger.error(f"Error handling discussion response: {e}")
            raise GithubEventHandlerError(f"Failed to handle discussion response: {str(e)}")

    def _create_discussion_comment(self, event_data: Dict[str, Any], response: str) -> None:
        try:
            if event_data['discussion_id']:
                self.github_handler.create_discussion_comment(
                    discussion_id=event_data['discussion_id'],
                    body=response,
                    installation_id=self.integration.external_id,
                    reply_to_id=event_data['reply_to_id']
                )
        except Exception as e:
            logger.error(f"Error creating discussion comment: {e}")
            raise GithubEventHandlerError(f"Failed to create discussion comment: {str(e)}")

class DiscussionCommentEventHandler(GitHubEventHandler):
    def extract_event_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        try:
            if not data.get('discussion') or not data.get('comment'):
                raise GithubEventDataError("Discussion or comment data is missing from webhook payload")

            discussion_data = data['discussion']
            comment_data = data['comment']
            if not discussion_data.get('node_id') or not comment_data.get('node_id'):
                raise GithubEventDataError("Discussion or comment node ID is missing")

            return {
                'discussion_id': discussion_data.get('node_id'),
                'body': comment_data.get('body', ''),
                'user': comment_data.get('user', {}).get('login', ''),
                'api_url': None,
                'reply_to_id': comment_data.get('node_id'),
                'repository_name': data.get('repository', {}).get('name'),
            }
        except GithubEventDataError:
            raise
        except Exception as e:
            logger.error(f"Error extracting discussion comment event data: {e}")
            raise GithubEventDataError(f"Failed to extract discussion comment event data: {str(e)}")

    def handle_response(self, response: Response, event_data: Dict[str, Any], bot_name: str) -> None:
        try:
            error_message = self.github_handler.format_github_answer(
                response.data,
                bot_name,
                event_data['body'],
                event_data['user'],
                success=response.status_code == 200
            )
            self._create_discussion_comment(event_data, error_message)
        except Exception as e:
            logger.error(f"Error handling discussion comment response: {e}")
            raise GithubEventHandlerError(f"Failed to handle discussion comment response: {str(e)}")

    def _create_discussion_comment(self, event_data: Dict[str, Any], response: str) -> None:
        try:
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
        except Exception as e:
            logger.error(f"Error creating discussion comment: {e}")
            raise GithubEventHandlerError(f"Failed to create discussion comment: {str(e)}")

class GitHubEventFactory:
    @staticmethod
    def get_handler(event_type: GithubEvent, integration: Integration, github_handler: GithubAppHandler) -> GitHubEventHandler:
        try:
            handlers = {
                GithubEvent.ISSUE_OPENED: IssueEventHandler,
                GithubEvent.ISSUE_COMMENT: IssueCommentEventHandler,
                GithubEvent.DISCUSSION_OPENED: DiscussionEventHandler,
                GithubEvent.DISCUSSION_COMMENT: DiscussionCommentEventHandler,
            }
            handler_class = handlers.get(event_type)
            if not handler_class:
                raise GithubEventTypeError(f"No handler found for event type: {event_type}")
            return handler_class(integration, github_handler)
        except GithubEventTypeError:
            raise
        except Exception as e:
            logger.error(f"Error creating event handler: {e}")
            raise GithubEventHandlerError(f"Failed to create event handler: {str(e)}") 