import unittest
from django.test import TestCase, override_settings
from django.utils import timezone
from django.core.files.uploadedfile import SimpleUploadedFile
from unittest.mock import patch, MagicMock, Mock, call
import os
import re
import tempfile
from pathlib import Path
import json
from urllib.parse import urljoin
import unicodedata
import io
from datetime import UTC, datetime
from multiprocessing import Process

from accounts.models import User
from core.models import GuruType, DataSource, CrawlState, DataSourceExists
from integrations.models import Integration
from core.data_sources import (
    # Content extraction functions
    youtube_content_extraction, 
    jira_content_extraction,
    zendesk_content_extraction, 
    pdf_content_extraction,
    website_content_extraction,
    confluence_content_extraction,
    
    # Utility functions
    clean_title,
    clean_content,
    sanitize_filename,
    fetch_data_source_content,
    process_website_data_sources_batch,
    
    # Strategy classes
    PDFStrategy,
    YouTubeStrategy,
    WebsiteStrategy,
    JiraStrategy,
    ZendeskStrategy,
    ConfluenceStrategy,
    
    # Service classes
    CrawlService,
    YouTubeService,
    
    # Crawler
    InternalLinkSpider,
    get_internal_links,
    run_spider_process
)

from core.exceptions import (
    WebsiteContentExtractionError,
    WebsiteContentExtractionThrottleError,
    YouTubeContentExtractionError,
    JiraContentExtractionError,
    ZendeskContentExtractionError,
    PDFContentExtractionError,
    ConfluenceContentExtractionError,
    NotFoundError
)

from core.utils import get_default_settings
from youtube_transcript_api import NoTranscriptFound
from django.core.files.uploadedfile import SimpleUploadedFile


class ContentExtractionTestCase(TestCase):
    """Base test case for content extraction functions"""
    def setUp(self):
        # Initialize common test data
        get_default_settings()
        self.guru_type = GuruType.objects.create(
            slug="test-guru", 
            name="Test Guru", 
            custom=True, 
            active=True
        )


class YouTubeContentExtractionTestCase(TestCase):
    """Tests for YouTube content extraction functionality"""
    def setUp(self):
        # Initialize common test data
        get_default_settings()
        self.guru_type = GuruType.objects.create(
            slug="test-guru", 
            name="Test Guru", 
            custom=True, 
            active=True
        )
        self.test_url = "https://www.youtube.com/watch?v=test123"
    
    @patch('core.data_sources.YoutubeLoader')
    def test_youtube_content_extraction_success(self, mock_youtube_loader):
        """Test successful YouTube content extraction"""
        # Set up mock loader
        mock_loader_instance = MagicMock()
        mock_youtube_loader.from_youtube_url.return_value = mock_loader_instance
        
        # Create a mock document with metadata and content
        mock_document = MagicMock()
        mock_document.metadata = {
            "title": "Test YouTube Video",
            "author": "Test Author",
            "length": "10:30"
        }
        mock_document.page_content = "This is the transcript content. [applause] More content."
        
        # Set up the loader to return our mock document
        mock_loader_instance.load.return_value = [mock_document]
        
        # Call function under test
        result = youtube_content_extraction(self.test_url)
        
        # Verify results
        self.assertEqual(result['metadata']['title'], "Test YouTube Video")
        self.assertEqual(result['metadata']['author'], "Test Author")
        # Check that content was cleaned (removing things in square brackets)
        self.assertEqual(result['content'], "This is the transcript content.  More content.")
        
        # Verify loader was called correctly
        mock_youtube_loader.from_youtube_url.assert_called_once_with(
            self.test_url,
            add_video_info=True,
            language=['en', 'hi', 'es', 'zh-Hans', 'zh-Hant', 'ar'],
            translation='en',
            chunk_size_seconds=30
        )
    
    @patch('core.data_sources.YoutubeLoader')
    def test_youtube_content_extraction_with_custom_language(self, mock_youtube_loader):
        """Test YouTube content extraction with custom language code"""
        # Set up mock loader
        mock_loader_instance = MagicMock()
        mock_youtube_loader.from_youtube_url.return_value = mock_loader_instance
        
        # Create a mock document with metadata and content
        mock_document = MagicMock()
        mock_document.metadata = {"title": "Test Video"}
        mock_document.page_content = "Contenu de la transcription."
        
        # Set up the loader to return our mock document
        mock_loader_instance.load.return_value = [mock_document]
        
        # Call function under test with custom language
        result = youtube_content_extraction(self.test_url, language_code='fr')
        
        # Verify language code was passed correctly
        mock_youtube_loader.from_youtube_url.assert_called_once_with(
            self.test_url,
            add_video_info=True,
            language=['en', 'hi', 'es', 'zh-Hans', 'zh-Hant', 'ar', 'fr'],
            translation='fr',
            chunk_size_seconds=30
        )
    
    @patch('core.data_sources.YoutubeLoader')
    def test_youtube_content_extraction_no_transcript(self, mock_youtube_loader):
        """Test YouTube content extraction when no transcript is available"""
        # Set up mock loader to raise NoTranscriptFound
        mock_loader_instance = MagicMock()
        mock_youtube_loader.from_youtube_url.return_value = mock_loader_instance
        mock_loader_instance.load.side_effect = NoTranscriptFound(video_id="test123", requested_language_codes=['en'], transcript_data=None)
        
        # Call function under test and verify it raises appropriate exception
        with self.assertRaises(YouTubeContentExtractionError) as context:
            youtube_content_extraction(self.test_url)
        
        # Verify error message
        error_message = str(context.exception)
        self.assertIn("No transcript found", error_message)
    
    @patch('core.data_sources.YoutubeLoader')
    def test_youtube_content_extraction_empty_transcript(self, mock_youtube_loader):
        """Test YouTube content extraction when transcript is empty"""
        # Set up mock loader to return empty list
        mock_loader_instance = MagicMock()
        mock_youtube_loader.from_youtube_url.return_value = mock_loader_instance
        mock_loader_instance.load.return_value = []
        
        # Call function under test and verify it raises appropriate exception
        with self.assertRaises(YouTubeContentExtractionError) as context:
            youtube_content_extraction(self.test_url)
        
        # Verify error message
        error_message = str(context.exception)
        self.assertIn("No transcript found", error_message)
    
    @patch('core.data_sources.YoutubeLoader')
    def test_youtube_content_extraction_loader_exception(self, mock_youtube_loader):
        """Test YouTube content extraction when loader throws an exception"""
        # Set up mock loader to raise an exception
        mock_youtube_loader.from_youtube_url.side_effect = Exception("YouTube API error")
        
        # Call function under test and verify it raises appropriate exception
        with self.assertRaises(YouTubeContentExtractionError) as context:
            youtube_content_extraction(self.test_url)
        
        # Verify error message
        error_message = str(context.exception)
        self.assertIn("Error extracting content", error_message)


class PDFContentExtractionTestCase(TestCase):
    """Tests for PDF content extraction functionality"""
    def setUp(self):
        # Initialize common test data
        get_default_settings()
        self.guru_type = GuruType.objects.create(
            slug="test-guru", 
            name="Test Guru", 
            custom=True, 
            active=True
        )
        self.test_pdf_path = "https://example.com/test.pdf"
    
    @patch('core.data_sources.replace_media_root_with_nginx_base_url')
    @patch('core.data_sources.PyPDFLoader')
    def test_pdf_content_extraction_success(self, mock_pdf_loader, mock_replace_path):
        """Test successful PDF content extraction"""
        # Set up mocks
        mock_replace_path.return_value = self.test_pdf_path
        
        # Create mock pages
        mock_page1 = MagicMock()
        mock_page1.page_content = "Page 1 content"
        mock_page2 = MagicMock()
        mock_page2.page_content = "Page 2 content"
        
        # Set up mock loader
        mock_loader_instance = MagicMock()
        mock_pdf_loader.return_value = mock_loader_instance
        mock_loader_instance.load.return_value = [mock_page1, mock_page2]
        
        # Call function under test
        content = pdf_content_extraction(self.test_pdf_path)
        
        # Verify results
        self.assertEqual(content, "Page 1 content\nPage 2 content")
        
        # Verify mocks were called correctly
        mock_replace_path.assert_called_once_with(self.test_pdf_path)
        mock_pdf_loader.assert_called_once_with(self.test_pdf_path)
        mock_loader_instance.load.assert_called_once()
    
    @patch('core.data_sources.replace_media_root_with_nginx_base_url')
    @patch('core.data_sources.PyPDFLoader')
    def test_pdf_content_extraction_sanitizes_null_bytes(self, mock_pdf_loader, mock_replace_path):
        """Test PDF content extraction sanitizes null bytes"""
        # Set up mocks
        mock_replace_path.return_value = self.test_pdf_path
        
        # Create mock page with null bytes
        mock_page = MagicMock()
        mock_page.page_content = "Content with\x00null\x00bytes"
        
        # Set up mock loader
        mock_loader_instance = MagicMock()
        mock_pdf_loader.return_value = mock_loader_instance
        mock_loader_instance.load.return_value = [mock_page]
        
        # Call function under test
        content = pdf_content_extraction(self.test_pdf_path)
        
        # Verify results - null bytes should be removed
        self.assertEqual(content, "Content withnullbytes")
    
    @patch('core.data_sources.replace_media_root_with_nginx_base_url')
    @patch('core.data_sources.PyPDFLoader')
    def test_pdf_content_extraction_error(self, mock_pdf_loader, mock_replace_path):
        """Test PDF content extraction when loader throws an exception"""
        # Set up mocks
        mock_replace_path.return_value = self.test_pdf_path
        
        # Set up mock loader to raise an exception
        mock_loader_instance = MagicMock()
        mock_pdf_loader.return_value = mock_loader_instance
        error_msg = f"Could not open file {self.test_pdf_path}"
        mock_loader_instance.load.side_effect = Exception(error_msg)
        
        # Call function under test and verify it raises appropriate exception
        with self.assertRaises(PDFContentExtractionError) as context:
            pdf_content_extraction(self.test_pdf_path)
        
        # Verify error message has path replaced
        error_message = str(context.exception)
        self.assertNotIn(self.test_pdf_path, error_message)
        self.assertIn("pdf_path", error_message)


