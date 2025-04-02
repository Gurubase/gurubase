import enum
import os
import tempfile
import logging
import time
import redis
import jwt
from git import Repo
from pathlib import Path
from django.conf import settings
from core.integrations import cleanup_title, get_trust_score_emoji, strip_first_header
from core.utils import get_default_settings
from core.exceptions import GitHubRepoContentExtractionError, GithubInvalidRepoError, GithubRepoSizeLimitError, GithubRepoFileCountLimitError, GithubAppHandlerError
import requests
import re

redis_client = redis.Redis(
    host=settings.REDIS_HOST,
    port=settings.REDIS_PORT,
    db=0,
    charset="utf-8",
    decode_responses=True,
)

logger = logging.getLogger(__name__)

code_file_extensions = {
    # General purpose languages
    '.py', '.pyi', '.pyx',  # Python
    '.js', '.jsx', '.mjs',  # JavaScript
    '.ts', '.tsx',          # TypeScript
    '.rb', '.rake', '.erb', # Ruby
    '.php',                 # PHP
    '.java',                # Java
    '.scala',               # Scala
    '.kt', '.kts',          # Kotlin
    '.go', '.mod',          # Go
    '.rs',                  # Rust
    '.cpp', '.cc', '.cxx',  # C++
    '.hpp', '.hh', '.hxx',  
    '.c', '.h',            # C
    '.cs',                  # C#
    '.fs', '.fsx',         # F#
    '.swift',              # Swift
    '.m', '.mm',           # Objective-C
    
    # Web technologies
    '.html', '.htm',       # HTML
    '.css', '.scss', '.sass', '.less',  # Stylesheets
    '.vue', '.svelte',     # Web frameworks
    
    # Shell and scripting
    '.sh', '.bash', '.zsh',  # Shell scripts
    '.ps1', '.psm1', '.psd1',  # PowerShell
    '.pl', '.pm',          # Perl
    '.lua',                # Lua
    
    # Functional languages
    '.hs', '.lhs',         # Haskell
    '.ex', '.exs',         # Elixir
    '.erl', '.hrl',        # Erlang
    '.clj', '.cljs',       # Clojure
    
    # Other languages
    '.r', '.R',            # R
    '.dart',               # Dart
    '.groovy',             # Groovy
    '.ml', '.mli',         # OCaml
    '.sol',                # Solidity
    '.cob', '.cbl',        # COBOL
    '.proto',              # Protocol Buffers
}

package_manifest_files = {
    # Python
    'requirements.txt',
    'setup.py',
    'pyproject.toml',
    'Pipfile',
    'poetry.toml',
    
    # JavaScript/TypeScript
    'package.json',
    'bower.json',
    
    # Ruby
    'Gemfile',
    
    # Java/Kotlin
    'pom.xml',
    'build.gradle',
    'build.gradle.kts',
    
    # Go
    'go.mod',
    
    # Rust
    'Cargo.toml',
    
    # PHP
    'composer.json',
    
    # .NET/C#
    '*.csproj',
    '*.fsproj',
    'packages.config',
    
    # Swift
    'Package.swift',
    
    # Scala
    'build.sbt',
    
    # Haskell
    'package.yaml',
    'cabal.project',
    
    # Elixir
    'mix.exs',
    
    # R
    'DESCRIPTION',
    
    # Perl
    'cpanfile',
    'Makefile.PL',
}

def extract_repo_name(repo_url):
    """Extract repository name from GitHub URL."""
    try:
        # Handle both HTTPS and SSH URLs
        if repo_url.endswith('.git'):
            repo_url = repo_url[:-4]
        return repo_url.split('/')[-2:]
    except Exception as e:
        raise GitHubRepoContentExtractionError(f"Invalid GitHub repository URL: {repo_url}")

def clone_repository(repo_url):
    """Clone a GitHub repository to a temporary directory."""
    try:
        logger.info(f"Cloning repository {repo_url}")
        # Create a temporary directory
        temp_dir = tempfile.mkdtemp()
        
        # Clone the repository
        repo = Repo.clone_from(repo_url, temp_dir)
        
        logger.info(f"Cloned repository {repo_url}")
        return temp_dir, repo
    except Exception as e:
        # Check if the error message indicates repository not found
        if "repository" in str(e).lower() and "not found" in str(e).lower():
            # Extract repo URL from error message using regex
            match = re.search(r"repository '([^']+)' not found", str(e))
            if match:
                repo_url = match.group(1)
                logger.error(f"Repository not found: {repo_url}")
                raise GithubInvalidRepoError(f"No repository exists at this URL.")
        elif 'No such device or address' in str(e):
            raise GithubInvalidRepoError(f"No repository exists at this URL.")
        logger.error(f"Error cloning repository {repo_url}: {str(e)}", exc_info=True)
        raise GitHubRepoContentExtractionError(f"Failed to clone repository: {str(e)}")

