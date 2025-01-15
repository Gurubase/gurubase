from rest_framework import status
from rest_framework.exceptions import APIException

class InvalidRequestError(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = {"msg": "invalid request"}
    default_code = 'invalidrequest'


class ContentExtractionError(Exception):
    """Base class for content extraction errors."""
    pass


class GitHubRepoContentExtractionError(ContentExtractionError):
    """Exception raised for errors in GitHub repository content extraction."""
    pass

class GithubInvalidRepoError(ContentExtractionError):
    """Exception raised for errors in GitHub repository content extraction."""
    pass

class GithubRepoSizeLimitError(ContentExtractionError):
    """Exception raised for errors in GitHub repository content extraction."""
    pass

class GithubRepoFileCountLimitError(ContentExtractionError):
    """Exception raised for errors in GitHub repository content extraction."""
    pass

class YouTubeContentExtractionError(ContentExtractionError):
    """Exception raised for errors in YouTube content extraction."""
    pass


class PDFContentExtractionError(ContentExtractionError):
    """Exception raised for errors in PDF content extraction."""
    pass


class WebsiteContentExtractionError(ContentExtractionError):
    """Exception raised for errors in Website content extraction."""
    pass 

class WebsiteContentExtractionThrottleError(WebsiteContentExtractionError):
    """Exception raised for errors in Website content extraction."""
    pass

class PermissionError(Exception):
    """Exception raised for permission errors."""
    pass

class NotFoundError(Exception):
    """Exception raised for not found errors."""
    pass
