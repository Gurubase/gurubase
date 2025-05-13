from django.test import TestCase
from unittest.mock import patch
from django.core.files.uploadedfile import SimpleUploadedFile

from core.models import GuruType, DataSource
from core.tasks import reindex_text_embedding_model
from core.utils import get_default_settings


class ReindexTextEmbeddingModelTaskTests(TestCase):
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
        
        # Create some non-GitHub data sources
        self.web_data_source = DataSource.objects.create(
            guru_type=self.guru_type,
            title="Web Test Source",
            type=DataSource.Type.WEBSITE,
            url="https://example.com",
            status=DataSource.Status.SUCCESS
        )
        
        # Create PDF file mock
        pdf_content = b"%PDF-1.5\n%Test PDF content"
        pdf_file = SimpleUploadedFile(
            name="test_document.pdf",
            content=pdf_content,
            content_type="application/pdf"
        )
        
        # Create a PDF data source with mock file
        self.pdf_data_source = DataSource.objects.create(
            guru_type=self.guru_type,
            title="PDF Test Source",
            type=DataSource.Type.PDF,
            file=pdf_file,  # Add the mock file
            status=DataSource.Status.SUCCESS
        )
        
        # Create a GitHub data source (should be excluded from processing)
        self.github_data_source = DataSource.objects.create(
            guru_type=self.guru_type,
            title="GitHub Test Source",
            type=DataSource.Type.GITHUB_REPO,
            url="https://github.com/test/repo",
            status=DataSource.Status.SUCCESS
        )
        
        # Patch the file-related methods to avoid actual file operations
        self.file_patcher = patch.multiple(
            'core.models.DataSource',
            get_file_path=lambda self: f"test/path/{self.file.name}",
            get_url_prefix=lambda self: "https://example.com/storage"
        )
        self.file_patcher.start()
        self.addCleanup(self.file_patcher.stop)
    
    @patch('core.tasks.get_embedding_model_config')
    @patch('core.tasks.milvus_utils.drop_collection')
    @patch('core.tasks.milvus_utils.create_context_collection')
    @patch('core.models.DataSource.delete_from_milvus')
    @patch('core.models.DataSource.write_to_milvus')
    def test_reindex_with_different_dimensions(
        self, 
        mock_write_to_milvus, 
        mock_delete_from_milvus, 
        mock_create_collection, 
        mock_drop_collection, 
        mock_get_embedding_config
    ):
        """
        Test reindexing when old and new embedding models have different dimensions.
        This should:
        1. Update non-GitHub data sources to NOT_PROCESSED
        2. Get dimensions for both models
        3. Drop the old collection
        4. Delete data sources from old collection
        5. Create a new collection
        6. Write data sources to new collection
        7. Update data sources to SUCCESS
        """
        # Mock the embedding model config to return different dimensions
        mock_get_embedding_config.side_effect = [
            ("old_model", 768),  # Old model with 768 dimensions
            ("new_model", 1536)  # New model with 1536 dimensions
        ]
        
        # Call the task function
        reindex_text_embedding_model(
            guru_type_id=self.guru_type.id,
            old_model="old_model",
            new_model="new_model"
        )
        
        # Verify all non-GitHub data sources were processed
        # Check they were first marked as NOT_PROCESSED
        self.web_data_source.refresh_from_db()
        self.pdf_data_source.refresh_from_db()
        self.github_data_source.refresh_from_db()
        
        # Check they were updated to SUCCESS status
        self.assertEqual(self.web_data_source.status, DataSource.Status.SUCCESS)
        self.assertEqual(self.pdf_data_source.status, DataSource.Status.SUCCESS)
        # GitHub sources should be untouched
        self.assertEqual(self.github_data_source.status, DataSource.Status.SUCCESS)
        
        # Check that collection was dropped and recreated for different dimensions
        mock_drop_collection.assert_called_once_with(self.guru_type.milvus_collection_name)
        mock_create_collection.assert_called_once_with(self.guru_type.milvus_collection_name, 1536)
        
        # Verify delete_from_milvus and write_to_milvus were called for non-GitHub sources
        self.assertEqual(mock_delete_from_milvus.call_count, 2)
        self.assertEqual(mock_write_to_milvus.call_count, 2)
        
        # Check the correct model was passed to the methods
        mock_delete_from_milvus.assert_any_call(overridden_model="old_model")
        mock_write_to_milvus.assert_any_call(overridden_model="new_model")
    
    @patch('core.tasks.get_embedding_model_config')
    @patch('core.tasks.milvus_utils.drop_collection')
    @patch('core.tasks.milvus_utils.create_context_collection')
    @patch('core.models.DataSource.delete_from_milvus')
    @patch('core.models.DataSource.write_to_milvus')
    def test_reindex_with_same_dimensions(
        self, 
        mock_write_to_milvus, 
        mock_delete_from_milvus, 
        mock_create_collection, 
        mock_drop_collection, 
        mock_get_embedding_config
    ):
        """
        Test reindexing when old and new embedding models have the same dimensions.
        This should:
        1. Update non-GitHub data sources to NOT_PROCESSED
        2. Get dimensions for both models
        3. NOT drop the old collection (since dimensions are the same)
        4. Delete data sources from old collection
        5. NOT create a new collection (since dimensions are the same)
        6. Write data sources to new collection
        7. Update data sources to SUCCESS
        """
        # Mock the embedding model config to return the same dimensions
        mock_get_embedding_config.side_effect = [
            ("old_model", 768),  # Old model with 768 dimensions
            ("new_model", 768)   # New model with 768 dimensions
        ]
        
        # Call the task function
        reindex_text_embedding_model(
            guru_type_id=self.guru_type.id,
            old_model="old_model",
            new_model="new_model"
        )
        
        # Verify all non-GitHub data sources were processed
        self.web_data_source.refresh_from_db()
        self.pdf_data_source.refresh_from_db()
        
        # Check they were updated to SUCCESS status
        self.assertEqual(self.web_data_source.status, DataSource.Status.SUCCESS)
        self.assertEqual(self.pdf_data_source.status, DataSource.Status.SUCCESS)
        
        # Collection should NOT be dropped or recreated since dimensions are the same
        mock_drop_collection.assert_not_called()
        mock_create_collection.assert_not_called()
        
        # Verify delete_from_milvus and write_to_milvus were called for non-GitHub sources
        self.assertEqual(mock_delete_from_milvus.call_count, 2)
        self.assertEqual(mock_write_to_milvus.call_count, 2)
    
    @patch('core.tasks.get_embedding_model_config')
    @patch('core.models.DataSource.delete_from_milvus')
    @patch('core.tasks.logger.error')
    def test_reindex_error_handling(
        self, 
        mock_logger_error, 
        mock_delete_from_milvus, 
        mock_get_embedding_config
    ):
        """
        Test error handling during reindexing.
        This should:
        1. Log the error
        2. Mark all data sources as FAILED
        3. Re-raise the exception
        """
        # Mock get_embedding_model_config to raise an exception
        mock_get_embedding_config.side_effect = Exception("Test error")
        
        # Call the task function and expect an exception
        with self.assertRaises(Exception):
            reindex_text_embedding_model(
                guru_type_id=self.guru_type.id,
                old_model="old_model",
                new_model="new_model"
            )
        
        # Verify all non-GitHub data sources were marked as FAILED
        self.web_data_source.refresh_from_db()
        self.pdf_data_source.refresh_from_db()
        self.github_data_source.refresh_from_db()
        
        self.assertEqual(self.web_data_source.status, DataSource.Status.FAIL)
        self.assertEqual(self.pdf_data_source.status, DataSource.Status.FAIL)
        # GitHub sources should be untouched
        self.assertEqual(self.github_data_source.status, DataSource.Status.SUCCESS)
        
        # Verify error was logged
        mock_logger_error.assert_called_once()
        
    @patch('core.tasks.get_embedding_model_config')
    @patch('core.tasks.milvus_utils.drop_collection')
    @patch('core.tasks.milvus_utils.create_context_collection')
    @patch('core.models.DataSource.delete_from_milvus')
    @patch('core.models.DataSource.write_to_milvus')
    def test_reindex_with_provided_dimensions(
        self, 
        mock_write_to_milvus, 
        mock_delete_from_milvus, 
        mock_create_collection, 
        mock_drop_collection, 
        mock_get_embedding_config
    ):
        """
        Test reindexing when dimensions are provided directly to the function.
        This should use the provided dimensions instead of calling get_embedding_model_config.
        """
        # Call the task function with dimensions provided
        reindex_text_embedding_model(
            guru_type_id=self.guru_type.id,
            old_model="old_model",
            new_model="new_model",
            old_dimension=512,
            new_dimension=1024
        )
        
        # get_embedding_model_config should not be called when dimensions are provided
        mock_get_embedding_config.assert_not_called()
        
        # Check that collection was dropped and recreated for different dimensions
        mock_drop_collection.assert_called_once_with(self.guru_type.milvus_collection_name)
        mock_create_collection.assert_called_once_with(self.guru_type.milvus_collection_name, 1024)
        
        # Verify delete_from_milvus and write_to_milvus were called for non-GitHub sources
        self.assertEqual(mock_delete_from_milvus.call_count, 2)
        self.assertEqual(mock_write_to_milvus.call_count, 2)

    @patch('core.tasks.get_embedding_model_config')
    @patch('core.tasks.milvus_utils.drop_collection')
    @patch('core.tasks.milvus_utils.create_context_collection')
    @patch('core.models.DataSource.delete_from_milvus')
    @patch('core.models.DataSource.write_to_milvus')
    @patch('core.models.DataSource.get_file_path')
    @patch('django.conf.settings.STORAGE_TYPE', 'local')
    def test_reindex_with_pdf_file(
        self,
        mock_get_file_path,
        mock_write_to_milvus,
        mock_delete_from_milvus,
        mock_create_collection,
        mock_drop_collection,
        mock_get_embedding_config
    ):
        """
        Test reindexing with a PDF file data source.
        This should verify that PDF files are properly handled during reindexing.
        """
        # Set up mock file path
        mock_get_file_path.return_value = "test/path/test_document.pdf"
        
        # Mock the embedding model config to return dimensions
        mock_get_embedding_config.side_effect = [
            ("old_model", 768),
            ("new_model", 1536)
        ]
        
        # Call the task function
        reindex_text_embedding_model(
            guru_type_id=self.guru_type.id,
            old_model="old_model",
            new_model="new_model"
        )
        
        # Refresh data source from database
        self.pdf_data_source.refresh_from_db()
        
        # Verify PDF data source was processed
        self.assertEqual(self.pdf_data_source.status, DataSource.Status.SUCCESS)
        
        # Verify delete_from_milvus and write_to_milvus were called for PDF source
        mock_delete_from_milvus.assert_any_call(overridden_model="old_model")
        mock_write_to_milvus.assert_any_call(overridden_model="new_model")
