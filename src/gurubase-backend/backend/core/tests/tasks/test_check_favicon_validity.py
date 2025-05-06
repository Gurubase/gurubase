from django.test import TestCase, override_settings
from django.utils import timezone
from unittest.mock import patch, MagicMock
import redis
from accounts.models import User
from core.models import Question, GuruType, DataSource, Integration, Settings, LLMEval, LLMEvalResult, SummaryQuestionGeneration, LinkReference, Favicon
from core.tasks import fill_empty_og_images, update_question_as_the_question_content_h1, find_duplicate_question_titles, process_titles, data_source_retrieval, llm_eval, llm_eval_result, check_favicon_validity
from core.utils import get_default_settings
from core.tasks import rewrite_content_for_wrong_markdown_content
from core.exceptions import WebsiteContentExtractionThrottleError, GithubInvalidRepoError, GithubRepoSizeLimitError, GithubRepoFileCountLimitError, YouTubeContentExtractionError
from core.requester import FirecrawlScraper # For type checking
import time
from datetime import datetime
class CheckFaviconValidityTaskTests(TestCase):
    def setUp(self):
        get_default_settings()
        self.guru_type = GuruType.objects.create(
            slug="test-guru", name="Test Guru", custom=True, active=True
        )
        self.favicon1 = Favicon.objects.create(
            domain="example.com",
            favicon_url="http://example.com/valid.ico",
            valid=False  # Initially not validated
        )
        self.favicon2 = Favicon.objects.create(
            domain="example2.com",
            favicon_url="http://example2.com/invalid.ico",
            valid=False  # Initially not validated
        )
        self.favicon3 = Favicon.objects.create(
            domain="example3.com",
            favicon_url="http://example3.com/error.ico",
            valid=False  # Initially not validated
        )
    
    @patch('requests.get')
    @patch('PIL.Image.open')
    def test_check_favicon_validity_success(self, mock_image_open, mock_requests_get):
        """Test processing a valid favicon."""
        # Mock successful response with valid image
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b'valid_image_content'
        mock_requests_get.return_value = mock_response

        # Mock successful image verification
        mock_image = MagicMock()
        mock_image_open.return_value = mock_image
        
        check_favicon_validity()
        
        self.favicon1.refresh_from_db()
        self.assertTrue(self.favicon1.valid)
        mock_requests_get.assert_any_call(self.favicon1.favicon_url, timeout=30)
        mock_image_open.assert_called()
        mock_image.verify.assert_called()
        mock_image.close.assert_called()
    
    @patch('requests.get')
    @patch('PIL.Image.open')
    def test_check_favicon_validity_invalid_image(self, mock_image_open, mock_requests_get):
        """Test processing an invalid image favicon."""
        # Mock successful response but with invalid image content
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b'invalid_image_content'
        mock_requests_get.return_value = mock_response
        
        # Mock image verification failure
        mock_image_open.side_effect = Exception("Invalid image format")
        
        check_favicon_validity()
        
        self.favicon2.refresh_from_db()
        self.assertFalse(self.favicon2.valid)
        mock_requests_get.assert_any_call(self.favicon2.favicon_url, timeout=30)
        mock_image_open.assert_called()
    
    @patch('requests.get')
    def test_check_favicon_validity_request_error(self, mock_requests_get):
        """Test handling request errors."""
        # Mock request throwing an exception
        mock_requests_get.side_effect = Exception("Connection error")
        
        check_favicon_validity()
        
        self.favicon3.refresh_from_db()
        self.assertFalse(self.favicon3.valid)
        mock_requests_get.assert_any_call(self.favicon3.favicon_url, timeout=30)
    
    @patch('requests.get')
    def test_check_favicon_validity_empty_response(self, mock_requests_get):
        """Test handling empty response content."""
        # Mock response with empty content
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b''  # Empty content
        mock_requests_get.return_value = mock_response
        
        check_favicon_validity()
        
        self.favicon1.refresh_from_db()
        self.assertFalse(self.favicon1.valid)
        mock_requests_get.assert_any_call(self.favicon1.favicon_url, timeout=30)
