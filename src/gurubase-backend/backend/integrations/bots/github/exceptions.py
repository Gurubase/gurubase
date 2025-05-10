class GithubBaseError(Exception):
    """Base exception for all GitHub-related errors."""
    pass

class GithubAppHandlerError(GithubBaseError):
    """Base exception for GitHub App Handler errors."""
    pass

class GithubAuthenticationError(GithubAppHandlerError):
    """Raised when there are issues with GitHub authentication."""
    pass

class GithubTokenError(GithubAuthenticationError):
    """Raised when there are issues with GitHub tokens (JWT, installation tokens)."""
    pass

class GithubAppTokenError(GithubTokenError):
    """Raised when there are issues with GitHub App tokens."""
    pass

class GithubPrivateKeyError(GithubTokenError):
    """Raised when there are issues with GitHub private keys."""
    pass

class GithubInstallationTokenError(GithubTokenError):
    """Raised when there are issues with GitHub installation tokens."""
    pass

class GithubWebhookError(GithubAppHandlerError):
    """Raised when there are issues with GitHub webhook verification."""
    pass

class GithubWebhookSecretError(GithubWebhookError):
    """Raised when there are issues with GitHub webhook secret."""
    pass

class GithubAPIError(GithubAppHandlerError):
    """Raised when there are issues with GitHub API calls."""
    def __init__(self, message: str, status_code: int = None, response_data: dict = None):
        super().__init__(message)
        self.status_code = status_code
        self.response_data = response_data

class GithubGraphQLError(GithubAPIError):
    """Raised when there are issues with GitHub GraphQL API calls."""
    pass

class GithubInstallationError(GithubAppHandlerError):
    """Raised when there are issues with GitHub App installations."""
    pass

class GithubInvalidInstallationError(GithubInstallationError):
    """Raised when there are issues with GitHub App installations."""
    pass

class GithubRepositoryError(GithubAppHandlerError):
    """Raised when there are issues with GitHub repositories."""
    pass

class GithubDiscussionError(GithubAppHandlerError):
    """Raised when there are issues with GitHub discussions."""
    pass

class GithubCommentError(GithubAppHandlerError):
    """Raised when there are issues with GitHub comments."""
    pass

class GithubEventError(GithubBaseError):
    """Base exception for GitHub event handling errors."""
    pass

class GithubEventTypeError(GithubEventError):
    """Raised when there are issues with GitHub event types."""
    pass

class GithubEventDataError(GithubEventError):
    """Raised when there are issues with GitHub event data."""
    pass

class GithubEventHandlerError(GithubEventError):
    """Raised when there are issues with GitHub event handlers."""
    pass