class WebsiteContentExtractionTestCase(TestCase):
    """Tests for website content extraction functionality"""
    def setUp(self):
        # Initialize common test data
        get_default_settings()
        self.guru_type = GuruType.objects.create(
            slug="test-guru", 
            name="Test Guru", 
            custom=True, 
            active=True
        )
        self.test_url = "https://example.com/page"
    
    @patch('core.data_sources.get_web_scraper')
    def test_website_content_extraction_success(self, mock_get_web_scraper):
        """Test successful website content extraction"""
        # Set up mock scraper
        mock_scraper = MagicMock()
        mock_scraper.scrape_url.return_value = ("Test Title", "Test Content")
        mock_get_web_scraper.return_value = (mock_scraper, "test_scraper")
        
        # Call function under test
        title, content, scrape_tool = website_content_extraction(self.test_url)
        
        # Verify results
        self.assertEqual(title, "Test Title")
        self.assertEqual(content, "Test Content")
        self.assertEqual(scrape_tool, "test_scraper")
        mock_scraper.scrape_url.assert_called_once_with(self.test_url)
    
    @patch('core.data_sources.get_web_scraper')
    def test_website_content_extraction_http_error(self, mock_get_web_scraper):
        """Test website content extraction with HTTP error"""
        # Set up mock scraper to raise exception
        mock_scraper = MagicMock()
        mock_exception = Exception("HTTP Error")
        mock_exception.response = MagicMock()
        mock_exception.response.status_code = 404
        mock_exception.response.reason = "Not Found"
        mock_exception.response.content = b"Not Found"
        mock_scraper.scrape_url.side_effect = mock_exception
        mock_get_web_scraper.return_value = (mock_scraper, "test_scraper")
        
        # Call function under test and verify it raises appropriate exception
        with self.assertRaises(WebsiteContentExtractionError) as context:
            website_content_extraction(self.test_url)
        
        # Verify error message contains status code and reason
        error_message = str(context.exception)
        self.assertIn("404", error_message)
        self.assertIn("Not Found", error_message)
    
    @patch('core.data_sources.get_web_scraper')
    def test_website_content_extraction_throttle(self, mock_get_web_scraper):
        """Test website content extraction with throttle error (429)"""
        # Set up mock scraper to raise throttle exception
        mock_scraper = MagicMock()
        mock_exception = Exception("Throttled")
        mock_exception.response = MagicMock()
        mock_exception.response.status_code = 429
        mock_exception.response.reason = "Too Many Requests"
        mock_exception.response.content = b"Rate limit exceeded"
        mock_scraper.scrape_url.side_effect = mock_exception
        mock_get_web_scraper.return_value = (mock_scraper, "test_scraper")
        
        # Call function under test and verify it raises appropriate exception
        with self.assertRaises(WebsiteContentExtractionThrottleError) as context:
            website_content_extraction(self.test_url)
        
        # Verify error message contains status code and reason
        error_message = str(context.exception)
        self.assertIn("429", error_message)
        self.assertIn("Too Many Requests", error_message)
    
    @patch('core.data_sources.clean_title')
    @patch('core.data_sources.clean_content')
    @patch('core.data_sources.get_web_scraper')
    def test_website_content_extraction_cleans_output(self, mock_get_web_scraper, mock_clean_content, mock_clean_title):
        """Test that website content extraction cleans title and content"""
        # Set up mock scraper
        mock_scraper = MagicMock()
        mock_scraper.scrape_url.return_value = ("Raw Title", "Raw Content")
        mock_get_web_scraper.return_value = (mock_scraper, "test_scraper")
        
        # Set up mocks for cleaning functions
        mock_clean_title.return_value = "Cleaned Title"
        mock_clean_content.return_value = "Cleaned Content"
        
        # Call function under test
        title, content, scrape_tool = website_content_extraction(self.test_url)
        
        # Verify cleaning functions were called
        mock_clean_title.assert_called_once_with("Raw Title")
        mock_clean_content.assert_called_once_with("Raw Content")
        
        # Verify cleaned results
        self.assertEqual(title, "Cleaned Title")
        self.assertEqual(content, "Cleaned Content")


class ProcessWebsiteBatchTestCase(TestCase):
    """Tests for batch processing of website data sources"""
    def setUp(self):
        # Initialize common test data
        get_default_settings()
        self.guru_type = GuruType.objects.create(
            slug="test-guru", 
            name="Test Guru", 
            custom=True, 
            active=True
        )
        
        # Create test data sources
        self.data_source1 = DataSource.objects.create(
            type=DataSource.Type.WEBSITE,
            guru_type=self.guru_type,
            url="https://example.com/page1",
            status=DataSource.Status.NOT_PROCESSED
        )
        
        self.data_source2 = DataSource.objects.create(
            type=DataSource.Type.WEBSITE,
            guru_type=self.guru_type,
            url="https://example.com/page2",
            status=DataSource.Status.NOT_PROCESSED
        )
        
        self.data_sources = [self.data_source1, self.data_source2]
    
    @patch('core.data_sources.get_web_scraper')
    def test_process_website_data_sources_batch_success(self, mock_get_web_scraper):
        """Test successful batch processing of website data sources"""
        # Set up mock scraper
        mock_scraper = MagicMock()
        mock_scraper.scrape_urls_batch.return_value = (
            [
                ("https://example.com/page1", "Title 1", "Content 1"),
                ("https://example.com/page2", "Title 2", "Content 2")
            ],
            []  # No failed URLs
        )
        mock_get_web_scraper.return_value = (mock_scraper, "test_scraper")
        
        # Call function under test
        processed_sources = process_website_data_sources_batch(self.data_sources)
        
        # Verify results
        self.assertEqual(len(processed_sources), 2)
        
        # Check the first data source using returned objects
        data_source1 = next(ds for ds in processed_sources if ds.url == "https://example.com/page1")
        self.assertEqual(data_source1.title, "Title 1")
        self.assertEqual(data_source1.content, "Content 1")
        self.assertEqual(data_source1.scrape_tool, "test_scraper")
        self.assertEqual(data_source1.status, DataSource.Status.SUCCESS)
        self.assertEqual(data_source1.error, "")
        
        # Check the second data source using returned objects
        data_source2 = next(ds for ds in processed_sources if ds.url == "https://example.com/page2")
        self.assertEqual(data_source2.title, "Title 2")
        self.assertEqual(data_source2.content, "Content 2")
        self.assertEqual(data_source2.scrape_tool, "test_scraper")
        self.assertEqual(data_source2.status, DataSource.Status.SUCCESS)
        self.assertEqual(data_source2.error, "")
        
        # Verify scraper was called with correct URLs
        mock_scraper.scrape_urls_batch.assert_called_once_with([
            "https://example.com/page1",
            "https://example.com/page2"
        ])
    
    @patch('core.data_sources.get_web_scraper')
    def test_process_website_data_sources_batch_partial_failure(self, mock_get_web_scraper):
        """Test batch processing with some URLs failing"""
        # Set up mock scraper
        mock_scraper = MagicMock()
        mock_scraper.scrape_urls_batch.return_value = (
            [
                ("https://example.com/page1", "Title 1", "Content 1")
            ],
            [
                ("https://example.com/page2", "Error message")
            ]
        )
        mock_get_web_scraper.return_value = (mock_scraper, "test_scraper")
        
        # Force a second attempt to be empty
        mock_scraper.scrape_urls_batch.side_effect = [
            (
                [("https://example.com/page1", "Title 1", "Content 1")],
                [("https://example.com/page2", "Error message")]
            ),
            ([], [("https://example.com/page2", "Failed after retry")])
        ]
        
        # Call function under test
        processed_sources = process_website_data_sources_batch(self.data_sources)
        
        # Verify results
        self.assertEqual(len(processed_sources), 2)
        
        # Check the successful data source using returned objects
        data_source1 = next(ds for ds in processed_sources if ds.url == "https://example.com/page1")
        self.assertEqual(data_source1.title, "Title 1")
        self.assertEqual(data_source1.content, "Content 1")
        self.assertEqual(data_source1.status, DataSource.Status.SUCCESS)
        
        # Check the failed data source using returned objects
        data_source2 = next(ds for ds in processed_sources if ds.url == "https://example.com/page2")
        self.assertEqual(data_source2.status, DataSource.Status.FAIL)
        self.assertIn("URL was not processed", data_source2.error)
    
    @patch('core.data_sources.get_web_scraper')
    def test_process_website_data_sources_batch_throttle(self, mock_get_web_scraper):
        """Test batch processing with throttling error"""
        # Set up mock scraper to raise throttle exception
        mock_scraper = MagicMock()
        mock_scraper.scrape_urls_batch.side_effect = WebsiteContentExtractionThrottleError("Rate limit exceeded")
        mock_get_web_scraper.return_value = (mock_scraper, "test_scraper")
        
        # Call function under test
        processed_sources = process_website_data_sources_batch(self.data_sources)
        
        # Verify results
        self.assertEqual(len(processed_sources), 2)
        
        # Check both data sources are marked as NOT_PROCESSED using returned objects
        for data_source in processed_sources:
            self.assertEqual(data_source.status, DataSource.Status.NOT_PROCESSED)
            self.assertIn("Rate limit exceeded", data_source.error)


