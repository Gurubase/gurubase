from django.test import TestCase
from unittest.mock import patch, MagicMock

from core.models import GuruType, DataSource
from core.tasks import scrape_main_content
from core.utils import get_default_settings


class ScrapeMainContentTaskTests(TestCase):
    def setUp(self):
        """
        Set up test environment with necessary models and data before each test.
        """
        # Initialize default settings
        get_default_settings()
        
        # Create a test guru type
        self.guru_type = GuruType.objects.create(
            slug="test-guru", 
            name="Test Guru", 
            custom=True, 
            active=True,
            milvus_collection_name="test_guru_collection"
        )
        
        # Create website data sources for testing
        self.website_successful = DataSource.objects.create(
            guru_type=self.guru_type,
            title="Website Test Source - Success",
            type=DataSource.Type.WEBSITE,
            url="https://example.com/page1",
            status=DataSource.Status.SUCCESS,
            content="<html><body><header>Header</header><main>Main content</main><footer>Footer</footer></body></html>",
            content_rewritten=False
        )
        
        self.website_already_rewritten = DataSource.objects.create(
            guru_type=self.guru_type,
            title="Website Test Source - Already Rewritten",
            type=DataSource.Type.WEBSITE,
            url="https://example.com/page2",
            status=DataSource.Status.SUCCESS,
            content="<html><body><main>Already extracted content</main></body></html>",
            content_rewritten=True,
            original_content="<html><body><header>Header</header><main>Already extracted content</main><footer>Footer</footer></body></html>"
        )
        
        self.website_not_success = DataSource.objects.create(
            guru_type=self.guru_type,
            title="Website Test Source - Not Success",
            type=DataSource.Type.WEBSITE,
            url="https://example.com/page3",
            status=DataSource.Status.FAIL,
            content="<html><body><header>Header</header><main>Main content</main><footer>Footer</footer></body></html>",
            content_rewritten=False
        )
        
        self.website_no_content = DataSource.objects.create(
            guru_type=self.guru_type,
            title="Website Test Source - No Content",
            type=DataSource.Type.WEBSITE,
            url="https://example.com/page4",
            status=DataSource.Status.SUCCESS,
            content=None,
            content_rewritten=False
        )
    
    @patch('core.models.DataSource.scrape_main_content')
    def test_scrape_main_content_calls_method_on_each_datasource(self, mock_scrape_method):
        """
        Test that the scrape_main_content task calls the scrape_main_content method
        on each DataSource object in the provided list.
        """
        # Call the task function with a list of data source IDs
        data_source_ids = [
            self.website_successful.id,
            self.website_already_rewritten.id,
            self.website_not_success.id,
            self.website_no_content.id
        ]
        
        scrape_main_content(data_source_ids)
        
        # Verify the method was called on each data source
        self.assertEqual(mock_scrape_method.call_count, 4)
    
    @patch('core.requester.GeminiRequester')
    @patch('core.models.transaction.atomic')
    @patch('core.models.DataSource.delete_from_milvus')
    @patch('core.models.DataSource.write_to_milvus')
    def test_datasource_scrape_main_content_successful(
        self,
        mock_write_to_milvus,
        mock_delete_from_milvus,
        mock_atomic,
        mock_gemini_requester
    ):
        """
        Test successful scraping of main content from a data source.
        This should:
        1. Extract main content using GeminiRequester
        2. Update the data source with new content
        3. Mark the content as rewritten
        4. Update Milvus by deleting and rewriting
        """
        # Set up the mock GeminiRequester instance
        mock_requester_instance = MagicMock()
        old_content = self.website_successful.content
        
        mock_gemini_requester.return_value = mock_requester_instance
        mock_requester_instance.scrape_main_content.return_value = "Extracted main content"
        
        # Call the task function with just the successful data source
        scrape_main_content([self.website_successful.id])
        
        # Refresh data source from database
        self.website_successful.refresh_from_db()

        # Verify GeminiRequester was called with the correct content
        mock_requester_instance.scrape_main_content.assert_called_once_with(
            old_content
        )
        
        # Verify the content was updated
        self.assertEqual(self.website_successful.content, "Extracted main content")
        
        # Verify content_rewritten was set to True
        self.assertTrue(self.website_successful.content_rewritten)
        
        # Verify original_content was stored
        self.assertEqual(
            self.website_successful.original_content,
            "<html><body><header>Header</header><main>Main content</main><footer>Footer</footer></body></html>"
        )
        
        # Verify Milvus was updated
        mock_delete_from_milvus.assert_called_once()
        mock_write_to_milvus.assert_called_once()
        mock_atomic.assert_called_once()
    
    @patch('core.requester.GeminiRequester')
    @patch('core.models.transaction.atomic')
    @patch('core.models.DataSource.delete_from_milvus')
    @patch('core.models.DataSource.write_to_milvus')
    def test_datasource_scrape_main_content_skip_already_rewritten(
        self,
        mock_write_to_milvus,
        mock_delete_from_milvus,
        mock_atomic,
        mock_gemini_requester
    ):
        """
        Test that the task skips data sources that are already rewritten.
        """
        # Set up the mock GeminiRequester instance
        mock_requester_instance = MagicMock()
        mock_gemini_requester.return_value = mock_requester_instance
        
        # Call the task function with just the already rewritten data source
        scrape_main_content([self.website_already_rewritten.id])
        
        # Verify GeminiRequester was not called
        mock_requester_instance.scrape_main_content.assert_not_called()
        
        # Verify Milvus was not updated
        mock_delete_from_milvus.assert_not_called()
        mock_write_to_milvus.assert_not_called()
    
    @patch('core.requester.GeminiRequester')
    @patch('core.models.transaction.atomic')
    @patch('core.models.DataSource.delete_from_milvus')
    @patch('core.models.DataSource.write_to_milvus')
    def test_datasource_scrape_main_content_skip_not_success(
        self,
        mock_write_to_milvus,
        mock_delete_from_milvus,
        mock_atomic,
        mock_gemini_requester
    ):
        """
        Test that the task skips data sources that are not in SUCCESS status.
        """
        # Set up the mock GeminiRequester instance
        mock_requester_instance = MagicMock()
        mock_gemini_requester.return_value = mock_requester_instance
        
        # Call the task function with just the not success data source
        scrape_main_content([self.website_not_success.id])
        
        # Verify GeminiRequester was not called
        mock_requester_instance.scrape_main_content.assert_not_called()
        
        # Verify Milvus was not updated
        mock_delete_from_milvus.assert_not_called()
        mock_write_to_milvus.assert_not_called()
    
    @patch('core.requester.GeminiRequester')
    @patch('core.models.transaction.atomic')
    @patch('core.models.DataSource.delete_from_milvus')
    @patch('core.models.DataSource.write_to_milvus')
    def test_datasource_scrape_main_content_skip_no_content(
        self,
        mock_write_to_milvus,
        mock_delete_from_milvus,
        mock_atomic,
        mock_gemini_requester
    ):
        """
        Test that the task skips data sources that have no content.
        """
        # Set up the mock GeminiRequester instance
        mock_requester_instance = MagicMock()
        mock_gemini_requester.return_value = mock_requester_instance
        
        # Call the task function with just the no content data source
        scrape_main_content([self.website_no_content.id])
        
        # Verify GeminiRequester was not called
        mock_requester_instance.scrape_main_content.assert_not_called()
        
        # Verify Milvus was not updated
        mock_delete_from_milvus.assert_not_called()
        mock_write_to_milvus.assert_not_called()
    
    @patch('core.requester.GeminiRequester')
    @patch('core.models.logger.error')
    def test_datasource_scrape_main_content_error_handling(
        self,
        mock_logger_error,
        mock_gemini_requester
    ):
        """
        Test error handling during scraping of main content.
        The error should be logged and not propagated.
        """
        # Set up the mock GeminiRequester instance to raise an exception
        mock_requester_instance = MagicMock()
        mock_gemini_requester.return_value = mock_requester_instance
        mock_requester_instance.scrape_main_content.side_effect = Exception("Test error")
        
        # Call the task function with the successful data source
        scrape_main_content([self.website_successful.id])
        
        # Verify the error was logged
        mock_logger_error.assert_called_once()
        
        # Verify the data source was not updated (content_rewritten should still be False)
        self.website_successful.refresh_from_db()
        self.assertFalse(self.website_successful.content_rewritten)
    
    @patch('core.models.DataSource.objects.filter')
    def test_scrape_main_content_nonexistent_datasources(self, mock_filter):
        """
        Test handling of nonexistent data sources.
        The function should not raise an exception.
        """
        # Set up the mock filter to return an empty queryset
        mock_queryset = MagicMock()
        mock_filter.return_value = mock_queryset
        mock_queryset.__iter__.return_value = []
        
        # Call the task function with nonexistent data source IDs
        scrape_main_content([999, 1000])
        
        # Verify filter was called with the correct IDs
        mock_filter.assert_called_once_with(id__in=[999, 1000])
