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
from core.utils import get_default_settings
from core.exceptions import GitHubRepoContentExtractionError, GithubInvalidRepoError, GithubRepoSizeLimitError, GithubRepoFileCountLimitError
import requests

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
            import re
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

def find_github_event_type(data):
    if 'issue' in data:
        if 'comment' in data and data.get('action') == 'created':
            return GithubEvent.ISSUE_COMMENT
        elif data.get('action') == 'opened':
            return GithubEvent.ISSUE_OPENED
    elif 'discussion' in data:
        if 'comment' in data and data.get('action') == 'created':
            return GithubEvent.DISCUSSION_COMMENT
        elif data.get('action') == 'opened':
            return GithubEvent.DISCUSSION_OPENED
    elif 'pull_request' in data:
        if 'comment' in data and data.get('action') == 'created':
            return GithubEvent.PULL_REQUEST_COMMENT
        elif data.get('action') == 'opened':
            return GithubEvent.PULL_REQUEST_OPENED
    else:
        return None

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
            try:
                # Verify the token is still valid
                jwt.decode(
                    existing_jwt, 
                    options={"verify_signature": False}
                )
                return existing_jwt.decode('utf-8')
            except jwt.ExpiredSignatureError:
                # Token expired, will generate new one
                pass
            except Exception as e:
                logger.error(f"Error decoding JWT: {e}")
                
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
            raise GitHubRepoContentExtractionError(f"Failed to generate GitHub App JWT: {str(e)}")

    def _get_or_create_installation_jwt(self, installation_id):
        """Get existing installation access token from Redis or create a new one if expired/missing."""
        redis_key = f'{self.installation_jwt_key}_{installation_id}'
        # Try to get existing installation token from Redis
        existing_token = self.redis_client.get(redis_key)
        if existing_token:
            try:
                # Verify the token is still valid
                token_data = jwt.decode(
                    existing_token, 
                    options={"verify_signature": False}
                )
                # Check if token is expired or about to expire (within 5 minutes)
                if token_data.get('exp', 0) > int(time.time()) + 300:
                    return existing_token.decode('utf-8')
            except Exception as e:
                logger.error(f"Error decoding installation token: {e}")

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
            raise GitHubRepoContentExtractionError(f"Failed to get GitHub installation access token: {str(e)}")

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
            GitHubRepoContentExtractionError: If the API call fails
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
                raise GitHubRepoContentExtractionError(f"Failed to create discussion comment: {error_msg}")
            
            return result["data"]["addDiscussionComment"]["comment"]
            
        except Exception as e:
            logger.error(f"Error creating discussion comment: {e}")
            raise GitHubRepoContentExtractionError(f"Failed to create discussion comment: {str(e)}")

    def get_discussion_comment(self, comment_node_id: str, installation_id: str) -> str:
        """Gets the parent comment of a discussion thread.
        
        Args:
            discussion_id (str): The node ID of the discussion
            comment_node_id (str): The node ID of the comment to fetch
            installation_id (str): The GitHub App installation ID
            
        Returns:
            dict: The comment data from GitHub API
            
        Raises:
            GitHubRepoContentExtractionError: If the API call fails
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
                raise GitHubRepoContentExtractionError(f"Failed to fetch discussion comment: {error_msg}")

            if 'data' not in result or 'node' not in result['data'] or 'replyTo' not in result['data']['node'] or 'id' not in result['data']['node']['replyTo']:
                return None
            
            return result['data']["node"]["replyTo"]["id"]
            
        except Exception as e:
            logger.error(f"Error fetching discussion comment: {e}")
            raise GitHubRepoContentExtractionError(f"Failed to fetch discussion comment: {str(e)}")

    def format_github_response(self, body: str, user: str, formatted_answer: str) -> str:
        """Format a GitHub response in the specified format.
        
        Args:
            body (str): The message body to quote
            user (str): The username who mentioned the bot
            
        Returns:
            str: Formatted response string
        """

        lines = body.split('\n')
        formatted_lines = []
        for line in lines:
            formatted_lines.append(f"> {line}")

        formatted_body = '\n'.join(formatted_lines)

        return f"""
{formatted_body}

Hey @{user}
Here is my answer:

{formatted_answer}"""

    def check_mentioned(self, body: str, user: str) -> bool:
        """Check if the user is mentioned in the body. However, it could be mentioning to itself like > @gurubase. Ignore these. Its line should not start with >"""
        lower_body = body.lower()
        lines = body.split('\n')
        for line in lines:
            if line.startswith('> '):
                continue
            if f"@{user.lower()}" in line:
                return True
        return False