class UtilityFunctionsTestCase(TestCase):
    """Test case for utility functions in data_sources.py"""

    def setUp(self):
        get_default_settings()
    
    def test_clean_title_removes_copy_to_clipboard(self):
        """Test that clean_title removes 'Copy to clipboard' text"""
        title = "Test Title Copy to clipboard"
        cleaned_title = clean_title(title)
        self.assertEqual(cleaned_title, "Test Title")
    
    def test_clean_title_removes_contents_menu(self):
        """Test that clean_title removes text after ContentsMenuExpandLight"""
        title = "Test Title ContentsMenuExpandLight Some other text"
        cleaned_title = clean_title(title)
        self.assertEqual(cleaned_title, "Test Title")
    
    def test_clean_title_removes_canary_text(self):
        """Test that clean_title removes canary feature text"""
        title = "Test Title - This feature is available in the latest Canary"
        cleaned_title = clean_title(title)
        self.assertEqual(cleaned_title, "Test Title")
    
    def test_clean_title_removes_social_media_text(self):
        """Test that clean_title removes social media links text"""
        title = "Test Title TwitterFacebookInstagramLinkedInYouTube"
        cleaned_title = clean_title(title)
        self.assertEqual(cleaned_title, "Test Title")
    
    def test_clean_title_removes_repeated_sequences(self):
        """Test that clean_title removes repeated character sequences"""
        title = "Test TitleTitleTitle"
        cleaned_title = clean_title(title)
        self.assertEqual(cleaned_title, "Test Title")
    
    def test_clean_content_removes_image_references(self):
        """Test that clean_content removes markdown image references"""
        content = "This is text with an image ![image](https://example.com/image.jpg) embedded."
        cleaned_content = clean_content(content)
        self.assertEqual(cleaned_content, "This is text with an image  embedded.")
    
    def test_clean_content_removes_clipboard_text(self):
        """Test that clean_content removes 'Copy to clipboard' lines"""
        content = "This is line 1\nCopy to clipboard\nThis is line 2"
        cleaned_content = clean_content(content)
        self.assertEqual(cleaned_content, "This is line 1This is line 2")
    
    def test_clean_content_removes_repeated_separators(self):
        """Test that clean_content removes repeated separator lines"""
        content = "This is line 1\n=============\nThis is line 2"
        cleaned_content = clean_content(content)
        self.assertEqual(cleaned_content, "This is line 1\n\nThis is line 2")
    
    def test_clean_content_removes_error_messages(self):
        """Test that clean_content removes common error messages"""
        content = "You signed in with another tab or window.\nThis is valid content.\nYou cant perform that action at this time."
        cleaned_content = clean_content(content)
        self.assertEqual(cleaned_content, "This is valid content.")
    
    def test_sanitize_filename_removes_non_ascii(self):
        """Test that sanitize_filename removes non-ASCII characters"""
        filename = "filéñamé.txt"
        sanitized = sanitize_filename(filename)
        self.assertEqual(sanitized, "filename.txt")
    
    def test_sanitize_filename_replaces_special_chars(self):
        """Test that sanitize_filename replaces special characters with underscores"""
        filename = "file name with spaces!.txt"
        sanitized = sanitize_filename(filename)
        self.assertEqual(sanitized, "file_name_with_spaces_.txt")
    
    def test_sanitize_filename_handles_unicode_normalization(self):
        """Test that sanitize_filename properly normalizes Unicode characters"""
        # Create a filename with unicode characters that should be normalized
        filename = "café.txt"  # é can be represented as a single character or as 'e' + combining accent
        sanitized = sanitize_filename(filename)
        self.assertEqual(sanitized, "cafe.txt")


class StrategyTestCase(TestCase):
    """Base test case for strategy pattern implementations"""
    def setUp(self):
        # Create a guru type that will be used across all strategy tests
        get_default_settings()
        self.guru_type = GuruType.objects.create(
            slug="test-guru", 
            name="Test Guru", 
            custom=True, 
            active=True
        )
        self.user = User.objects.create_user(
            name="Test User",
            email="test@example.com",
            password="testpassword"
        )


class ServiceTestCase(TestCase):
    """Base test case for service classes"""
    def setUp(self):
        # Setup common data for service tests
        get_default_settings()
        self.guru_type = GuruType.objects.create(
            slug="test-guru", 
            name="Test Guru", 
            custom=True, 
            active=True
        )
        self.user = User.objects.create_user(
            name="Test User",
            email="test@example.com",
            password="testpassword"
        )


class JiraContentExtractionTestCase(TestCase):
    """Tests for Jira content extraction functionality"""
    def setUp(self):
        # Initialize common test data
        get_default_settings()
        self.guru_type = GuruType.objects.create(
            slug="test-guru", 
            name="Test Guru", 
            custom=True, 
            active=True
        )
        self.user = User.objects.create_user(
            name="Test User",
            email="test@example.com",
            password="testpassword"
        )
        self.integration = Integration(
            guru_type=self.guru_type,
            type=Integration.Type.JIRA
        )
        self.integration.guru_type.maintainers.add(self.user)
        self.integration.save()
        self.jira_issue_url = "https://test-jira.atlassian.net/browse/TEST-123"
    
    @patch('core.data_sources.JiraRequester')
    def test_jira_content_extraction_success(self, mock_jira_requester_class):
        """Test successful Jira content extraction"""
        # Set up mock requester
        mock_requester = MagicMock()
        mock_jira_requester_class.return_value = mock_requester
        
        # Set up mock response
        mock_requester.get_issue.return_value = {
            "title": "Test Issue Title",
            "content": "Test issue description with details."
        }
        
        # Call function under test
        title, content = jira_content_extraction(self.integration, self.jira_issue_url)
        
        # Verify results
        self.assertEqual(title, "Test Issue Title")
        self.assertEqual(content, "Test issue description with details.")
        
        # Verify requester was created with the correct integration
        mock_jira_requester_class.assert_called_once_with(self.integration)
        
        # Verify get_issue was called with the correct issue key
        mock_requester.get_issue.assert_called_once_with("TEST-123")
    
    @patch('core.data_sources.JiraRequester')
    def test_jira_content_extraction_error(self, mock_jira_requester_class):
        """Test Jira content extraction when requester throws an exception"""
        # Set up mock requester to raise an exception
        mock_requester = MagicMock()
        mock_jira_requester_class.return_value = mock_requester
        mock_requester.get_issue.side_effect = Exception("Authentication failed")
        
        # Call function under test and verify it raises appropriate exception
        with self.assertRaises(JiraContentExtractionError) as context:
            jira_content_extraction(self.integration, self.jira_issue_url)
        
        # Verify error message
        error_message = str(context.exception)
        self.assertIn("Authentication failed", error_message)


class ZendeskContentExtractionTestCase(TestCase):
    """Tests for Zendesk content extraction functionality"""
    def setUp(self):
        # Initialize common test data
        get_default_settings()
        self.guru_type = GuruType.objects.create(
            slug="test-guru", 
            name="Test Guru", 
            custom=True, 
            active=True
        )
        self.user = User.objects.create_user(
            name="Test User",
            email="test@example.com",
            password="testpassword"
        )
        self.integration = Integration(
            guru_type=self.guru_type,
            type=Integration.Type.ZENDESK
        )
        self.integration.guru_type.maintainers.add(self.user)
        self.integration.save()
        self.zendesk_ticket_url = "https://test-support.zendesk.com/agent/tickets/123"
        self.zendesk_article_url = "https://test-support.zendesk.com/hc/en-us/articles/123-test-article"
    
    @patch('core.data_sources.ZendeskRequester')
    def test_zendesk_ticket_content_extraction_success(self, mock_zendesk_requester_class):
        """Test successful Zendesk ticket content extraction"""
        # Set up mock requester
        mock_requester = MagicMock()
        mock_zendesk_requester_class.return_value = mock_requester
        
        # Set up mock response
        mock_requester.get_ticket.return_value = {
            "title": "Test Ticket Title",
            "content": "Test ticket description and comments."
        }
        
        # Call function under test
        title, content = zendesk_content_extraction(self.integration, self.zendesk_ticket_url)
        
        # Verify results
        self.assertEqual(title, "Test Ticket Title")
        self.assertEqual(content, "Test ticket description and comments.")
        
        # Verify requester was created with the correct integration
        mock_zendesk_requester_class.assert_called_once_with(self.integration)
        
        # Verify get_ticket was called with the correct ticket ID
        mock_requester.get_ticket.assert_called_once_with("123")
    
    @patch('core.data_sources.ZendeskRequester')
    def test_zendesk_article_content_extraction_success(self, mock_zendesk_requester_class):
        """Test successful Zendesk article content extraction"""
        # Set up mock requester
        mock_requester = MagicMock()
        mock_zendesk_requester_class.return_value = mock_requester
        
        # Set up mock response
        mock_requester.get_article.return_value = {
            "title": "Test Article Title",
            "content": "Test article content with details."
        }
        
        # Call function under test
        title, content = zendesk_content_extraction(self.integration, self.zendesk_article_url)
        
        # Verify results
        self.assertEqual(title, "Test Article Title")
        self.assertEqual(content, "Test article content with details.")
        
        # Verify requester was created with the correct integration
        mock_zendesk_requester_class.assert_called_once_with(self.integration)
        
        # Verify get_article was called with the correct article ID
        mock_requester.get_article.assert_called_once_with("123")
    
    @patch('core.data_sources.ZendeskRequester')
    def test_zendesk_content_extraction_error(self, mock_zendesk_requester_class):
        """Test Zendesk content extraction when requester throws an exception"""
        # Set up mock requester to raise an exception
        mock_requester = MagicMock()
        mock_zendesk_requester_class.return_value = mock_requester
        mock_requester.get_ticket.side_effect = Exception("Authentication failed")
        
        # Call function under test and verify it raises appropriate exception
        with self.assertRaises(ZendeskContentExtractionError) as context:
            zendesk_content_extraction(self.integration, self.zendesk_ticket_url)
        
        # Verify error message
        error_message = str(context.exception)
        self.assertIn("Authentication failed", error_message)


