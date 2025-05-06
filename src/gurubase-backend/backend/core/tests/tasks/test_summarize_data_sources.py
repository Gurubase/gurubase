from django.test import TestCase
from unittest.mock import patch, MagicMock, call
from django.conf import settings

from core.utils import get_default_settings
from core.tasks import summarize_data_sources, summarize_data_sources_for_guru_type
from core.models import GuruType, DataSource, Summarization


class SummarizeDataSourcesTaskTests(TestCase):
    def setUp(self):
        """Set up test fixtures for all tests."""
        # Create GuruType test objects
        get_default_settings()
        self.guru_type1 = GuruType.objects.create(
            slug="python",
            name="Python",
            custom=True,
            active=True
        )
        
        self.guru_type2 = GuruType.objects.create(
            slug="javascript",
            name="JavaScript",
            custom=True,
            active=True
        )
    
    @patch('core.tasks.summarize_data_sources_for_guru_type')
    def test_summarize_data_sources_with_specific_slugs(self, mock_summarize):
        """Test summarize_data_sources with specific guru type slugs."""
        # Call the function with specific slugs
        summarize_data_sources(guru_type_slugs=['python', 'javascript'])
        
        # Assert that summarize_data_sources_for_guru_type was called for each slug
        mock_summarize.assert_has_calls([
            call(guru_type_slug='python', guru_type=self.guru_type1),
            call(guru_type_slug='javascript', guru_type=self.guru_type2)
        ])
    
    @patch('core.tasks.summarize_data_sources_for_guru_type')
    def test_summarize_data_sources_with_wildcard(self, mock_summarize):
        """Test summarize_data_sources with wildcard to process all guru types."""
        # Call the function with wildcard
        summarize_data_sources(guru_type_slugs=['*'])
        
        # Assert that summarize_data_sources_for_guru_type was called for all guru types
        # The order of calls depends on the order of GuruType.objects.all()
        mock_summarize.assert_has_calls([
            call(guru_type_slug='python', guru_type=self.guru_type1),
            call(guru_type_slug='javascript', guru_type=self.guru_type2)
        ])
    
    @patch('core.tasks.logger')
    @patch('core.tasks.summarize_data_sources_for_guru_type')
    def test_summarize_data_sources_with_nonexistent_slug(self, mock_summarize, mock_logger):
        """Test handling of nonexistent guru type slugs."""
        # Call the function with nonexistent slug
        summarize_data_sources(guru_type_slugs=['nonexistent'])
        
        # Assert that summarize_data_sources_for_guru_type was not called
        mock_summarize.assert_not_called()
        
        # Assert that error was logged
        mock_logger.error.assert_called_once()


class SummarizeDataSourcesForGuruTypeTaskTests(TestCase):
    def setUp(self):
        """Set up test fixtures for all tests."""
        # Create test guru type
        get_default_settings()
        self.guru_type = GuruType.objects.create(
            slug="python",
            name="Python",
            custom=True,
            active=True
        )
        
        # Create test data sources for different scenarios
        # First batch: need initial summarization
        self.data_source1 = DataSource.objects.create(
            url="https://example.com/python1",
            type=DataSource.Type.WEBSITE,
            status=DataSource.Status.SUCCESS,
            initial_summarizations_created=False,
            final_summarization_created=False,
            guru_type=self.guru_type,
            content='x' * 2000,  # Long enough content to be processed
            title="Python Source 1"
        )
        
        self.data_source2 = DataSource.objects.create(
            url="https://example.com/python2",
            type=DataSource.Type.WEBSITE,
            status=DataSource.Status.SUCCESS,
            initial_summarizations_created=False,
            final_summarization_created=False,
            guru_type=self.guru_type,
            content='x' * 2000,
            title="Python Source 2"
        )
        
        # Second batch: need final summarization
        self.data_source3 = DataSource.objects.create(
            url="https://example.com/python3",
            type=DataSource.Type.WEBSITE,
            status=DataSource.Status.SUCCESS,
            initial_summarizations_created=True,
            final_summarization_created=False,
            guru_type=self.guru_type,
            content='x' * 2000,
            title="Python Source 3"
        )
        
        # Small content data source
        self.small_data_source = DataSource.objects.create(
            url="https://example.com/python-small",
            type=DataSource.Type.WEBSITE,
            status=DataSource.Status.SUCCESS,
            initial_summarizations_created=False,
            final_summarization_created=False,
            guru_type=self.guru_type,
            content="short",  # Less than 1000 chars
            title="Small Python Source"
        )
    
    @patch('core.tasks.create_guru_type_summarization')
    @patch('core.tasks.finalize_data_source_summarizations')
    @patch('core.models.DataSource.create_initial_summarizations')
    def test_summarize_data_sources_for_guru_type_basic_flow(self, mock_create_initial, mock_finalize, mock_create_summary):
        """Test the basic flow of summarize_data_sources_for_guru_type with real data sources."""
        # Call the function
        summarize_data_sources_for_guru_type(guru_type_slug='python', guru_type=self.guru_type)
        
        # Assert that create_initial_summarizations was called
        self.assertEqual(mock_create_initial.call_count, 2)
        
        # Assert that finalize_data_source_summarizations was called for data_source3
        mock_finalize.assert_called_once_with(self.data_source3)
        
        # Assert that create_guru_type_summarization was called
        mock_create_summary.assert_called_once_with(self.guru_type)
    
    @patch('core.tasks.logger')
    @patch('core.tasks.create_guru_type_summarization')
    @patch('core.models.DataSource.create_initial_summarizations')
    def test_summarize_data_sources_for_guru_type_with_error(self, mock_create_initial, mock_create_summary, mock_logger):
        """Test error handling during summarization with real data sources."""
        # Setup error for initial summarization
        mock_create_initial.side_effect = Exception("Test error")
        
        # Call the function
        summarize_data_sources_for_guru_type(guru_type_slug='python', guru_type=self.guru_type)
        
        # Error shouldn't prevent the function from completing
        mock_create_summary.assert_called_once_with(self.guru_type)
    
    @patch('core.tasks.create_guru_type_summarization')
    @patch('core.tasks.finalize_data_source_summarizations')
    @patch('core.models.DataSource.create_initial_summarizations')
    def test_summarize_data_sources_for_guru_type_small_content(self, mock_create_initial, mock_finalize, mock_create_summary):
        """Test handling of data sources with small content using real data sources."""
        # Remove other data sources to focus on the small content one
        DataSource.objects.exclude(id=self.small_data_source.id).delete()
        
        # Call the function
        summarize_data_sources_for_guru_type(guru_type_slug='python', guru_type=self.guru_type)
        
        # Should still process even with small content
        mock_create_initial.assert_not_called()
        
        # Complete the flow
        mock_create_summary.assert_called_once_with(self.guru_type)
