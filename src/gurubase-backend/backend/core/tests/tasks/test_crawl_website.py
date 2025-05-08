from django.test import TestCase
from django.utils import timezone
from unittest.mock import patch
from core.models import CrawlState, GuruType
from core.tasks import crawl_website
from core.utils import get_default_settings


class TestCrawlWebsite(TestCase):
    def setUp(self):
        """
        Set up test environment with necessary objects:
        1. Default settings
        2. GuruType for testing
        3. CrawlState objects for different test scenarios
        """
        # Initialize default settings
        get_default_settings()
        
        # Create test GuruType
        self.guru_type = GuruType.objects.create(
            slug="test-guru",
            name="Test Guru",
            custom=True,
            active=True
        )
        
        # Create CrawlState objects for different test scenarios
        self.crawl_state = CrawlState.objects.create(
            url="https://example.com",
            guru_type=self.guru_type,
            status=CrawlState.Status.RUNNING,
            start_time=timezone.now(),
            source=CrawlState.Source.API
        )
        
        # Test data
        self.test_url = "https://example.com"
        self.test_link_limit = 100
        self.test_language_code = "en"

    @patch('core.tasks.get_internal_links')
    def test_crawl_website_success(self, mock_get_internal_links):
        """
        Test successful website crawling scenario.
        
        This test verifies that:
        1. The get_internal_links function is called with correct parameters
        2. No exceptions are raised
        """
        # Call the task
        crawl_website(
            url=self.test_url,
            crawl_state_id=self.crawl_state.id,
            link_limit=self.test_link_limit,
            language_code=self.test_language_code
        )
        
        # Assert get_internal_links was called with correct parameters
        mock_get_internal_links.assert_called_once_with(
            self.test_url, 
            crawl_state_id=self.crawl_state.id, 
            link_limit=self.test_link_limit,
            language_code=self.test_language_code
        )

    @patch('core.tasks.get_internal_links')
    def test_crawl_website_exception(self, mock_get_internal_links):
        """
        Test website crawling failure scenario.
        
        This test verifies that:
        1. When get_internal_links raises an exception, the task handles it gracefully
        2. The CrawlState is updated with correct failure status and error message
        """
        # Configure mock to raise an exception
        mock_exception_message = "Connection error"
        mock_get_internal_links.side_effect = Exception(mock_exception_message)
        
        # Call the task
        crawl_website(
            url=self.test_url,
            crawl_state_id=self.crawl_state.id,
            link_limit=self.test_link_limit,
            language_code=self.test_language_code
        )
        
        # Reload the crawl state from the database
        self.crawl_state.refresh_from_db()
        
        # Assert CrawlState was updated with failure information
        self.assertEqual(self.crawl_state.status, CrawlState.Status.FAILED)
        self.assertEqual(self.crawl_state.error_message, mock_exception_message)
        self.assertIsNotNone(self.crawl_state.end_time)

    @patch('core.tasks.get_internal_links')
    @patch('core.models.CrawlState.objects.get')
    def test_crawl_website_state_update_error(self, mock_get_crawl_state, mock_get_internal_links):
        """
        Test scenario where updating the CrawlState fails.
        
        This test verifies that:
        1. When get_internal_links raises an exception
        2. And updating the CrawlState also raises an exception
        3. The task handles both exceptions gracefully
        """
        # Configure first mock to raise an exception
        mock_exception_message = "Crawl error"
        mock_get_internal_links.side_effect = Exception(mock_exception_message)
        
        # Configure second mock to raise an exception
        mock_get_crawl_state.side_effect = Exception("Database error")
        
        # Call the task - should not raise any exceptions
        crawl_website(
            url=self.test_url,
            crawl_state_id=self.crawl_state.id,
            link_limit=self.test_link_limit,
            language_code=self.test_language_code
        )
        
        # Verify the task handled both exceptions without crashing
        # No assertions needed as the test passes if no exceptions are raised

    @patch('core.tasks.get_internal_links')
    def test_crawl_website_with_different_parameters(self, mock_get_internal_links):
        """
        Test website crawling with different parameter values.
        
        This test verifies that:
        1. Different URL, link limit, and language code values are correctly passed
        2. The function works with various valid inputs
        """
        # Different test parameters
        different_url = "https://different-example.org"
        different_limit = 50
        different_language = "fr"
        
        # Call the task with different parameters
        crawl_website(
            url=different_url,
            crawl_state_id=self.crawl_state.id,
            link_limit=different_limit,
            language_code=different_language
        )
        
        # Assert get_internal_links was called with the different parameters
        mock_get_internal_links.assert_called_once_with(
            different_url, 
            crawl_state_id=self.crawl_state.id, 
            link_limit=different_limit,
            language_code=different_language
        )