class ConfluenceContentExtractionTestCase(TestCase):
    """Tests for Confluence content extraction functionality"""
    def setUp(self):
        # Initialize common test data
        get_default_settings()
        self.guru_type = GuruType.objects.create(
            slug="test-guru", 
            name="Test Guru", 
            custom=True, 
            active=True
        )
        self.user = User.objects.create_user(
            name="Test User",
            email="test@example.com",
            password="testpassword"
        )
        self.integration = Integration(
            guru_type=self.guru_type,
            type=Integration.Type.CONFLUENCE
        )
        self.integration.guru_type.maintainers.add(self.user)
        self.integration.save()
        self.confluence_page_url = "https://test.atlassian.net/wiki/spaces/TEST/pages/123456/Test+Page"
        self.confluence_space_url = "https://test.atlassian.net/wiki/spaces/TEST/overview"
    
    @patch('core.data_sources.ConfluenceRequester')
    def test_confluence_page_content_extraction_success(self, mock_confluence_requester_class):
        """Test successful Confluence page content extraction"""
        # Set up mock requester
        mock_requester = MagicMock()
        mock_confluence_requester_class.return_value = mock_requester
        
        # Set up mock response
        mock_requester.get_page_content.return_value = {
            "title": "Test Page Title",
            "content": "Test page content with details."
        }
        
        # Call function under test
        title, content = confluence_content_extraction(self.integration, self.confluence_page_url)
        
        # Verify results
        self.assertEqual(title, "Test Page Title")
        self.assertEqual(content, "Test page content with details.")
        
        # Verify requester was created with the correct integration
        mock_confluence_requester_class.assert_called_once_with(self.integration)
        
        # Verify get_page_content was called with the correct page ID
        mock_requester.get_page_content.assert_called_once_with("123456")
    
    @patch('core.data_sources.ConfluenceRequester')
    def test_confluence_space_content_extraction_success(self, mock_confluence_requester_class):
        """Test successful Confluence space content extraction (with homepage)"""
        # Set up mock requester
        mock_requester = MagicMock()
        mock_confluence_requester_class.return_value = mock_requester
        
        # Set up mock responses
        mock_requester.get_space_with_homepage.return_value = {
            "homepage": {
                "id": "789012"
            }
        }
        mock_requester.get_page_content.return_value = {
            "title": "Test Homepage Title",
            "content": "Test homepage content."
        }
        
        # Call function under test
        title, content = confluence_content_extraction(self.integration, self.confluence_space_url)
        
        # Verify results
        self.assertEqual(title, "Test Homepage Title")
        self.assertEqual(content, "Test homepage content.")
        
        # Verify requester was created with the correct integration
        mock_confluence_requester_class.assert_called_once_with(self.integration)
        
        # Verify get_space_with_homepage was called with the correct space key
        mock_requester.get_space_with_homepage.assert_called_once_with("TEST")
        
        # Verify get_page_content was called with the homepage ID
        mock_requester.get_page_content.assert_called_once_with("789012")
    
    @patch('core.data_sources.ConfluenceRequester')
    def test_confluence_space_content_extraction_no_homepage(self, mock_confluence_requester_class):
        """Test Confluence space content extraction without homepage"""
        # Set up mock requester
        mock_requester = MagicMock()
        mock_confluence_requester_class.return_value = mock_requester
        
        # Set up mock responses - no homepage in space
        mock_requester.get_space_with_homepage.return_value = {
            "key": "TEST",
            "name": "Test Space"
            # No homepage key
        }
        
        # Call function under test
        title, content = confluence_content_extraction(self.integration, self.confluence_space_url)
        
        # Verify results - should create fallback content
        self.assertEqual(title, "Space: TEST")
        self.assertTrue("This is a Confluence space" in content)
        
        # Verify requester was created with the correct integration
        mock_confluence_requester_class.assert_called_once_with(self.integration)
        
        # Verify get_space_with_homepage was called with the correct space key
        mock_requester.get_space_with_homepage.assert_called_once_with("TEST")
        
        # Verify get_page_content was NOT called
        mock_requester.get_page_content.assert_not_called()
    
    @patch('core.data_sources.ConfluenceRequester')
    def test_confluence_content_extraction_error(self, mock_confluence_requester_class):
        """Test Confluence content extraction when requester throws an exception"""
        # Set up mock requester to raise an exception
        mock_requester = MagicMock()
        mock_confluence_requester_class.return_value = mock_requester
        mock_requester.get_page_content.side_effect = Exception("Authentication failed")
        
        # Call function under test and verify it raises appropriate exception
        with self.assertRaises(ConfluenceContentExtractionError) as context:
            confluence_content_extraction(self.integration, self.confluence_page_url)
        
        # Verify error message
        error_message = str(context.exception)
        self.assertIn("Authentication failed", error_message)


class FetchDataSourceContentTestCase(TestCase):
    """Tests for the fetch_data_source_content function"""
    def setUp(self):
        # Initialize common test data
        get_default_settings()
        self.guru_type = GuruType.objects.create(
            slug="test-guru", 
            name="Test Guru", 
            custom=True, 
            active=True
        )
        self.user = User.objects.create_user(
            name="Test User",
            email="test@example.com",
            password="testpassword"
        )
        self.integration = Integration(
            guru_type=self.guru_type,
            type=Integration.Type.JIRA
        )
        self.integration.guru_type.maintainers.add(self.user)
        self.integration.save()
        self.language_code = "en"
    
    @patch('core.data_sources.pdf_content_extraction')
    def test_fetch_data_source_content_pdf(self, mock_pdf_extraction):
        """Test fetch_data_source_content for PDF data source"""
        # Create a test PDF data source
        file = SimpleUploadedFile("test.pdf", b"%PDF-1.4\n1 0 obj\n<</Type/Catalog/Pages 2 0 R>>\nendobj\n2 0 obj\n<</Type/Pages/Count 1>>\nendobj\ntrailer\n<</Root 1 0 R>>\n%%EOF", content_type="application/pdf")
        data_source = DataSource.objects.create(
            type=DataSource.Type.PDF,
            guru_type=self.guru_type,
            url="https://example.com/test.pdf",
            file=file
        )
        
        # Set up mock extraction function
        mock_pdf_extraction.return_value = "PDF content extracted"
        
        # Call function under test
        result = fetch_data_source_content(self.integration, data_source, self.language_code)
        
        # Verify PDF extraction was called
        mock_pdf_extraction.assert_called_once_with(data_source.url)
        
        # Verify data source was updated correctly
        self.assertEqual(result.content, "PDF content extracted")
        self.assertEqual(result.scrape_tool, "pdf")
        self.assertEqual(result.error, "")
    
    @patch('core.data_sources.website_content_extraction')
    def test_fetch_data_source_content_website(self, mock_website_extraction):
        """Test fetch_data_source_content for website data source"""
        # Create a test website data source
        data_source = DataSource.objects.create(
            type=DataSource.Type.WEBSITE,
            guru_type=self.guru_type,
            url="https://example.com/page"
        )
        
        # Set up mock extraction function
        mock_website_extraction.return_value = ("Website Title", "Website content", "test_scraper")
        
        # Call function under test
        result = fetch_data_source_content(self.integration, data_source, self.language_code)
        
        # Verify website extraction was called
        mock_website_extraction.assert_called_once_with(data_source.url)
        
        # Verify data source was updated correctly
        self.assertEqual(result.title, "Website Title")
        self.assertEqual(result.content, "Website content")
        self.assertEqual(result.scrape_tool, "test_scraper")
        self.assertEqual(result.error, "")
    
    @patch('core.data_sources.youtube_content_extraction')
    def test_fetch_data_source_content_youtube(self, mock_youtube_extraction):
        """Test fetch_data_source_content for YouTube data source"""
        # Create a test YouTube data source
        data_source = DataSource.objects.create(
            type=DataSource.Type.YOUTUBE,
            guru_type=self.guru_type,
            url="https://www.youtube.com/watch?v=test123"
        )
        
        # Set up mock extraction function
        mock_youtube_extraction.return_value = {
            "metadata": {"title": "YouTube Video Title"},
            "content": "YouTube transcript content"
        }
        
        # Call function under test
        result = fetch_data_source_content(self.integration, data_source, self.language_code)
        
        # Verify YouTube extraction was called
        mock_youtube_extraction.assert_called_once_with(data_source.url, self.language_code)
        
        # Verify data source was updated correctly
        self.assertEqual(result.title, "YouTube Video Title")
        self.assertEqual(result.content, "YouTube transcript content")
        self.assertEqual(result.scrape_tool, "youtube")
        self.assertEqual(result.error, "")
    
    @patch('core.data_sources.jira_content_extraction')
    def test_fetch_data_source_content_jira(self, mock_jira_extraction):
        """Test fetch_data_source_content for Jira data source"""
        # Create a test Jira data source
        data_source = DataSource.objects.create(
            type=DataSource.Type.JIRA,
            guru_type=self.guru_type,
            url="https://test.atlassian.net/browse/TEST-123"
        )
        
        # Set up mock extraction function
        mock_jira_extraction.return_value = ("Jira Issue Title", "Jira issue content")
        
        # Call function under test
        result = fetch_data_source_content(self.integration, data_source, self.language_code)
        
        # Verify Jira extraction was called
        mock_jira_extraction.assert_called_once_with(self.integration, data_source.url)
        
        # Verify data source was updated correctly
        self.assertEqual(result.title, "Jira Issue Title")
        self.assertEqual(result.content, "Jira issue content")
        self.assertEqual(result.scrape_tool, "jira")
        self.assertEqual(result.error, "")