def get_file_content(file_path):
    """Read and return the content of a file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except UnicodeDecodeError:
        # Skip binary files
        return None
    except Exception as e:
        logger.warning(f"Error reading file {file_path}: {str(e)}")
        return None
    
def read_repository(repo_path):
    """Get the directory structure and file contents of the repository."""
    structure = []
    logger.info(f"Reading repository {repo_path}")

    default_settings = get_default_settings()

    package_manifest_files = set(default_settings.package_manifest_files) # Turn into set to optimize existence check
    code_file_extensions = set(default_settings.code_file_extensions) # Turn into set to optimize existence check

    for root, dirs, files in os.walk(repo_path):
        # Skip .git directory
        if '.git' in dirs:
            dirs.remove('.git')
        
        # Skip common build directories and cache
        dirs[:] = [d for d in dirs if d not in [
            '.git', 'node_modules', '__pycache__', 'build', 'dist',
            'venv', 'env', '.venv', '.env',  # Python virtual environments
            'target', 'out',  # Java/Maven/Gradle build directories
            'bin', 'obj',  # .NET build directories
            'vendor',  # PHP/Go dependencies
            'coverage', '.coverage',  # Test coverage reports
            '.idea', '.vscode',  # IDE directories
            'tmp', 'temp',  # Temporary directories
            '.next', '.nuxt',  # Next.js/Nuxt.js build directories
            'logs', 'log'  # Log directories
        ]]
        
        # Add files at current level
        for file in sorted(files):
            file_path = os.path.join(root, file)
            relative_path = os.path.relpath(file_path, repo_path)
            
            # Process only if it's a code file or package manifest
            _, ext = os.path.splitext(file.lower())
            if ext in code_file_extensions or file in package_manifest_files:
                # Skip files larger than 10MB
                if os.path.getsize(file_path) > 1024 * 1024 * 10:
                    continue
                
                content = get_file_content(file_path)
                structure.append({
                    'path': relative_path,
                    'content': content,
                    'size': os.path.getsize(file_path)
                })

    logger.info(f"Repository structure and contents read")
    return structure

def save_repository(data_source, structure, default_branch):
    """Save the read repository structure and contents to the database."""
    from core.models import GithubFile
    bulk_save = []

    if settings.ENV != 'selfhosted':
        if len(structure) > data_source.guru_type.github_file_count_limit_per_repo_soft:
            raise GithubRepoFileCountLimitError(f"The codebase ({len(structure)}) exceeds the maximum file limit of {data_source.guru_type.github_file_count_limit_per_repo_soft} files supported")

        # Calculate total size of all files
        total_size = sum(file['size'] for file in structure)
        
        # Check if total size exceeds limit
        if total_size > data_source.guru_type.github_repo_size_limit_mb * 1024 * 1024:
            raise GithubRepoSizeLimitError(f"The codebase exceeds the maximum size limit of {data_source.guru_type.github_repo_size_limit_mb} MB supported")

    for file in structure:
        bulk_save.append(GithubFile(
            data_source=data_source,
            path=file['path'],
            content=file['content'],
            size=file['size'],
            link=f'{data_source.url}/tree/{default_branch}/{file["path"]}'
        ))

        if len(bulk_save) >= 100:
            try:
                GithubFile.objects.bulk_create(bulk_save)
            except Exception as e:
                for file in bulk_save:
                    try:
                        file.save()
                    except Exception as e:
                        logger.error(f"Error saving GitHub file {file.path}: {e}")
            bulk_save = []

    if bulk_save:
        try:
            GithubFile.objects.bulk_create(bulk_save)
        except Exception as e:
            for file in bulk_save:
                try:
                    file.save()
                except Exception as e:
                    logger.error(f"Error saving GitHub file {file.path}: {e}")


def process_github_repository(data_source):
    """Main function to process a GitHub repository."""
    try:
        repo_url = data_source.url
        # Clone the repository
        temp_dir, repo = clone_repository(repo_url)
        
        # Check default branch name
        default_branch = repo.active_branch.name
        logger.info(f"Default branch name: {default_branch}")
        
        # Get repository structure and contents
        structure = read_repository(temp_dir)

        save_repository(data_source, structure, default_branch)
        
        # Clean up temporary directory
        repo.close()
        os.system(f"rm -rf {temp_dir}")
        
        return default_branch 
    except GithubInvalidRepoError as e:
        raise e
    except GithubRepoSizeLimitError as e:
        raise e
    except GithubRepoFileCountLimitError as e:
        raise e
    except Exception as e:
        raise GitHubRepoContentExtractionError(f"Error processing GitHub repository: {str(e)}")

class GithubEvent(enum.Enum):
    # Reopens are not caught as comments are caught separately
    ISSUE_OPENED = "issue_opened"
    ISSUE_COMMENT = "issue_comment"

    DISCUSSION_OPENED = "discussion_opened"
    DISCUSSION_COMMENT = "discussion_comment"

    PULL_REQUEST_OPENED = "pull_request_opened"
    PULL_REQUEST_COMMENT = "pull_request_comment"

    PULL_REQUEST_REVIEW_COMMENT = "pull_request_review_comment"
    # PULL_REQUEST_REVIEW_REOPENED = "pull_request_review_reopened"

    PULL_REQUEST_REVIEW_REQUESTED = "pull_request_review_requested"
    # PULL_REQUEST_REVIEW_REQUESTED_REOPENED = "pull_request_review_requested_reopened"


class GithubAppHandler:
    def __init__(self):
        self.redis_client = redis_client
        self.jwt_key = "github_app_jwt"
        self.installation_jwt_key = "github_installation_jwt"
        self.base_path = os.path.dirname(os.path.abspath(__file__))
        self.pem_path = os.path.join(self.base_path, "..", "github", "github.pem")
        self.client_id = settings.GITHUB_APP_CLIENT_ID
        self.github_api_url = "https://api.github.com"
        self.github_graphql_url = "https://api.github.com/graphql"

    def _get_or_create_app_jwt(self):
        """Get existing JWT from Redis or create a new one if expired/missing."""
        # Try to get existing JWT from Redis
        existing_jwt = self.redis_client.get(self.jwt_key)
        if existing_jwt:
            return existing_jwt
                
        # Generate new JWT
        try:
            with open(self.pem_path, 'rb') as pem_file:
                signing_key = pem_file.read()

            payload = {
                'iat': int(time.time()),
                'exp': int(time.time()) + 600,  # 10 minutes expiration
                'iss': self.client_id
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

        except Exception as e:
            logger.error(f"Error generating GitHub App JWT: {e}")
            raise GithubAppHandlerError(f"Failed to generate GitHub App JWT: {str(e)}")

    def _get_or_create_installation_jwt(self, installation_id):
        """Get existing installation access token from Redis or create a new one if expired/missing."""
        redis_key = f'{self.installation_jwt_key}_{installation_id}'
        # Try to get existing installation token from Redis
        existing_token = self.redis_client.get(redis_key)
        if existing_token:
            return existing_token

        # Get a new app JWT
        app_jwt = self._get_or_create_app_jwt()

        try:
            # Request new installation access token
            response = requests.post(
                f"https://api.github.com/app/installations/{installation_id}/access_tokens",
                headers={
                    "Accept": "application/vnd.github+json",
                    "Authorization": f"Bearer {app_jwt}",
                    "X-GitHub-Api-Version": "2022-11-28"
                }
            )
            response.raise_for_status()
            token_data = response.json()
            
            # Store in Redis with TTL of 55 minutes (slightly less than 1 hour expiration)
            self.redis_client.setex(
                redis_key,
                3300,  # 55 minutes in seconds
                token_data['token']
            )
            
            return token_data['token']

        except Exception as e:
            logger.error(f"Error getting GitHub installation access token: {e}")
            raise GithubAppHandlerError(f"Failed to get GitHub installation access token: {str(e)}")

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
        """Create a thread on a GitHub discussion using GraphQL API.
        
        Args:
            discussion_id (str): The node ID of the discussion to comment on
            body (str): The content of the comment
            installation_id (str): The GitHub App installation ID
            reply_to_id (str, optional): The node ID of the discussion comment to reply to
            
        Returns:
            dict: The created comment data from GitHub API
            
        Raises:
            GithubAppHandlerError: If the API call fails
        """
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
            
            response.raise_for_status()
            result = response.json()
            
            # Check for GraphQL errors
            if "errors" in result:
                error_msg = result["errors"][0]["message"]
                logger.error(f"GraphQL error creating discussion comment: {error_msg}")
                raise GithubAppHandlerError(f"Failed to create discussion comment: {error_msg}")
            
            return result["data"]["addDiscussionComment"]["comment"]
            
        except Exception as e:
            logger.error(f"Error creating discussion comment: {e}")
            raise GithubAppHandlerError(f"Failed to create discussion comment: {str(e)}")

    def get_discussion_comment(self, comment_node_id: str, installation_id: str) -> str:
        """Gets the parent comment of a discussion thread.
        
        Args:
            discussion_id (str): The node ID of the discussion
            comment_node_id (str): The node ID of the comment to fetch
            installation_id (str): The GitHub App installation ID
            
        Returns:
            dict: The comment data from GitHub API
            
        Raises:
            GithubAppHandlerError: If the API call fails
        """
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
            
            # Convert the numeric ID to a node ID format
            
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
            
            response.raise_for_status()
            result = response.json()
            
            # Check for GraphQL errors
            if "errors" in result:
                error_msg = result["errors"][0]["message"]
                logger.error(f"GraphQL error fetching discussion comment: {error_msg}")
                raise GithubAppHandlerError(f"Failed to fetch discussion comment: {error_msg}")

            if 'data' not in result or 'node' not in result['data'] or 'replyTo' not in result['data']['node'] or 'id' not in result['data']['node']['replyTo']:
                return None
            
            return result['data']["node"]["replyTo"]["id"]
            
        except Exception as e:
            logger.error(f"Error fetching discussion comment: {e}")
            raise GithubAppHandlerError(f"Failed to fetch discussion comment: {str(e)}")

    def format_github_answer(self, answer: dict, body: str = None, user: str = None, success: bool = True) -> str:
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
            body (str, optional): The message body to quote
            user (str, optional): The username who mentioned the bot
            success (bool, optional): Whether the API call was successful. Defaults to True.
            
        Returns:
            str: Formatted response string
        """
        # Build the final message
        formatted_msg = []
        
        # Add quoted body if provided
        if body and user:
            for line in body.split('\n'):
                formatted_msg.append(f"> {line}")
            formatted_msg.append(f"\nHey @{user}\n")
            if success:
                formatted_msg.append("Here is my answer:\n")
            else:
                formatted_msg.append("Sorry, I don't have enough contexts to answer your question.")
                return "\n".join(formatted_msg)
        
        if not success:
            return "Sorry, I don't have enough contexts to answer your question."
            
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
            frontend_link_section = f"\n_👀 [View on Gurubase for a better UX]({question_url})_\n\n_Tag @gurubase to ask me a question._"
        
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
        """Check if the user is mentioned in the body. However, it could be mentioning to itself like > @gurubase. Ignore these. Its line should not start with >"""
        lower_body = body.lower()
        lines = body.split('\n')
        for line in lines:
            if line.startswith('> '):
                continue
            if f"@{user.lower()}" in line and not line.startswith(f'_Tag @{user.lower()} to ask me a question'):
                return True
        return False

    def cleanup_user_question(self, body:str, bot_name:str) -> str:
        """Remove the bot name from the question if it is mentioned."""
        lines = body.split('\n')
        valid_lines = []
        for line in lines:
            if not line.startswith('> '):
                valid_lines.append(line)

        merged = '\n'.join(valid_lines)
        return merged.replace(f'@{bot_name}', '').strip()

    def find_github_event_type(self, data:dict) -> GithubEvent:
        if 'issue' in data:
            if 'comment' in data and data.get('action') == 'created':
                # Can be pr and issue comment
                if data.get('issue').get('html_url').split('/')[-2] == 'issues':
                    # Issue comment
                    return GithubEvent.ISSUE_COMMENT
                else:
                    # Pr comment
                    return None
            elif data.get('action') == 'opened':
                return GithubEvent.ISSUE_OPENED
        # elif 'discussion' in data:
        #     if 'comment' in data and data.get('action') == 'created':
        #         return GithubEvent.DISCUSSION_COMMENT
        #     elif data.get('action') == 'opened':
        #         return GithubEvent.DISCUSSION_OPENED
        # elif 'pull_request' in data:
        #     if 'comment' in data and data.get('action') == 'created':
        #         return GithubEvent.PULL_REQUEST_COMMENT
        #     elif data.get('action') == 'opened':
        #         return GithubEvent.PULL_REQUEST_OPENED
        else:
            return None
        
    def prepare_issue_comments(self, comments: list) -> list:
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

    def format_comments_for_prompt(self, comments: list) -> str:
        """Format the comments for the prompt."""
        processed_comments = []
        for c in comments:
            processed_comments.append(f"<Github comment>\nAuthor association: {c['author_association']}\nBody: {c['body']}\n</Github comment>\n")
        return '\n'.join(processed_comments)

    def get_issue_comments(self, api_url: str, installation_id: str) -> list:
        """Get all comments for a specific issue.
        
        Args:
            api_url (str): The API URL of the issue
            installation_id (str): The GitHub App installation ID
            
        Returns:
            list: List of comments with their details
            
        Raises:
            GithubAppHandlerError: If the API call fails
        """
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
            
            response.raise_for_status()
            comments = response.json()
            return [{'body': comment['body'], 'author_association': comment['author_association']} for comment in comments]
            
        except Exception as e:
            logger.error(f"Error fetching issue comments: {e}")
            raise GithubAppHandlerError(f"Failed to fetch issue comments: {str(e)}")

    def get_issue(self, api_url: str, installation_id: str) -> list:
        """Get the initial issue post.
        
        Args:
            api_url (str): The API URL of the issue
            installation_id (str): The GitHub App installation ID
            
        Returns:
            dict: The issue data
            
        Raises:
            GithubAppHandlerError: If the API call fails
        """
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
            
            response.raise_for_status()
            issue = response.json()
            return {'body': issue['body'], 'author_association': issue['author_association']}
            
        except Exception as e:
            logger.error(f"Error fetching issue comments: {e}")
            raise GithubAppHandlerError(f"Failed to fetch issue comments: {str(e)}")

    def get_installation(self, installation_id: str) -> dict:
        """Get the installation details.
        
        Args:
            installation_id (str): The GitHub App installation ID

        Returns:
            dict: The installation details
            
        Raises:
            GithubAppHandlerError: If the API call fails
        """
        try:
            # Get installation access token
            installation_jwt = self._get_or_create_app_jwt()

            # Make the API request
            response = requests.get(
                f"{self.github_api_url}/app/installations/{installation_id}",
                headers={
                    "Accept": "application/vnd.github+json",
                    "Authorization": f"Bearer {installation_jwt}",
                    "X-GitHub-Api-Version": "2022-11-28"
                }
            )

            response.raise_for_status()
            installation = response.json()
            return installation
        
        except Exception as e:
            logger.error(f"Error fetching GitHub installation: {e}", exc_info=True)
            raise GithubAppHandlerError(f"Failed to fetch GitHub installation: {str(e)}")

    def fetch_repositories(self, installation_id: str) -> list:
        """Fetch repositories for a GitHub installation.
        
        Args:
            installation_id (str): The GitHub App installation ID
            
        Returns:
            list: List of repository names
            
        Raises:
            GithubAppHandlerError: If the API call fails
        """
        try:
            # Get installation access token
            access_token = self._get_or_create_installation_jwt(installation_id)
            
            # Fetch repositories
            response = requests.get(
                f"{self.github_api_url}/installation/repositories?per_page=100",
                headers={
                    "Accept": "application/vnd.github+json",
                    "Authorization": f"Bearer {access_token}",
                    "X-GitHub-Api-Version": "2022-11-28"
                }
            )
            response.raise_for_status()
            data = response.json()
            
            # Extract repository names
            return [repo['name'] for repo in data.get('repositories', [])]
        except Exception as e:
            logger.error(f"Error fetching GitHub repositories: {e}", exc_info=True)
            raise GithubAppHandlerError(f"Failed to fetch GitHub repositories: {str(e)}")


    def delete_installation(self, installation_id: str) -> None:
        """Delete a GitHub App installation.
        
        Args:
            installation_id (str): The GitHub App installation ID to delete
            
        Raises:
            GithubAppHandlerError: If the API call fails
        """
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
                
            response.raise_for_status()
            logger.info(f"Successfully deleted installation {installation_id}")
            
        except Exception as e:
            logger.error(f"Error deleting GitHub installation {installation_id}: {e}", exc_info=True)
            raise GithubAppHandlerError(f"Failed to delete GitHub installation: {str(e)}")

    def will_answer(self, body: str, bot_name: str, event_type: GithubEvent, mode: str) -> bool:
        """Check if the bot will answer based on the mode and event type."""

        # New issue and mode is auto
        if event_type == GithubEvent.ISSUE_OPENED and mode == 'auto':
            return True

        # Else, gurubase is mentioned
        if self.check_mentioned(body, bot_name):
            return True

        return False
