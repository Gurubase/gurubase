from rest_framework import status
from rest_framework.exceptions import APIException

class InvalidRequestError(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = {"msg": "invalid request"}
    default_code = 'invalidrequest'

class GuruNotFoundError(APIException):
    status_code = status.HTTP_404_NOT_FOUND
    default_detail = {"msg": "Guru type not found"}
    default_code = 'guru_not_found'


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


class JiraContentExtractionError(ContentExtractionError):
    """Exception raised for errors in Jira content extraction."""
    pass


class ZendeskContentExtractionError(ContentExtractionError):
    """Exception raised for errors in Zendesk content extraction."""
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

class ThrottlingException(Exception):
    """Exception raised for throttling errors."""
    pass

class ValidationError(Exception):
    """Exception raised for validation errors."""
    pass

class ZendeskError(Exception):
    """Exception raised for Zendesk errors."""
    pass

class ZendeskAuthenticationError(ZendeskError):
    """Exception raised for Zendesk authentication errors."""
    pass

class ZendeskInvalidDomainError(ZendeskError):
    """Exception raised for Zendesk invalid domain errors."""
    pass

class ZendeskInvalidSubdomainError(ZendeskError):
    """Exception raised for Zendesk invalid subdomain errors."""
    pass

class ConfluenceError(Exception):
    """Exception raised for Confluence errors."""
    pass

class ConfluenceInvalidDomainError(ConfluenceError):
    """Exception raised for Confluence invalid domain errors."""
    pass

class ConfluenceAuthenticationError(ConfluenceError):
    """Exception raised for Confluence authentication errors."""
    pass

class JiraError(Exception):
    """Exception raised for Jira errors."""
    pass

class JiraInvalidDomainError(JiraError):
    """Exception raised for Jira invalid domain errors."""
    pass

class JiraAuthenticationError(JiraError):
    """Exception raised for Jira authentication errors."""
    pass

class IntegrityError(Exception):
    """Exception raised for integrity errors."""
    pass

class ConfluenceContentExtractionError(Exception):
    pass


class ExcelContentExtractionError(Exception):
    """Exception raised for Excel content extraction errors."""
    pass

class ThrottleError(Exception):
    """Exception raised for throttling errors."""
    pass