class PDFStrategyTest(StrategyTestCase):
    """Tests for PDFStrategy class"""

    def setUp(self):
        super().setUp()
        self.strategy = PDFStrategy()
        
    def test_create_pdf_success(self):
        """Test creating a new PDF data source successfully"""
        # Create a mock PDF file
        pdf_content = b"%PDF-1.4\n1 0 obj\n<</Type/Catalog/Pages 2 0 R>>\nendobj\n2 0 obj\n<</Type/Pages/Count 1>>\nendobj\ntrailer\n<</Root 1 0 R>>\n%%EOF"
        pdf_file = SimpleUploadedFile("test_doc.pdf", pdf_content, content_type="application/pdf")
        
        # Call the strategy create method
        result = self.strategy.create(self.guru_type, pdf_file)
        
        uploaded_file_name = result['file']
        if '-' in uploaded_file_name:
            uploaded_file_name = uploaded_file_name.split('-')[0] + '.pdf'
        # Verify the result
        self.assertEqual(result['type'], 'PDF')
        self.assertEqual(uploaded_file_name, 'test_doc.pdf')
        self.assertEqual(result['status'], 'success')
        self.assertTrue('id' in result)
        
        # Verify the data source was created in the database
        data_source = DataSource.objects.get(id=result['id'])
        data_source_file_name = data_source.file.name.split('/')[-1]
        if '-' in data_source_file_name:
            data_source_file_name = data_source_file_name.split('-')[0] + '.pdf'
        self.assertEqual(data_source.type, DataSource.Type.PDF)
        self.assertEqual(data_source.guru_type, self.guru_type)
        self.assertEqual(data_source_file_name, uploaded_file_name)

    @patch('core.models.DataSource.objects.create')
    def test_create_pdf_exists(self, mock_create):
        """Test creating a PDF data source that already exists"""
        # Make the create method raise DataSourceExists
        existing_data = {'id': 123, 'title': 'Existing PDF'}
        mock_create.side_effect = DataSourceExists(existing_data)
        
        # Create a mock PDF file
        pdf_content = b"%PDF-1.4\n1 0 obj\n<</Type/Catalog/Pages 2 0 R>>\nendobj\n2 0 obj\n<</Type/Pages/Count 1>>\nendobj\ntrailer\n<</Root 1 0 R>>\n%%EOF"
        pdf_file = SimpleUploadedFile("existing.pdf", pdf_content, content_type="application/pdf")
        
        # Call the strategy create method
        result = self.strategy.create(self.guru_type, pdf_file)
        
        # Verify the result
        self.assertEqual(result['type'], 'PDF')
        self.assertEqual(result['file'], 'existing.pdf')
        self.assertEqual(result['status'], 'exists')
        self.assertEqual(result['id'], 123)
        self.assertEqual(result['title'], 'Existing PDF')
    
    @patch('core.models.DataSource.objects.create')
    def test_create_pdf_error(self, mock_create):
        """Test creating a PDF data source with an error"""
        # Make the create method raise an exception
        mock_create.side_effect = Exception("Test error")
        
        # Create a mock PDF file
        pdf_content = b"%PDF-1.4\n1 0 obj\n<</Type/Catalog/Pages 2 0 R>>\nendobj\n2 0 obj\n<</Type/Pages/Count 1>>\nendobj\ntrailer\n<</Root 1 0 R>>\n%%EOF"
        pdf_file = SimpleUploadedFile("error.pdf", pdf_content, content_type="application/pdf")
        
        # Call the strategy create method
        result = self.strategy.create(self.guru_type, pdf_file)
        
        # Verify the result
        self.assertEqual(result['type'], 'PDF')
        self.assertEqual(result['file'], 'error.pdf')
        self.assertEqual(result['status'], 'error')
        self.assertEqual(result['message'], 'Test error')
    
    def test_create_pdf_private(self):
        """Test creating a private PDF data source"""
        # Create a mock PDF file
        pdf_content = b"%PDF-1.4\n1 0 obj\n<</Type/Catalog/Pages 2 0 R>>\nendobj\n2 0 obj\n<</Type/Pages/Count 1>>\nendobj\ntrailer\n<</Root 1 0 R>>\n%%EOF"
        pdf_file = SimpleUploadedFile("private.pdf", pdf_content, content_type="application/pdf")
        
        # Call the strategy create method with private=True
        result = self.strategy.create(self.guru_type, pdf_file, private=True)
        
        # Verify the result
        self.assertEqual(result['status'], 'success')
        
        # Verify the data source was created with private=True
        data_source = DataSource.objects.get(id=result['id'])
        self.assertTrue(data_source.private)


class YouTubeStrategyTest(StrategyTestCase):
    """Tests for YouTubeStrategy class"""

    def setUp(self):
        super().setUp()
        self.strategy = YouTubeStrategy()
        self.youtube_url = "https://www.youtube.com/watch?v=test123"
    
    def test_create_youtube_success(self):
        """Test creating a new YouTube data source successfully"""
        # Call the strategy create method
        result = self.strategy.create(self.guru_type, self.youtube_url)
        
        # Verify the result
        self.assertEqual(result['type'], 'YouTube')
        self.assertEqual(result['url'], self.youtube_url)
        self.assertEqual(result['status'], 'success')
        self.assertTrue('id' in result)
        
        # Verify the data source was created in the database
        data_source = DataSource.objects.get(id=result['id'])
        self.assertEqual(data_source.type, DataSource.Type.YOUTUBE)
        self.assertEqual(data_source.guru_type, self.guru_type)
        self.assertEqual(data_source.url, self.youtube_url)
    
    @patch('core.models.DataSource.objects.create')
    def test_create_youtube_exists(self, mock_create):
        """Test creating a YouTube data source that already exists"""
        # Make the create method raise DataSourceExists
        existing_data = {'id': 123, 'title': 'Existing YouTube Video'}
        mock_create.side_effect = DataSourceExists(existing_data)
        
        # Call the strategy create method
        result = self.strategy.create(self.guru_type, self.youtube_url)
        
        # Verify the result
        self.assertEqual(result['type'], 'YouTube')
        self.assertEqual(result['url'], self.youtube_url)
        self.assertEqual(result['status'], 'exists')
        self.assertEqual(result['id'], 123)
        self.assertEqual(result['title'], 'Existing YouTube Video')
    
    @patch('core.models.DataSource.objects.create')
    def test_create_youtube_error(self, mock_create):
        """Test creating a YouTube data source with an error"""
        # Make the create method raise an exception
        mock_create.side_effect = Exception("Test error")
        
        # Call the strategy create method
        result = self.strategy.create(self.guru_type, self.youtube_url)
        
        # Verify the result
        self.assertEqual(result['type'], 'YouTube')
        self.assertEqual(result['url'], self.youtube_url)
        self.assertEqual(result['status'], 'error')
        self.assertEqual(result['message'], 'Test error')


