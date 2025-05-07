from django.test import TestCase, override_settings
from unittest.mock import patch, MagicMock
from accounts.models import User
from core.models import GuruType, DataSource, Integration, Settings
from core.tasks import data_source_retrieval
from core.utils import get_default_settings
from core.exceptions import WebsiteContentExtractionThrottleError, GithubRepoSizeLimitError, YouTubeContentExtractionError
from core.requester import FirecrawlScraper # For type checking

class DataSourceRetrievalTaskTests(TestCase):
    def setUp(self):
        # Use override_settings to ensure specific settings are used during tests
        self.settings_override = override_settings(
            ENV='test',
            DATA_SOURCE_FETCH_BATCH_SIZE=10,
            FIRECRAWL_BATCH_SIZE=5,
            DATA_SOURCE_RETRIEVAL_LOCK_DURATION_SECONDS=10,
            WEB_SCRAPER_TOOL='default' # Use default scraper, not firecrawl initially
        )
        self.settings_override.enable()
        get_default_settings() # Re-initialize settings if needed

        self.user = User.objects.create_user(
            name='testuser',
            email='testuser@example.com',
            password='testpassword'
        )

        self.guru_type = GuruType.objects.create(
            slug="test-guru-ds",
            name="Test Guru DS",
            custom=True,
            active=True,
            milvus_collection_name="test_guru_ds_collection",
        )

        self.guru_type.maintainers.add(self.user)
        self.guru_type.save()
        # Create a dummy Milvus collection (mocked interaction later)
        # Normally utils.create_context_collection would be called

    def tearDown(self):
        self.settings_override.disable()

    @patch('core.tasks.get_web_scraper')
    @patch('core.tasks.fetch_data_source_content')
    @patch('core.tasks.get_guru_type_object_without_filters')
    @patch('core.tasks.DataSource.write_to_milvus')
    @patch('core.tasks.redis_client') # Mock redis lock
    @patch('core.tasks.get_default_settings')
    def test_data_source_retrieval_single_website_no_firecrawl(
        self, mock_get_settings, mock_redis, mock_write_to_milvus, mock_get_guru_type, mock_fetch_content, mock_get_scraper
    ):
        """Test retrieval for a single WEBSITE source without Firecrawl batching."""
        # Mock scraper to be non-Firecrawl
        mock_scraper_instance = MagicMock()
        mock_get_scraper.return_value = (mock_scraper_instance, 'default')

        # Mock get_guru_type to return our test guru
        mock_get_guru_type.return_value = self.guru_type

        # Create a data source to process
        ds = DataSource.objects.create(
            guru_type=self.guru_type,
            type=DataSource.Type.WEBSITE,
            status=DataSource.Status.NOT_PROCESSED,
            url="http://example.com/page1"
        )

        # Mock fetch_data_source_content response
        mock_fetched_ds = DataSource(
            id=ds.id,
            guru_type=self.guru_type,
            type=DataSource.Type.WEBSITE,
            status=DataSource.Status.SUCCESS, # Mark as success by fetch
            url="http://example.com/page1",
            title="Example Page 1",
            content="Content of page 1",
            scrape_tool='default'
        )
        # We need to return the *instance* that fetch_data_source_content would modify
        # Side effect allows modifying the passed object or returning a new one
        def fetch_side_effect(integration, data_source, language_code):
            data_source.title = "Example Page 1"
            data_source.content = "Content of page 1"
            data_source.scrape_tool = 'default'
            # Simulate successful fetch modifying the object passed in
            return data_source

        mock_fetch_content.side_effect = fetch_side_effect

        # Call the task for the specific guru type
        data_source_retrieval(guru_type_slug=self.guru_type.slug)

        # Refresh from DB
        ds.refresh_from_db()

        # Assertions
        mock_get_guru_type.assert_called_with(self.guru_type.slug)
        mock_fetch_content.assert_called_once()
        # Check args passed to fetch_data_source_content
        fetch_args, _ = mock_fetch_content.call_args
        self.assertIsNone(fetch_args[0]) # No integration for WEBSITE
        self.assertEqual(fetch_args[1].id, ds.id) # Check DS object
        self.assertEqual(fetch_args[2], self.guru_type.get_language_code()) # Language code

        self.assertEqual(ds.status, DataSource.Status.SUCCESS)
        self.assertEqual(ds.title, "Example Page 1")
        self.assertEqual(ds.content, "Content of page 1")
        self.assertEqual(ds.scrape_tool, 'default')
        self.assertIsNotNone(ds.last_successful_index_date)
        self.assertEqual(ds.error, '')
        self.assertEqual(ds.user_error, '')

        # Check Milvus write was called
        mock_write_to_milvus.assert_called_once()

    @patch('core.tasks.get_web_scraper')
    @patch('core.tasks.fetch_data_source_content')
    @patch('core.tasks.get_guru_type_object_without_filters')
    @patch('core.tasks.DataSource.write_to_milvus')
    @patch('core.tasks.redis_client')
    @patch('core.tasks.get_default_settings')
    def test_data_source_retrieval_fetch_exception(self, mock_get_settings, mock_redis, mock_write_to_milvus, mock_get_guru_type, mock_fetch_content, mock_get_scraper):
        """Test retrieval when fetch_data_source_content raises an exception."""
        mock_scraper_instance = MagicMock()
        mock_get_scraper.return_value = (mock_scraper_instance, 'default')
        mock_get_guru_type.return_value = self.guru_type

        ds = DataSource.objects.create(
            guru_type=self.guru_type,
            type=DataSource.Type.WEBSITE,
            status=DataSource.Status.NOT_PROCESSED,
            url="http://example.com/page-error"
        )

        # Mock fetch_data_source_content to raise an error
        error_message = "Failed to fetch content"
        mock_fetch_content.side_effect = Exception(error_message)

        data_source_retrieval(guru_type_slug=self.guru_type.slug)

        ds.refresh_from_db()

        # Assertions
        mock_fetch_content.assert_called_once()
        self.assertEqual(ds.status, DataSource.Status.FAIL)
        self.assertEqual(ds.error, error_message)
        self.assertEqual(ds.user_error, "Error while fetching data source")
        self.assertIsNone(ds.last_successful_index_date)
        mock_write_to_milvus.assert_not_called()

    @patch('core.tasks.get_web_scraper')
    @patch('core.tasks.fetch_data_source_content')
    @patch('core.tasks.get_guru_type_object_without_filters')
    @patch('core.tasks.DataSource.write_to_milvus')
    @patch('core.tasks.redis_client')
    @patch('core.tasks.get_default_settings')
    def test_data_source_retrieval_throttle_error(self, mock_get_settings, mock_redis, mock_write_to_milvus, mock_get_guru_type, mock_fetch_content, mock_get_scraper):
        """Test retrieval handling WebsiteContentExtractionThrottleError."""
        mock_scraper_instance = MagicMock()
        mock_get_scraper.return_value = (mock_scraper_instance, 'default')
        mock_get_guru_type.return_value = self.guru_type

        ds = DataSource.objects.create(
            guru_type=self.guru_type,
            type=DataSource.Type.WEBSITE,
            status=DataSource.Status.NOT_PROCESSED,
            url="http://example.com/page-throttle"
        )

        error_message = "Rate limited"
        mock_fetch_content.side_effect = WebsiteContentExtractionThrottleError(error_message)

        data_source_retrieval(guru_type_slug=self.guru_type.slug)

        ds.refresh_from_db()

        # Assertions for throttling
        mock_fetch_content.assert_called_once()
        self.assertEqual(ds.status, DataSource.Status.NOT_PROCESSED) # Should remain NOT_PROCESSED
        self.assertEqual(ds.error, error_message)
        self.assertEqual(ds.user_error, error_message)
        mock_write_to_milvus.assert_not_called()

    @patch('core.tasks.get_web_scraper')
    @patch('core.tasks.fetch_data_source_content')
    @patch('core.tasks.get_guru_type_object_without_filters')
    @patch('core.tasks.DataSource.write_to_milvus')
    @patch('core.tasks.redis_client')
    @patch('core.tasks.get_default_settings')
    def test_data_source_retrieval_youtube_error(self, mock_get_settings, mock_redis, mock_write_to_milvus, mock_get_guru_type, mock_fetch_content, mock_get_scraper):
        """Test retrieval handling YouTubeContentExtractionError."""
        mock_scraper_instance = MagicMock()
        mock_get_scraper.return_value = (mock_scraper_instance, 'default')
        mock_get_guru_type.return_value = self.guru_type

        ds = DataSource.objects.create(
            guru_type=self.guru_type,
            type=DataSource.Type.YOUTUBE,
            status=DataSource.Status.NOT_PROCESSED,
            url="http://youtube.com/watch?v=invalid"
        )

        error_message = "Invalid video ID"
        mock_fetch_content.side_effect = YouTubeContentExtractionError(error_message)

        data_source_retrieval(guru_type_slug=self.guru_type.slug)

        ds.refresh_from_db()

        # Assertions for YouTube error
        mock_fetch_content.assert_called_once()
        self.assertEqual(ds.status, DataSource.Status.FAIL)
        self.assertEqual(ds.error, error_message)
        self.assertEqual(ds.user_error, error_message)
        mock_write_to_milvus.assert_not_called()

    @patch('core.tasks.get_web_scraper')
    @patch('core.tasks.fetch_data_source_content')
    @patch('core.tasks.get_guru_type_object_without_filters')
    @patch('core.tasks.DataSource.write_to_milvus')
    @patch('core.tasks.redis_client')
    @patch('core.tasks.get_default_settings')
    def test_data_source_retrieval_github_limit_error(self, mock_get_settings, mock_redis, mock_write_to_milvus, mock_get_guru_type, mock_fetch_content, mock_get_scraper):
        """Test retrieval handling GithubRepoSizeLimitError."""
        mock_scraper_instance = MagicMock()
        mock_get_scraper.return_value = (mock_scraper_instance, 'default')
        mock_get_guru_type.return_value = self.guru_type

        ds = DataSource.objects.create(
            guru_type=self.guru_type,
            type=DataSource.Type.GITHUB_REPO,
            status=DataSource.Status.NOT_PROCESSED,
            url="http://github.com/user/repo-too-big"
        )

        error_message = "Repo exceeds size limit"
        # Note: In the actual task, GitHub errors are raised within fetch_data_source_content
        mock_fetch_content.side_effect = GithubRepoSizeLimitError(error_message)

        # Need to explicitly call the github part of the task logic
        # The main function calls process_guru_type twice, once for github, once for others.
        # We can simulate this by calling the task twice or patching the inner function directly.
        # Let's just call the main task and let it filter.
        data_source_retrieval(guru_type_slug=self.guru_type.slug)

        ds.refresh_from_db()

        # Assertions for GitHub error
        mock_fetch_content.assert_called_once()
        self.assertEqual(ds.status, DataSource.Status.FAIL)
        self.assertEqual(ds.error, error_message)
        self.assertEqual(ds.user_error, error_message)
        mock_write_to_milvus.assert_not_called()

    @override_settings(WEB_SCRAPER_TOOL='firecrawl')
    @patch('core.tasks.get_web_scraper')
    @patch('core.tasks.process_website_data_sources_batch')
    @patch('core.tasks.get_guru_type_object_without_filters')
    @patch('core.tasks.DataSource.write_to_milvus')
    @patch('core.tasks.redis_client')
    @patch('core.tasks.get_default_settings')
    def test_data_source_retrieval_firecrawl_batch_success(self, mock_get_settings, mock_redis, mock_write_to_milvus, mock_get_guru_type, mock_process_batch, mock_get_scraper):
        """Test retrieval using Firecrawl batch processing for WEBSITE sources."""
        # Mock scraper to be Firecrawl
        mock_firecrawl_instance = MagicMock(spec=FirecrawlScraper)
        mock_get_scraper.return_value = (mock_firecrawl_instance, 'firecrawl')

        mock_get_guru_type.return_value = self.guru_type

        # Create multiple website data sources
        ds1 = DataSource.objects.create(guru_type=self.guru_type, type=DataSource.Type.WEBSITE, status=DataSource.Status.NOT_PROCESSED, url="http://example.com/fire1")
        ds2 = DataSource.objects.create(guru_type=self.guru_type, type=DataSource.Type.WEBSITE, status=DataSource.Status.NOT_PROCESSED, url="http://example.com/fire2")

        # Mock process_website_data_sources_batch response
        # Simulate that the batch processor updated the status and content
        processed_ds1 = DataSource(id=ds1.id, guru_type=self.guru_type, type=DataSource.Type.WEBSITE, status=DataSource.Status.SUCCESS, url="http://example.com/fire1", title="Fire 1", content="Content 1", scrape_tool='firecrawl', error=None)
        processed_ds2 = DataSource(id=ds2.id, guru_type=self.guru_type, type=DataSource.Type.WEBSITE, status=DataSource.Status.SUCCESS, url="http://example.com/fire2", title="Fire 2", content="Content 2", scrape_tool='firecrawl', error=None)
        mock_process_batch.return_value = [processed_ds1, processed_ds2]

        # Mock bulk_update to check it's called
        with patch('core.tasks.DataSource.objects.bulk_update') as mock_bulk_update:
            data_source_retrieval(guru_type_slug=self.guru_type.slug)

            # Assertions
            mock_process_batch.assert_called_once()
            batch_args, _ = mock_process_batch.call_args
            # Check the list of objects passed to the batch function
            self.assertEqual(len(batch_args[0]), 2)
            self.assertIn(ds1, batch_args[0])
            self.assertIn(ds2, batch_args[0])

            # Check bulk_update was called for success
            mock_bulk_update.assert_called_once()
            update_args, _ = mock_bulk_update.call_args
            self.assertEqual(len(update_args[0]), 2) # Both successful
            self.assertIn('status', update_args[1])
            self.assertIn('content', update_args[1])

            # Check Milvus write was called for each successful source
            self.assertEqual(mock_write_to_milvus.call_count, 2)

        # Refresh from DB (although bulk_update was mocked, check the instance state)
        # Note: The actual DB state won't reflect bulk_update unless we let it run.
        # We check that write_to_milvus was called instead.

    @override_settings(WEB_SCRAPER_TOOL='firecrawl')
    @patch('core.tasks.get_web_scraper')
    @patch('core.tasks.process_website_data_sources_batch')
    @patch('core.tasks.get_guru_type_object_without_filters')
    @patch('core.tasks.DataSource.write_to_milvus')
    @patch('core.tasks.redis_client')
    @patch('core.tasks.get_default_settings')
    def test_data_source_retrieval_firecrawl_batch_throttle(self, mock_get_settings, mock_redis, mock_write_to_milvus, mock_get_guru_type, mock_process_batch, mock_get_scraper):
        """Test Firecrawl batch processing when a throttle error occurs."""
        mock_firecrawl_instance = MagicMock(spec=FirecrawlScraper)
        mock_get_scraper.return_value = (mock_firecrawl_instance, 'firecrawl')
        mock_get_guru_type.return_value = self.guru_type

        ds1 = DataSource.objects.create(guru_type=self.guru_type, type=DataSource.Type.WEBSITE, status=DataSource.Status.NOT_PROCESSED, url="http://example.com/fire-throttle1")
        ds2 = DataSource.objects.create(guru_type=self.guru_type, type=DataSource.Type.WEBSITE, status=DataSource.Status.NOT_PROCESSED, url="http://example.com/fire-throttle2")

        # Mock batch processing raising throttle error
        throttle_message = "Firecrawl throttled"
        mock_process_batch.side_effect = WebsiteContentExtractionThrottleError(throttle_message)

        with patch('core.tasks.DataSource.objects.bulk_update') as mock_bulk_update:
            data_source_retrieval(guru_type_slug=self.guru_type.slug)

            # Assertions
            mock_process_batch.assert_called_once()

            # Check bulk_update was called to mark batch as NOT_PROCESSED
            mock_bulk_update.assert_called_once()
            update_args, _ = mock_bulk_update.call_args
            self.assertEqual(len(update_args[0]), 2) # Both marked
            updated_objects = update_args[0]
            self.assertEqual(updated_objects[0].status, DataSource.Status.NOT_PROCESSED)
            self.assertEqual(updated_objects[1].status, DataSource.Status.NOT_PROCESSED)
            self.assertEqual(updated_objects[0].error, throttle_message)
            self.assertEqual(updated_objects[1].error, throttle_message)
            self.assertEqual(updated_objects[0].user_error, throttle_message)
            self.assertEqual(updated_objects[1].user_error, throttle_message)
            self.assertIn('status', update_args[1])
            self.assertIn('error', update_args[1])
            self.assertIn('user_error', update_args[1])

            # Milvus should not be called
            mock_write_to_milvus.assert_not_called()

    @patch('core.tasks.fetch_data_source_content')
    @patch('core.tasks.get_guru_type_object_without_filters')
    @patch('core.tasks.DataSource.write_to_milvus')
    @patch('core.tasks.redis_client')
    @patch('core.tasks.get_default_settings')
    def test_data_source_retrieval_integration(self, mock_get_settings, mock_redis, mock_write_to_milvus, mock_get_guru_type, mock_fetch_content):
        """Test retrieval for an integration data source (e.g., JIRA)."""
        # Note: This test assumes WEB_SCRAPER_TOOL is not 'firecrawl'
        mock_get_guru_type.return_value = self.guru_type

        integration = Integration.objects.create(
            guru_type=self.guru_type,
            type=Integration.Type.JIRA,
            # Add necessary fields if fetch_data_source_content needs them
            # e.g., api_key, base_url etc.
        )

        ds = DataSource.objects.create(
            guru_type=self.guru_type,
            type=DataSource.Type.JIRA,
            status=DataSource.Status.NOT_PROCESSED,
            url="https://jira.example.com/JIRA-123" # Example ID/key
        )

        def fetch_side_effect(int_arg, data_source, language_code):
            self.assertEqual(int_arg.id, integration.id) # Check integration passed
            data_source.title = "Jira Issue 123"
            data_source.content = "Details of Jira issue"
            return data_source

        mock_fetch_content.side_effect = fetch_side_effect

        data_source_retrieval(guru_type_slug=self.guru_type.slug)

        ds.refresh_from_db()

        # Assertions
        mock_fetch_content.assert_called_once()
        self.assertEqual(ds.status, DataSource.Status.SUCCESS)
        self.assertEqual(ds.title, "Jira Issue 123")
        self.assertEqual(ds.content, "Details of Jira issue")
        mock_write_to_milvus.assert_called_once()

    # Add tests for self-hosted specific checks (AIProvider settings)
    @override_settings(ENV='selfhosted')
    @patch('core.tasks.get_default_settings')
    @patch('core.tasks.process_guru_type_data_sources') # Don't run actual processing
    def test_data_source_retrieval_selfhosted_openai_invalid(self, mock_process, mock_get_settings):
        """Test selfhosted check skips processing if OpenAI key is invalid."""
        mock_settings_obj = MagicMock(spec=Settings)
        mock_settings_obj.ai_model_provider = Settings.AIProvider.OPENAI
        mock_settings_obj.is_openai_key_valid = False
        mock_get_settings.return_value = mock_settings_obj

        data_source_retrieval() # Call without specific guru type

        mock_process.assert_not_called()

    @override_settings(ENV='selfhosted')
    @patch('core.tasks.get_default_settings')
    @patch('core.tasks.process_guru_type_data_sources') # Don't run actual processing
    def test_data_source_retrieval_selfhosted_ollama_invalid_url(self, mock_process, mock_get_settings):
        """Test selfhosted check skips processing if Ollama URL is invalid."""
        mock_settings_obj = MagicMock(spec=Settings)
        mock_settings_obj.ai_model_provider = Settings.AIProvider.OLLAMA
        mock_settings_obj.is_ollama_url_valid = False
        mock_settings_obj.is_ollama_embedding_model_valid = True
        mock_get_settings.return_value = mock_settings_obj

        data_source_retrieval()

        mock_process.assert_not_called()

    @override_settings(ENV='selfhosted')
    @patch('core.tasks.get_default_settings')
    @patch('core.tasks.process_guru_type_data_sources') # Don't run actual processing
    def test_data_source_retrieval_selfhosted_ollama_invalid_model(self, mock_process, mock_get_settings):
        """Test selfhosted check skips processing if Ollama embedding model is invalid."""
        mock_settings_obj = MagicMock(spec=Settings)
        mock_settings_obj.ai_model_provider = Settings.AIProvider.OLLAMA
        mock_settings_obj.is_ollama_url_valid = True
        mock_settings_obj.is_ollama_embedding_model_valid = False
        mock_get_settings.return_value = mock_settings_obj

        data_source_retrieval()

        mock_process.assert_not_called()
    
    @override_settings(ENV='selfhosted')
    @patch('core.tasks.get_default_settings')
    @patch('core.tasks.process_guru_type_data_sources') # Mock processing
    @patch('core.tasks.get_guru_type_names') # Mock guru type fetching
    def test_data_source_retrieval_selfhosted_valid(self, mock_get_names, mock_process, mock_get_settings):
        """Test selfhosted check proceeds if settings are valid."""
        mock_settings_obj = MagicMock(spec=Settings)
        mock_settings_obj.ai_model_provider = Settings.AIProvider.OPENAI
        mock_settings_obj.is_openai_key_valid = True
        mock_get_settings.return_value = mock_settings_obj
        mock_get_names.return_value = [self.guru_type.slug]

        data_source_retrieval() # Call without specific guru type

        # Should call process twice per guru_type (github=True/False)
        self.assertEqual(mock_process.call_count, 2)
        mock_process.assert_any_call(guru_type_slug=self.guru_type.slug, is_github=True, countdown=0)
        mock_process.assert_any_call(guru_type_slug=self.guru_type.slug, is_github=False, countdown=0)
