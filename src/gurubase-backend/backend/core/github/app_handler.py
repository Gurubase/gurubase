import os
from django.conf import settings
import jwt
import logging
import time
import redis
import hmac
import hashlib
import requests

from core.github.models import GithubEvent
from core.integrations.helpers import cleanup_title, get_trust_score_emoji, strip_first_header
from core.github.exceptions import (
    GithubAppHandlerError, GithubAppTokenError, GithubInstallationTokenError, GithubInvalidInstallationError, GithubPrivateKeyError, GithubTokenError, GithubWebhookError,
    GithubAPIError, GithubGraphQLError, GithubInstallationError,
    GithubRepositoryError, GithubDiscussionError, GithubCommentError, GithubWebhookSecretError
)

logger = logging.getLogger(__name__)

redis_client = redis.Redis(
    host=settings.REDIS_HOST,
    port=settings.REDIS_PORT,
    db=0,
    charset="utf-8",
    decode_responses=True,
)

class GithubAppHandler:
    def __init__(self, integration = None):
        self.redis_client = redis_client
        self.jwt_key = "github_app_jwt"
        self.installation_jwt_key = "github_installation_jwt"
        self.base_path = os.path.dirname(os.path.abspath(__file__))
        self.pem_path = os.path.join(self.base_path, "github.pem")
        self.client_id = settings.GITHUB_APP_CLIENT_ID
        self.github_api_url = "https://api.github.com"
        self.github_graphql_url = "https://api.github.com/graphql"
        self.integration = integration

    def clear_redis_cache(self):
        """Clear the Redis cache."""
        self.redis_client.delete(self.jwt_key)
        # Clear all installation JWT keys using pattern matching
        for key in self.redis_client.keys(f"{self.installation_jwt_key}_*"):
            self.redis_client.delete(key)

    def _get_private_key(self):
        """Get the private key from the database."""
        if settings.ENV == 'selfhosted':
            if self.integration:
                return self.integration.github_private_key
            else:
                raise GithubAppHandlerError("No integration found")
        else:
            try:
                with open(self.pem_path, 'rb') as pem_file:
                    return pem_file.read()
            except Exception as e:
                raise GithubPrivateKeyError(f"Failed to read private key file: {str(e)}")

    def _get_client_id(self):
        """Get the client ID from the database."""
        if settings.ENV == 'selfhosted':
            if self.integration:
                return self.integration.github_client_id
            else:
                raise GithubAppHandlerError("No integration found")
        else:
            return self.client_id

    def _get_or_create_app_jwt(self, client_id: str = None, private_key: str = None):
        """Get existing JWT from Redis or create a new one if expired/missing."""
        try:
            # Try to get existing JWT from Redis
            existing_jwt = self.redis_client.get(self.jwt_key)
            if existing_jwt:
                return existing_jwt
                    
            # Generate new JWT
            if not private_key:
                signing_key = self._get_private_key()
            else:
                signing_key = private_key

            if not client_id:
                client_id = self._get_client_id()

            payload = {
                'iat': int(time.time()),
                'exp': int(time.time()) + 600,  # 10 minutes expiration
                'iss': client_id
            }

            # Create new JWT
            encoded_jwt = jwt.encode(payload, signing_key, algorithm='RS256')
            
            # Store in Redis with TTL of 9 minutes (slightly less than JWT expiration)
            self.redis_client.setex(
                self.jwt_key,
                540,  # 9 minutes in seconds
                encoded_jwt if isinstance(encoded_jwt, bytes) else encoded_jwt.encode('utf-8')
            )
            
            return encoded_jwt if isinstance(encoded_jwt, str) else encoded_jwt.decode('utf-8')

        except jwt.InvalidTokenError as e:
            logger.error(f"Invalid JWT token: {e}")
            self.clear_redis_cache()
            raise GithubAppTokenError(f"Failed to generate valid JWT token: {str(e)}") from e
        except jwt.InvalidKeyError as e:
            logger.error(f"Invalid key error: {e}")
            self.clear_redis_cache()
            raise GithubPrivateKeyError(f"Failed to generate valid JWT token: {str(e)}") from e
        except GithubPrivateKeyError as e:
            self.clear_redis_cache()
            raise e
        except Exception as e:
            logger.error(f"Error generating GitHub App JWT: {e}")
            self.clear_redis_cache()
            raise GithubAppTokenError(f"Failed to generate GitHub App JWT: {str(e)}") from e

    def _get_or_create_installation_jwt(self, installation_id, client_id: str = None, private_key: str = None):
        """Get existing installation access token from Redis or create a new one if expired/missing."""
        try:
            redis_key = f'{self.installation_jwt_key}_{installation_id}'
            # Try to get existing installation token from Redis
            existing_token = self.redis_client.get(redis_key)
            if existing_token:
                return existing_token

            # Get a new app JWT
            app_jwt = self._get_or_create_app_jwt(client_id, private_key)

            # Request new installation access token
            response = requests.post(
                f"https://api.github.com/app/installations/{installation_id}/access_tokens",
                headers={
                    "Accept": "application/vnd.github+json",
                    "Authorization": f"Bearer {app_jwt}",
                    "X-GitHub-Api-Version": "2022-11-28"
                }
            )
            
            if response.status_code != 201:
                raise GithubTokenError(f"Failed to get installation token. Status: {response.status_code}, Response: {response.text}")
                
            token_data = response.json()
            
            # Store in Redis with TTL of 55 minutes (slightly less than 1 hour expiration)
            self.redis_client.setex(
                redis_key,
                3300,  # 55 minutes in seconds
                token_data['token']
            )
            
            return token_data['token']

        except (GithubTokenError, GithubPrivateKeyError) as e:
            raise e
        except Exception as e:
            logger.error(f"Error getting GitHub installation access token: {e}")
            raise GithubInstallationTokenError(f"Failed to get GitHub installation access token: {str(e)}") from e

    def respond_to_github_issue_event(self, api_url, installation_id, formatted_response):
        installation_jwt = self._get_or_create_installation_jwt(installation_id)

        # Post the formatted response
        response = requests.post(
            f"{api_url}/comments",
            headers={
                "Authorization": f"Bearer {installation_jwt}",
                "X-GitHub-Api-Version": "2022-11-28"
            },
            json={
                "body": formatted_response
            }
        )

        response.raise_for_status()

    def create_discussion_comment(self, discussion_id: str, body: str, installation_id: str, reply_to_id: str = None):
        """Create a thread on a GitHub discussion using GraphQL API."""
        try:
            # Get installation access token
            installation_jwt = self._get_or_create_installation_jwt(installation_id)
            
            # Prepare the GraphQL mutation
            mutation = """
            mutation AddDiscussionComment($discussionId: ID!, $body: String!, $replyToId: ID) {
                addDiscussionComment(input: {
                    discussionId: $discussionId,
                    body: $body,
                    replyToId: $replyToId
                }) {
                    comment {
                        id
                        body
                        createdAt
                        author {
                            login
                        }
                        replyTo {
                            id
                        }
                    }
                }
            }
            """
            
            # Prepare variables
            variables = {
                "discussionId": discussion_id,
                "body": body,
                "replyToId": reply_to_id
            }
            
            # Make the GraphQL request
            response = requests.post(
                self.github_graphql_url,
                headers={
                    "Authorization": f"Bearer {installation_jwt}",
                    "Content-Type": "application/json",
                    "X-GitHub-Api-Version": "2022-11-28"
                },
                json={
                    "query": mutation,
                    "variables": variables
                }
            )
            
            if response.status_code != 200:
                raise GithubAPIError(
                    f"Failed to create discussion comment. Status: {response.status_code}",
                    status_code=response.status_code,
                    response_data=response.json()
                )
                
            result = response.json()
            
            # Check for GraphQL errors
            if "errors" in result:
                error_msg = result["errors"][0]["message"]
                logger.error(f"GraphQL error creating discussion comment: {error_msg}")
                raise GithubGraphQLError(f"Failed to create discussion comment: {error_msg}")
            
            return result["data"]["addDiscussionComment"]["comment"]
            
        except (GithubAPIError, GithubGraphQLError) as e:
            raise e
        except Exception as e:
            logger.error(f"Error creating discussion comment: {e}")
            raise GithubDiscussionError(f"Failed to create discussion comment: {str(e)}")

    def get_discussion_comment(self, comment_node_id: str, installation_id: str) -> str:
        """Gets the parent comment of a discussion thread."""
        try:
            # Get installation access token
            installation_jwt = self._get_or_create_installation_jwt(installation_id)
            
            # Prepare the GraphQL query
            query = """
            query GetDiscussionComment($commentId: ID!) {
                node(id: $commentId) {
                    ... on DiscussionComment {
                        id
                        body
                        replyTo {
                            id
                            body
                            replyTo {
                                id
                            }
                        }
                    }
                }
            }
            """
            
            # Prepare variables
            variables = {
                "commentId": comment_node_id
            }
            
            # Make the GraphQL request
            response = requests.post(
                self.github_graphql_url,
                headers={
                    "Authorization": f"Bearer {installation_jwt}",
                    "Content-Type": "application/json",
                    "X-GitHub-Api-Version": "2022-11-28"
                },
                json={
                    "query": query,
                    "variables": variables
                }
            )
            
            if response.status_code != 200:
                raise GithubAPIError(
                    f"Failed to fetch discussion comment. Status: {response.status_code}",
                    status_code=response.status_code,
                    response_data=response.json()
                )
                
            result = response.json()
            
            # Check for GraphQL errors
            if "errors" in result:
                error_msg = result["errors"][0]["message"]
                logger.error(f"GraphQL error fetching discussion comment: {error_msg}")
                raise GithubGraphQLError(f"Failed to fetch discussion comment: {error_msg}")

            if 'data' not in result or 'node' not in result['data'] or 'replyTo' not in result['data']['node'] or 'id' not in result['data']['node']['replyTo']:
                return None
            
            return result['data']["node"]["replyTo"]["id"]
            
        except (GithubAPIError, GithubGraphQLError) as e:
            raise e
        except Exception as e:
            logger.error(f"Error fetching discussion comment: {e}")
            raise GithubCommentError(f"Failed to fetch discussion comment: {str(e)}") from e

    def format_github_answer(self, answer: dict, bot_name: str, body: str = None, user: str = None, success: bool = True) -> str:
        """Format the response with trust score and references for GitHub.
        Using GitHub's markdown formatting:
        **bold**
        *italic*
        `code`
        ```preformatted```
        > blockquote
        [text](url) for links

        Args:
            answer (dict): The answer dictionary containing content, trust_score, references, etc.
            bot_name (str): The name of the bot
            body (str, optional): The message body to quote
            user (str, optional): The username who mentioned the bot
            success (bool, optional): Whether the API call was successful. Defaults to True.
            
        Returns:
            str: Formatted response string
        """
        # Build the final message
        formatted_msg = []
        
        # Add quoted body if provided
        if body:
            for line in body.split('\n'):
                formatted_msg.append(f"> {line}")
        if user:
            formatted_msg.append(f"\nHey @{user}\n")

        if success:
            formatted_msg.append("Here is my answer:\n")
        else:
            formatted_msg.append(f"Sorry, I don't have enough contexts to answer your question.\n\n_Tag **@{bot_name}** to ask me a question._")
            return "\n".join(formatted_msg)
        
        # Calculate the length of the fixed sections first
        trust_score = answer.get('trust_score', 0)
        trust_emoji = get_trust_score_emoji(trust_score)

        trust_score_section = f"\n---\n_**Trust Score**: {trust_emoji} {trust_score}%_"
        
        # Calculate references section length
        references = answer.get('references', [])
        references_section = ""
        if references:
            references_section = "\n_**Sources**:_ "
            for ref in references:
                # Clean up the title by removing emojis and extra spaces
                clean_title = cleanup_title(ref['title'])
                references_section += f"\n* _[{clean_title}]({ref['link']})_"
        
        # Calculate frontend link section length
        question_url = answer.get('question_url')
        frontend_link_section = ""
        if question_url:
            frontend_link_section = f"\n_👀 [View on Gurubase for a better UX]({question_url})_\n\n_Tag **@{bot_name}** to ask me a question._"
        
        # Calculate the length of the quoted body and user mention if provided
        quoted_body_length = 0
        user_mention_length = 0
        if body and user:
            # Calculate length of quoted body
            lines = body.split('\n')
            quoted_body_length = sum(len(f"> {line}\n") for line in lines)
            
            # Calculate length of user mention
            user_mention_length = len(f"\nHey @{user}\nHere is my answer:\n\n")
        
        # Calculate total length of fixed sections
        fixed_sections_length = (
            len(trust_score_section) + 
            len(references_section) + 
            len(frontend_link_section) + 
            quoted_body_length + 
            user_mention_length
        )
        
        # Calculate maximum allowed content length (65536 - fixed sections - some buffer)
        max_content_length = 65536 - fixed_sections_length - 100  # 100 chars buffer
        
        # Get and truncate content if needed
        content = answer.get('content', '')
        content = strip_first_header(content)
        if len(content) > max_content_length:
            content = content[:max_content_length] + "..."
        
        # Add content and other sections
        formatted_msg.append(content)
        formatted_msg.append(trust_score_section)
        if references:
            formatted_msg.append(references_section)
        if question_url:
            formatted_msg.append(frontend_link_section)
        
        return "\n".join(formatted_msg)

    def check_mentioned(self, body: str, user: str) -> bool:
        """Check if the user is mentioned in the body. However, it could be mentioning to itself like > @gurubase. Ignore these. Its line should not start with >.
        Also ignores email addresses like contact@gurubase.io and only considers exact @gurubase mentions with possible spaces."""
        lower_body = body.lower()
        lines = lower_body.split('\n')
        for line in lines:
            if line.startswith('> '):
                continue
            # Split the line into words to check for exact @gurubase mentions
            words = line.split()
            for word in words:
                # Check if the word is exactly @gurubase (case insensitive)
                if word.lower() == f"@{user.lower()}" and not line.startswith(f'_tag @{user.lower()} to ask me a question') and not line.startswith(f'hey @{user.lower()}'):
                    return True
        return False

    def cleanup_user_question(self, body:str, bot_name:str) -> str:
        """Remove the bot name from the question if it is mentioned."""
        if not body:
            return ''
        lines = body.split('\n')
        valid_lines = []
        for line in lines:
            if not line.startswith('> '):
                valid_lines.append(line)

        merged = '\n'.join(valid_lines)
        return merged.replace(f'@{bot_name}', '').strip()

    def limit_issue_comments_by_length(self, comments: list) -> list:
        """Prepare the comments for the issue.

        They are already formatted, we just need to limit the length and get them in reverse date order.

        Args:
            comments (list): The comments to prepare
            
        Returns:
            list: The prepared comments
        """

        limit = settings.GITHUB_CONTEXT_CHAR_LIMIT
        total_length = 0
        reversed_comments = list(reversed(comments))
        for i, comment in enumerate(reversed_comments):
            total_length += len(comment['body'])
            if total_length > limit:
                break

        if total_length < limit:
            i += 1
        return reversed_comments[:i]

    def strip_and_format_issue_comments(self, comments: list, bot_name: str) -> list:
        """Strip the comments and format them for the prompt."""
        processed_comments = []
        for c in comments:
            stripped_comment = {
                'body': c['body'] if c['body'] else '',
                'author_association': c['author_association'],
                'author': c['user']['login']
            }

            # Actually, the right place to do this is in `format_comments_for_prompt`, but otherwise we need to pass the bot id 3-4 layers below.
            if stripped_comment['author'] == f'{bot_name}[bot]':
                stripped_comment['author_association'] = 'YOU'

            if 'title' in c:
                stripped_comment['title'] = c['title']

            processed_comments.append(stripped_comment)
        return processed_comments

    def format_comments_for_prompt(self, comments: list) -> str:
        """Format the comments for the prompt."""
        processed_comments = []
        for c in comments:
            author_association = c['author_association']
            if author_association == 'NONE':
                author_association = 'USER'

            if 'title' in c:
                context = f'<Github issue>\nTitle: {c["title"]}\n\nAuthor: {c["author"]}\nAuthor association: {author_association}\nBody: {c["body"]}\n</Github issue>\n'
            else:
                context = f'<Github comment>\nAuthor: {c["author"]}\nAuthor association: {author_association}\nBody: {c["body"]}\n</Github comment>\n'

            processed_comments.append(context)
        return '\n'.join(processed_comments)

    def get_issue_comments(self, api_url: str, installation_id: str) -> list:
        """Get all comments for a specific issue."""
        try:
            # Get installation access token
            installation_jwt = self._get_or_create_installation_jwt(installation_id)
            
            # Prepare the API URL
            url = f"{api_url}/comments?sort=created&direction=desc&per_page=100"
            
            # Make the API request
            response = requests.get(
                url,
                headers={
                    "Authorization": f"Bearer {installation_jwt}",
                    "Accept": "application/vnd.github+json",
                    "X-GitHub-Api-Version": "2022-11-28"
                }
            )
            
            if response.status_code != 200:
                raise GithubAPIError(
                    f"Failed to fetch issue comments. Status: {response.status_code}",
                    status_code=response.status_code,
                    response_data=response.json()
                )
                
            comments = response.json()
            return comments
            
        except GithubAPIError as e:
            raise e
        except Exception as e:
            logger.error(f"Error fetching issue comments: {e}")
            raise GithubCommentError(f"Failed to fetch issue comments: {str(e)}") from e

    def get_issue(self, api_url: str, installation_id: str) -> list:
        """Get the initial issue post."""
        try:
            # Get installation access token
            installation_jwt = self._get_or_create_installation_jwt(installation_id)
            
            # Prepare the API URL
            url = f"{api_url}"
            
            # Make the API request
            response = requests.get(
                url,
                headers={
                    "Authorization": f"Bearer {installation_jwt}",
                    "Accept": "application/vnd.github+json",
                    "X-GitHub-Api-Version": "2022-11-28"
                }
            )
            
            if response.status_code != 200:
                raise GithubAPIError(
                    f"Failed to fetch issue. Status: {response.status_code}",
                    status_code=response.status_code,
                    response_data=response.json()
                )
                
            issue = response.json()
            return issue
            
        except GithubAPIError as e:
            raise e
        except Exception as e:
            logger.error(f"Error fetching issue: {e}")
            raise GithubCommentError(f"Failed to fetch issue: {str(e)}") from e

    def get_installation(self, installation_id: str, client_id: str = None, private_key: str = None) -> dict:
        """Get the installation details."""
        try:
            # Get installation access token
            installation_jwt = self._get_or_create_app_jwt(client_id, private_key)

            # Make the API request
            response = requests.get(
                f"{self.github_api_url}/app/installations/{installation_id}",
                headers={
                    "Accept": "application/vnd.github+json",
                    "Authorization": f"Bearer {installation_jwt}",
                    "X-GitHub-Api-Version": "2022-11-28"
                }
            )

            if response.status_code != 200:
                self.clear_redis_cache()
                if response.status_code == 404:
                    raise GithubInvalidInstallationError(f"Installation {installation_id} not found")

                raise GithubAPIError(
                    f"Failed to fetch installation. Status: {response.status_code}",
                    status_code=response.status_code,
                    response_data=response.json()
                )

            installation = response.json()
            return installation
        
        except GithubAPIError as e:
            raise e
        except Exception as e:
            raise e

    def fetch_repositories(self, installation_id: str, client_id: str = None, private_key: str = None) -> list:
        """Fetch repositories for a GitHub installation."""
        try:
            # Get installation access token
            access_token = self._get_or_create_installation_jwt(installation_id, client_id, private_key)
            
            # Fetch repositories
            response = requests.get(
                f"{self.github_api_url}/installation/repositories?per_page=100",
                headers={
                    "Accept": "application/vnd.github+json",
                    "Authorization": f"Bearer {access_token}",
                    "X-GitHub-Api-Version": "2022-11-28"
                }
            )
            
            if response.status_code != 200:
                raise GithubAPIError(
                    f"Failed to fetch repositories. Status: {response.status_code}",
                    status_code=response.status_code,
                    response_data=response.json()
                )
                
            data = response.json()
            
            # Extract repository names
            return [repo['name'] for repo in data.get('repositories', [])]
            
        except GithubAPIError as e:
            raise e
        except Exception as e:
            logger.error(f"Error fetching GitHub repositories: {e}", exc_info=True)
            raise GithubRepositoryError(f"Failed to fetch GitHub repositories: {str(e)}")

    def delete_installation(self, installation_id: str) -> None:
        """Delete a GitHub App installation."""
        try:
            # Get app JWT token
            app_jwt = self._get_or_create_app_jwt()
            
            # Make the DELETE request
            response = requests.delete(
                f"{self.github_api_url}/app/installations/{installation_id}",
                headers={
                    "Accept": "application/vnd.github+json",
                    "Authorization": f"Bearer {app_jwt}",
                    "X-GitHub-Api-Version": "2022-11-28"
                }
            )
            
            # Check if the installation was not found (404) - this is acceptable
            if response.status_code == 404:
                logger.info(f"Installation {installation_id} was already deleted or does not exist")
                return
                
            if response.status_code != 204:
                raise GithubAPIError(
                    f"Failed to delete installation. Status: {response.status_code}",
                    status_code=response.status_code,
                    response_data=response.json()
                )
                
            logger.info(f"Successfully deleted installation {installation_id}")
            
        except GithubAPIError as e:
            raise e
        except Exception as e:
            logger.error(f"Error deleting GitHub installation {installation_id}: {e}", exc_info=True)
            raise GithubInstallationError(f"Failed to delete GitHub installation: {str(e)}") from e

    def will_answer(self, body: str, bot_name: str, event_type: GithubEvent, mode: str) -> bool:
        """Check if the bot will answer based on the mode and event type."""

        # New issue and mode is auto
        if event_type == GithubEvent.ISSUE_OPENED and mode == 'auto':
            return True

        # Else, gurubase is mentioned
        if self.check_mentioned(body, bot_name):
            return True

        return False

    def _get_webhook_secret(self):
        """Get the webhook secret from the database or environment."""
        if settings.ENV == 'selfhosted':
            if self.integration:
                return self.integration.github_secret
            else:
                raise GithubWebhookSecretError("No integration found")
        else:
            return settings.GITHUB_SECRET_KEY

    def verify_signature(self, payload_body: bytes, signature_header: str) -> None:
        """Verify that the payload was sent from GitHub by validating SHA256."""
        try:
            secret_token = self._get_webhook_secret()
            if not secret_token:
                # If no secret token is set, we don't need to verify the signature
                return 

            if not signature_header:
                raise GithubWebhookSecretError("x-hub-signature-256 header is missing!")

            hash_object = hmac.new(
                secret_token.encode('utf-8'),
                msg=payload_body,
                digestmod=hashlib.sha256
            )
            expected_signature = "sha256=" + hash_object.hexdigest()
            
            if not hmac.compare_digest(expected_signature, signature_header):
                raise GithubWebhookSecretError("Request signatures didn't match!")

        except GithubWebhookSecretError as e:
            raise e
        except Exception as e:
            logger.error(f"Error verifying GitHub webhook signature: {e}")
            raise GithubWebhookError(f"Failed to verify webhook signature: {str(e)}") from e