class WebsiteStrategyTest(StrategyTestCase):
    """Tests for WebsiteStrategy class"""

    def setUp(self):
        super().setUp()
        self.strategy = WebsiteStrategy()
        self.website_url = "https://example.com/page"
    
    def test_create_website_success(self):
        """Test creating a new Website data source successfully"""
        # Call the strategy create method
        result = self.strategy.create(self.guru_type, self.website_url)
        
        # Verify the result
        self.assertEqual(result['type'], 'Website')
        self.assertEqual(result['url'], self.website_url)
        self.assertEqual(result['status'], 'success')
        self.assertTrue('id' in result)
        
        # Verify the data source was created in the database
        data_source = DataSource.objects.get(id=result['id'])
        self.assertEqual(data_source.type, DataSource.Type.WEBSITE)
        self.assertEqual(data_source.guru_type, self.guru_type)
        self.assertEqual(data_source.url, self.website_url)
    
    @patch('core.models.DataSource.objects.create')
    def test_create_website_exists(self, mock_create):
        """Test creating a Website data source that already exists"""
        # Make the create method raise DataSourceExists
        existing_data = {'id': 123, 'title': 'Existing Website'}
        mock_create.side_effect = DataSourceExists(existing_data)
        
        # Call the strategy create method
        result = self.strategy.create(self.guru_type, self.website_url)
        
        # Verify the result
        self.assertEqual(result['type'], 'Website')
        self.assertEqual(result['url'], self.website_url)
        self.assertEqual(result['status'], 'exists')
        self.assertEqual(result['id'], 123)
        self.assertEqual(result['title'], 'Existing Website')
    
    @patch('core.models.DataSource.objects.create')
    def test_create_website_error(self, mock_create):
        """Test creating a Website data source with an error"""
        # Make the create method raise an exception
        mock_create.side_effect = Exception("Test error")
        
        # Call the strategy create method
        result = self.strategy.create(self.guru_type, self.website_url)
        
        # Verify the result
        self.assertEqual(result['type'], 'Website')
        self.assertEqual(result['url'], self.website_url)
        self.assertEqual(result['status'], 'error')
        self.assertEqual(result['message'], 'Test error')


class JiraStrategyTest(StrategyTestCase):
    """Tests for JiraStrategy class"""

    def setUp(self):
        super().setUp()
        self.strategy = JiraStrategy()
        self.jira_url = "https://test-jira.atlassian.net/browse/TEST-123"
    
    def test_create_jira_success(self):
        """Test creating a new Jira data source successfully"""
        # Call the strategy create method
        result = self.strategy.create(self.guru_type, self.jira_url)
        
        # Verify the result
        self.assertEqual(result['type'], 'Jira')
        self.assertEqual(result['url'], self.jira_url)
        self.assertEqual(result['status'], 'success')
        self.assertTrue('id' in result)
        
        # Verify the data source was created in the database
        data_source = DataSource.objects.get(id=result['id'])
        self.assertEqual(data_source.type, DataSource.Type.JIRA)
        self.assertEqual(data_source.guru_type, self.guru_type)
        self.assertEqual(data_source.url, self.jira_url)
    
    @patch('core.models.DataSource.objects.create')
    def test_create_jira_exists(self, mock_create):
        """Test creating a Jira data source that already exists"""
        # Make the create method raise DataSourceExists
        existing_data = {'id': 123, 'title': 'Existing Jira Issue'}
        mock_create.side_effect = DataSourceExists(existing_data)
        
        # Call the strategy create method
        result = self.strategy.create(self.guru_type, self.jira_url)
        
        # Verify the result
        self.assertEqual(result['type'], 'Jira')
        self.assertEqual(result['url'], self.jira_url)
        self.assertEqual(result['status'], 'exists')
        self.assertEqual(result['id'], 123)
        self.assertEqual(result['title'], 'Existing Jira Issue')
    
    @patch('core.models.DataSource.objects.create')
    def test_create_jira_error(self, mock_create):
        """Test creating a Jira data source with an error"""
        # Make the create method raise an exception
        mock_create.side_effect = Exception("Test error")
        
        # Call the strategy create method
        result = self.strategy.create(self.guru_type, self.jira_url)
        
        # Verify the result
        self.assertEqual(result['type'], 'Jira')
        self.assertEqual(result['url'], self.jira_url)
        self.assertEqual(result['status'], 'error')
        self.assertEqual(result['message'], 'Test error')


class ZendeskStrategyTest(StrategyTestCase):
    """Tests for ZendeskStrategy class"""

    def setUp(self):
        super().setUp()
        self.strategy = ZendeskStrategy()
        self.zendesk_url = "https://test-support.zendesk.com/agent/tickets/123"
    
    def test_create_zendesk_success(self):
        """Test creating a new Zendesk data source successfully"""
        # Call the strategy create method
        result = self.strategy.create(self.guru_type, self.zendesk_url)
        
        # Verify the result
        self.assertEqual(result['type'], 'Zendesk')
        self.assertEqual(result['url'], self.zendesk_url)
        self.assertEqual(result['status'], 'success')
        self.assertTrue('id' in result)
        
        # Verify the data source was created in the database
        data_source = DataSource.objects.get(id=result['id'])
        self.assertEqual(data_source.type, DataSource.Type.ZENDESK)
        self.assertEqual(data_source.guru_type, self.guru_type)
        self.assertEqual(data_source.url, self.zendesk_url)
    
    @patch('core.models.DataSource.objects.create')
    def test_create_zendesk_exists(self, mock_create):
        """Test creating a Zendesk data source that already exists"""
        # Make the create method raise DataSourceExists
        existing_data = {'id': 123, 'title': 'Existing Zendesk Ticket'}
        mock_create.side_effect = DataSourceExists(existing_data)
        
        # Call the strategy create method
        result = self.strategy.create(self.guru_type, self.zendesk_url)
        
        # Verify the result
        self.assertEqual(result['type'], 'Zendesk')
        self.assertEqual(result['url'], self.zendesk_url)
        self.assertEqual(result['status'], 'exists')
        self.assertEqual(result['id'], 123)
        self.assertEqual(result['title'], 'Existing Zendesk Ticket')
    
    @patch('core.models.DataSource.objects.create')
    def test_create_zendesk_error(self, mock_create):
        """Test creating a Zendesk data source with an error"""
        # Make the create method raise an exception
        mock_create.side_effect = Exception("Test error")
        
        # Call the strategy create method
        result = self.strategy.create(self.guru_type, self.zendesk_url)
        
        # Verify the result
        self.assertEqual(result['type'], 'Zendesk')
        self.assertEqual(result['url'], self.zendesk_url)
        self.assertEqual(result['status'], 'error')
        self.assertEqual(result['message'], 'Test error')


class ConfluenceStrategyTest(StrategyTestCase):
    """Tests for ConfluenceStrategy class"""

    def setUp(self):
        super().setUp()
        self.strategy = ConfluenceStrategy()
        self.confluence_url = "https://test.atlassian.net/wiki/spaces/TEST/pages/123456/Test+Page"
    
    def test_create_confluence_success(self):
        """Test creating a new Confluence data source successfully"""
        # Call the strategy create method
        result = self.strategy.create(self.guru_type, self.confluence_url)
        
        # Verify the result
        self.assertEqual(result['type'], 'Confluence')
        self.assertEqual(result['url'], self.confluence_url)
        self.assertEqual(result['status'], 'success')
        self.assertTrue('id' in result)
        
        # Verify the data source was created in the database
        data_source = DataSource.objects.get(id=result['id'])
        self.assertEqual(data_source.type, DataSource.Type.CONFLUENCE)
        self.assertEqual(data_source.guru_type, self.guru_type)
        self.assertEqual(data_source.url, self.confluence_url)
    
    @patch('core.models.DataSource.objects.create')
    def test_create_confluence_exists(self, mock_create):
        """Test creating a Confluence data source that already exists"""
        # Make the create method raise DataSourceExists
        existing_data = {'id': 123, 'title': 'Existing Confluence Page'}
        mock_create.side_effect = DataSourceExists(existing_data)
        
        # Call the strategy create method
        result = self.strategy.create(self.guru_type, self.confluence_url)
        
        # Verify the result
        self.assertEqual(result['type'], 'Confluence')
        self.assertEqual(result['url'], self.confluence_url)
        self.assertEqual(result['status'], 'exists')
        self.assertEqual(result['id'], 123)
        self.assertEqual(result['title'], 'Existing Confluence Page')
    
    @patch('core.models.DataSource.objects.create')
    def test_create_confluence_error(self, mock_create):
        """Test creating a Confluence data source with an error"""
        # Make the create method raise an exception
        mock_create.side_effect = Exception("Test error")
        
        # Call the strategy create method
        result = self.strategy.create(self.guru_type, self.confluence_url)
        
        # Verify the result
        self.assertEqual(result['type'], 'Confluence')
        self.assertEqual(result['url'], self.confluence_url)
        self.assertEqual(result['status'], 'error')
        self.assertEqual(result['message'], 'Test error')


class CrawlServiceTestCase(TestCase):
    """Tests for CrawlService"""
    def setUp(self):
        # Initialize common test data
        get_default_settings()
        self.guru_type = GuruType.objects.create(
            slug="test-guru", 
            name="Test Guru", 
            custom=True, 
            active=True
        )
        self.user = User.objects.create_user(
            name="Test User",
            email="test@example.com",
            password="testpassword"
        )
        self.test_url = "https://example.com"
    
    @patch('core.data_sources.get_guru_type_object_by_maintainer')
    @patch('core.tasks.crawl_website')
    def test_start_crawl_success(self, mock_crawl_website, mock_get_guru_type):
        """Test starting a crawl successfully"""
        # Set up mocks
        mock_get_guru_type.return_value = self.guru_type
        
        # Call function under test
        response, status = CrawlService.start_crawl("test-guru", self.user, self.test_url)
        
        # Verify response
        self.assertEqual(status, 200)
        self.assertTrue('id' in response)
        
        # Verify that the crawl state was created
        crawl_state = CrawlState.objects.get(id=response['id'])
        self.assertEqual(crawl_state.url, self.test_url)
        self.assertEqual(crawl_state.status, CrawlState.Status.RUNNING)
        self.assertEqual(crawl_state.guru_type, self.guru_type)
        self.assertEqual(crawl_state.user, self.user)
        
        # Verify that the crawl_website task was called
        mock_crawl_website.delay.assert_called_once()
        
        # Get the arguments passed to crawl_website
        args = mock_crawl_website.delay.call_args[0]
        self.assertEqual(args[0], self.test_url)
        self.assertEqual(args[1], crawl_state.id)
    
    def test_start_crawl_invalid_url(self):
        """Test starting a crawl with an invalid URL"""
        # Call function under test with invalid URL
        response, status = CrawlService.start_crawl("test-guru", self.user, "not-a-valid-url")
        
        # Verify response indicates error
        self.assertEqual(status, 400)
        self.assertIn('Invalid URL format', response['msg'])
        
        # Verify no crawl state was created
        self.assertEqual(CrawlState.objects.count(), 0)
    
    @patch('core.data_sources.get_guru_type_object_by_maintainer')
    def test_start_crawl_existing_crawl(self, mock_get_guru_type):
        """Test starting a crawl when one is already running for the guru type"""
        # Set up mocks
        mock_get_guru_type.return_value = self.guru_type
        
        # Create an existing running crawl for the guru type
        CrawlState.objects.create(
            url="https://example.com/existing",
            status=CrawlState.Status.RUNNING,
            guru_type=self.guru_type,
            user=self.user
        )
        
        # Call function under test
        response, status = CrawlService.start_crawl("test-guru", self.user, self.test_url)
        
        # Verify response indicates error
        self.assertEqual(status, 400)
        self.assertIn('A crawl is already running', response['msg'])
        
        # Verify only the original crawl state exists
        self.assertEqual(CrawlState.objects.count(), 1)
    
    @patch('core.data_sources.get_guru_type_object_by_maintainer')
    def test_start_crawl_guru_not_found(self, mock_get_guru_type):
        """Test starting a crawl when guru type is not found"""
        # Set up mocks to return None
        mock_get_guru_type.return_value = None
        
        # Call function under test
        with self.assertRaises(NotFoundError) as context:
            CrawlService.start_crawl("nonexistent", self.user, self.test_url)
        
        # Verify error message
        self.assertIn('Guru type nonexistent not found', str(context.exception))
        
        # Verify no crawl state was created
        self.assertEqual(CrawlState.objects.count(), 0)
    
    def test_stop_crawl_success(self):
        """Test stopping a crawl successfully"""
        # Create a crawl state to stop
        crawl_state = CrawlState.objects.create(
            url=self.test_url,
            status=CrawlState.Status.RUNNING,
            guru_type=self.guru_type,
            user=self.user
        )
        
        # Call function under test
        response, status = CrawlService.stop_crawl(self.user, crawl_state.id)
        
        # Verify response
        self.assertEqual(status, 200)
        self.assertEqual(response['id'], crawl_state.id)
        
        # Verify crawl state was updated
        crawl_state.refresh_from_db()
        self.assertEqual(crawl_state.status, CrawlState.Status.STOPPED)
        self.assertIsNotNone(crawl_state.end_time)
    
    def test_stop_crawl_not_found(self):
        """Test stopping a crawl that doesn't exist"""
        # Call function under test with a non-existent ID
        response, status = CrawlService.stop_crawl(self.user, 999)
        
        # Verify response indicates error
        self.assertEqual(status, 404)
        self.assertIn('Crawl not found', response['msg'])
    
    def test_get_crawl_status_success(self):
        """Test getting crawl status successfully"""
        # Create a crawl state to query
        crawl_state = CrawlState.objects.create(
            url=self.test_url,
            status=CrawlState.Status.RUNNING,
            guru_type=self.guru_type,
            user=self.user,
            discovered_urls=["https://example.com/page1", "https://example.com/page2"]
        )
        
        # Call function under test
        response, status = CrawlService.get_crawl_status(self.user, crawl_state.id)
        
        # Verify response
        self.assertEqual(status, 200)
        self.assertEqual(response['id'], crawl_state.id)
        self.assertEqual(response['status'], 'RUNNING')
        self.assertEqual(len(response['discovered_urls']), 2)
        
        # Verify last_polled_at was updated
        crawl_state.refresh_from_db()
        self.assertIsNotNone(crawl_state.last_polled_at)
    
    def test_get_crawl_status_with_error(self):
        """Test getting crawl status with error message"""
        # Create a crawl state with an error
        crawl_state = CrawlState.objects.create(
            url=self.test_url,
            status=CrawlState.Status.FAILED,
            guru_type=self.guru_type,
            user=self.user,
            error_message="Test error message"
        )
        
        # Call function under test
        response, status = CrawlService.get_crawl_status(self.user, crawl_state.id)
        
        # Verify response
        self.assertEqual(status, 200)
        self.assertEqual(response['id'], crawl_state.id)
        self.assertEqual(response['status'], 'FAILED')
        self.assertEqual(response['error_message'], "Test error message")
    
    def test_get_crawl_status_not_found(self):
        """Test getting status of a crawl that doesn't exist"""
        # Call function under test with a non-existent ID
        response, status = CrawlService.get_crawl_status(self.user, 999)
        
        # Verify response indicates error
        self.assertEqual(status, 404)
        self.assertIn('Crawl not found', response['msg'])


class YouTubeServiceTestCase(TestCase):
    """Tests for YouTubeService"""
    def setUp(self):
        # Initialize common test data
        get_default_settings()
        self.test_playlist_url = "https://www.youtube.com/watch?v=test123&list=PLtest"
        self.test_channel_url = "https://www.youtube.com/@testchannel"
    
    def _setup_cloud_env(self):
        """Helper to setup cloud environment for tests"""
        return {'msg': 'Youtube API key is not checked on cloud.'}, 200
    
    def _setup_selfhosted_env(self, is_valid=True):
        """Helper to setup selfhosted environment for tests"""
        if is_valid:
            return {'msg': 'YouTube API key is valid'}, 200
        else:
            return {'msg': 'YouTube API key is invalid'}, 400
    
    @patch('core.data_sources.get_default_settings')
    def test_verify_api_key_valid_cloud(self, mock_get_default_settings):
        """Test verifying a valid YouTube API key in cloud environment"""
        # Set up mock settings
        mock_settings = MagicMock()
        mock_settings.youtube_api_key = "valid_key"
        mock_settings.is_youtube_key_valid = True
        mock_get_default_settings.return_value = mock_settings
        
        # Call function under test
        response, status = YouTubeService.verify_api_key()
        
        # Verify response
        self.assertEqual(status, 200)
        self.assertIn('Youtube API key is not checked on cloud.', response['msg'])
    
    @patch('core.data_sources.get_default_settings')
    @override_settings(ENV="selfhosted")
    def test_verify_api_key_valid_selfhosted(self, mock_get_default_settings):
        """Test verifying a valid YouTube API key in selfhosted environment"""
        # Set up mock settings
        mock_settings = MagicMock()
        mock_settings.youtube_api_key = "valid_key"
        mock_settings.is_youtube_key_valid = True
        mock_get_default_settings.return_value = mock_settings
        
        # Call function under test
        response, status = YouTubeService.verify_api_key()
        
        # Verify response
        self.assertEqual(status, 200)
        self.assertIn('YouTube API key is valid', response['msg'])
    
    @patch('core.data_sources.get_default_settings')
    def test_verify_api_key_invalid_cloud(self, mock_get_default_settings):
        """Test verifying an invalid YouTube API key in cloud environment"""
        # Set up mock settings
        mock_settings = MagicMock()
        mock_settings.youtube_api_key = "invalid_key"
        mock_settings.is_youtube_key_valid = False
        mock_get_default_settings.return_value = mock_settings
        
        # Call function under test
        response, status = YouTubeService.verify_api_key()
        
        # Verify response
        self.assertEqual(status, 200)
        self.assertIn('Youtube API key is not checked on cloud.', response['msg'])
    
    @patch('core.data_sources.get_default_settings')
    @override_settings(ENV="selfhosted")
    def test_verify_api_key_invalid_selfhosted(self, mock_get_default_settings):
        """Test verifying an invalid YouTube API key in selfhosted environment"""
        # Set up mock settings
        mock_settings = MagicMock()
        mock_settings.youtube_api_key = "invalid_key"
        mock_settings.is_youtube_key_valid = False
        mock_get_default_settings.return_value = mock_settings
        
        # Call function under test
        response, status = YouTubeService.verify_api_key()
        
        # Verify response
        self.assertEqual(status, 400)
        self.assertIn('YouTube API key is invalid', response['msg'])
    
    @patch('core.data_sources.get_default_settings')
    def test_verify_api_key_missing(self, mock_get_default_settings):
        """Test verifying when YouTube API key is missing"""
        # Set up mock settings
        mock_settings = MagicMock()
        mock_settings.youtube_api_key = None
        mock_get_default_settings.return_value = mock_settings
        
        # Call function under test
        response, status = YouTubeService.verify_api_key()
        
        # Verify response
        self.assertEqual(status, 400)
        self.assertIn('Youtube API key is not checked on cloud.', response['msg'])

    @patch('core.data_sources.get_default_settings')
    @override_settings(ENV="selfhosted")
    def test_verify_api_key_missing(self, mock_get_default_settings):
        """Test verifying when YouTube API key is missing"""
        # Set up mock settings
        mock_settings = MagicMock()
        mock_settings.youtube_api_key = None
        mock_get_default_settings.return_value = mock_settings
        
        # Call function under test
        response, status = YouTubeService.verify_api_key()
        
        # Verify response
        self.assertEqual(status, 400)
        self.assertIn('A YouTube API key is required', response['msg'])        
    
    @patch('core.data_sources.YouTubeService.verify_api_key')
    @patch('core.data_sources.YouTubeRequester')
    def test_fetch_playlist_success(self, mock_youtube_requester_class, mock_verify_api_key):
        """Test fetching a YouTube playlist successfully"""
        # Set up mocks
        mock_verify_api_key.return_value = ({'msg': 'YouTube API key is valid'}, 200)
        
        mock_requester = MagicMock()
        mock_youtube_requester_class.return_value = mock_requester
        
        # Mock playlist videos
        mock_requester.fetch_all_playlist_videos.return_value = [
            {
                'contentDetails': {'videoId': 'video1'},
                'snippet': {
                    'title': 'Video 1',
                    'description': 'Description 1',
                    'publishedAt': '2023-01-01T00:00:00Z',
                    'thumbnails': {'high': {'url': 'https://example.com/thumb1.jpg'}}
                }
            },
            {
                'contentDetails': {'videoId': 'video2'},
                'snippet': {
                    'title': 'Video 2',
                    'description': 'Description 2',
                    'publishedAt': '2023-01-02T00:00:00Z',
                    'thumbnails': {'high': {'url': 'https://example.com/thumb2.jpg'}}
                }
            }
        ]
        
        # Call function under test
        response, status = YouTubeService.fetch_playlist(self.test_playlist_url)
        
        # Verify response
        self.assertEqual(status, 200)
        self.assertEqual(response['playlist_id'], 'PLtest')
        self.assertEqual(response['video_count'], 2)
        self.assertEqual(len(response['videos']), 2)
        self.assertEqual(response['videos'][0], 'https://www.youtube.com/watch?v=video1')
        self.assertEqual(response['videos'][1], 'https://www.youtube.com/watch?v=video2')
        
        # Verify requester was called correctly
        mock_requester.fetch_all_playlist_videos.assert_called_once_with('PLtest')
    
    @patch('core.data_sources.YouTubeService.verify_api_key')
    def test_fetch_playlist_invalid_api_key(self, mock_verify_api_key):
        """Test fetching a playlist with invalid API key"""
        # Set up mocks
        mock_verify_api_key.return_value = ({'msg': 'YouTube API key is invalid'}, 400)
        
        # Call function under test
        response, status = YouTubeService.fetch_playlist(self.test_playlist_url)
        
        # Verify response
        self.assertEqual(status, 400)
        self.assertIn('YouTube API key is invalid', response['msg'])
    
    def test_fetch_playlist_invalid_url(self):
        """Test fetching a playlist with invalid URL"""
        # Call function under test with invalid URL
        response, status = YouTubeService.fetch_playlist("https://www.youtube.com/watch?v=test123")
        
        # Verify response
        self.assertEqual(status, 400)
        self.assertIn('Invalid YouTube playlist URL', response['msg'])
    
    @patch('core.data_sources.YouTubeService.verify_api_key')
    @patch('core.data_sources.YouTubeRequester')
    def test_fetch_channel_by_username_success(self, mock_youtube_requester_class, mock_verify_api_key):
        """Test fetching a YouTube channel by username successfully"""
        # Set up mocks
        mock_verify_api_key.return_value = ({'msg': 'YouTube API key is valid'}, 200)
        
        mock_requester = MagicMock()
        mock_youtube_requester_class.return_value = mock_requester
        
        # Mock channel videos
        mock_requester.fetch_all_channel_videos.return_value = [
            {
                'contentDetails': {'videoId': 'video1'},
                'snippet': {
                    'title': 'Video 1',
                    'description': 'Description 1',
                    'publishedAt': '2023-01-01T00:00:00Z',
                    'thumbnails': {'high': {'url': 'https://example.com/thumb1.jpg'}}
                }
            },
            {
                'contentDetails': {'videoId': 'video2'},
                'snippet': {
                    'title': 'Video 2',
                    'description': 'Description 2',
                    'publishedAt': '2023-01-02T00:00:00Z',
                    'thumbnails': {'high': {'url': 'https://example.com/thumb2.jpg'}}
                }
            }
        ]
        
        # Call function under test
        response, status = YouTubeService.fetch_channel(self.test_channel_url)
        
        # Verify response
        self.assertEqual(status, 200)
        self.assertEqual(response['channel_identifier'], 'testchannel')
        self.assertEqual(response['identifier_type'], 'username')
        self.assertEqual(response['video_count'], 2)
        self.assertEqual(len(response['videos']), 2)
        self.assertEqual(response['videos'][0], 'https://www.youtube.com/watch?v=video1')
        self.assertEqual(response['videos'][1], 'https://www.youtube.com/watch?v=video2')
        
        # Verify requester was called correctly
        mock_requester.fetch_all_channel_videos.assert_called_once_with(username='testchannel', channel_id=None)
    
    @patch('core.data_sources.YouTubeService.verify_api_key')
    @patch('core.data_sources.YouTubeRequester')
    def test_fetch_channel_by_id_success(self, mock_youtube_requester_class, mock_verify_api_key):
        """Test fetching a YouTube channel by ID successfully"""
        # Set up mocks
        mock_verify_api_key.return_value = ({'msg': 'YouTube API key is valid'}, 200)
        
        mock_requester = MagicMock()
        mock_youtube_requester_class.return_value = mock_requester
        
        # Mock channel videos
        mock_requester.fetch_all_channel_videos.return_value = [
            {'contentDetails': {'videoId': 'video1'}},
            {'contentDetails': {'videoId': 'video2'}}
        ]
        
        # Call function under test with channel ID URL
        response, status = YouTubeService.fetch_channel("https://www.youtube.com/channel/UC123456789")
        
        # Verify response
        self.assertEqual(status, 200)
        self.assertEqual(response['channel_identifier'], 'UC123456789')
        self.assertEqual(response['identifier_type'], 'channel_id')
        
        # Verify requester was called correctly
        mock_requester.fetch_all_channel_videos.assert_called_once_with(username=None, channel_id='UC123456789')
    
    def test_fetch_channel_invalid_url(self):
        """Test fetching a channel with invalid URL"""
        # Call function under test with invalid URL
        response, status = YouTubeService.fetch_channel("https://www.youtube.com/watch?v=test123")
        
        # Verify response
        self.assertEqual(status, 400)
        self.assertIn('Invalid YouTube channel URL', response['msg'])


class CrawlerTestCase(TestCase):
    """Tests for crawler functionality"""
    def setUp(self):
        # Initialize common test data
        get_default_settings()
        self.guru_type = GuruType.objects.create(
            slug="test-guru", 
            name="Test Guru", 
            custom=True, 
            active=True
        )
        self.user = User.objects.create_user(
            name="Test User",
            email="test@example.com",
            password="testpassword"
        )
        self.test_url = "https://example.com"
        
        # Create a crawl state
        self.crawl_state = CrawlState.objects.create(
            url=self.test_url,
            status=CrawlState.Status.RUNNING,
            guru_type=self.guru_type,
            user=self.user
        )
    
    @patch('core.data_sources.Process')
    def test_get_internal_links(self, mock_process_class):
        """Test get_internal_links spawns a crawler process"""
        # Set up mock Process
        mock_process = MagicMock()
        mock_process_class.return_value = mock_process
        
        # Call function under test
        get_internal_links(self.test_url, self.crawl_state.id, 100, "en")
        
        # Verify Process was created and started
        mock_process_class.assert_called_once_with(
            target=run_spider_process,
            args=(self.test_url, self.crawl_state.id, 100, "en")
        )
        mock_process.start.assert_called_once()
    
    @patch('core.data_sources.Process')
    def test_get_internal_links_error(self, mock_process_class):
        """Test get_internal_links handles errors"""
        # Set up mock Process to raise an exception
        mock_process_class.side_effect = Exception("Test error")
        
        # Call function under test
        with self.assertRaises(Exception):
            get_internal_links(self.test_url, self.crawl_state.id, 100, "en")
        
        # Verify crawl state was updated with failure
        self.crawl_state.refresh_from_db()
        self.assertEqual(self.crawl_state.status, CrawlState.Status.FAILED)
        self.assertIn("Test error", self.crawl_state.error_message)
        self.assertIsNotNone(self.crawl_state.end_time)
    
    @patch('core.data_sources.CrawlerProcess')
    def test_run_spider_process(self, mock_crawler_process_class):
        """Test run_spider_process starts the crawler with correct settings"""
        # Set up mocks
        mock_crawler_process = MagicMock()
        mock_crawler_process_class.return_value = mock_crawler_process
        
        # Call function under test
        run_spider_process(self.test_url, self.crawl_state.id, 100, "en")
        
        # Verify crawler process was created with expected settings
        # First get the settings argument
        settings_arg = mock_crawler_process_class.call_args[0][0]
        self.assertEqual(settings_arg['LOG_ENABLED'], False)
        self.assertEqual(settings_arg['ROBOTSTXT_OBEY'], False)
        
        # Verify crawl was started with correct parameters
        mock_crawler_process.crawl.assert_called_once_with(
            InternalLinkSpider,
            start_urls=[self.test_url],
            original_url=self.test_url,
            crawl_state_id=self.crawl_state.id,
            link_limit=100,
            language_code="en"
        )
        mock_crawler_process.start.assert_called_once()


if __name__ == '__main__':
    unittest.main()