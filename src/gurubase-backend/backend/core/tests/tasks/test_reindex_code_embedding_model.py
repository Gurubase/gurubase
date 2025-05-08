from django.test import TestCase
from unittest.mock import patch
from core.models import GuruType, DataSource
from core.tasks import reindex_code_embedding_model
from core.utils import get_default_settings


class ReindexCodeEmbeddingModelTaskTests(TestCase):
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
        
        # Create GitHub repository data sources
        self.github_repo1 = DataSource.objects.create(
            guru_type=self.guru_type,
            title="GitHub Test Repo 1",
            type=DataSource.Type.GITHUB_REPO,
            url="https://github.com/test/repo1",
            status=DataSource.Status.SUCCESS
        )
        
        self.github_repo2 = DataSource.objects.create(
            guru_type=self.guru_type,
            title="GitHub Test Repo 2",
            type=DataSource.Type.GITHUB_REPO,
            url="https://github.com/test/repo2",
            status=DataSource.Status.SUCCESS
        )
        
        # Create a non-GitHub data source (should be excluded from processing)
        self.website_data_source = DataSource.objects.create(
            guru_type=self.guru_type,
            title="Web Test Source",
            type=DataSource.Type.WEBSITE,
            url="https://example.com",
            status=DataSource.Status.SUCCESS
        )
    
    @patch('core.tasks.get_embedding_model_config')
    @patch('core.models.DataSource.delete_from_milvus')
    @patch('core.models.DataSource.write_to_milvus')
    def test_reindex_code_embedding_model_success(
        self, 
        mock_write_to_milvus, 
        mock_delete_from_milvus,
        mock_get_embedding_config
    ):
        """
        Test successful reindexing of GitHub repositories when code_embedding_model changes.
        This should:
        1. Update GitHub repos to NOT_PROCESSED
        2. Delete GitHub repos from old collection
        3. Write GitHub repos to new collection
        4. Update GitHub repos to SUCCESS
        """
        # Mock the embedding model config to return collection name and dimensions
        mock_get_embedding_config.side_effect = [
            ("old_model_collection", 768),  # For delete_from_milvus
            ("new_model_collection", 1536)  # For write_to_milvus
        ]
        
        # Call the task function
        reindex_code_embedding_model(
            guru_type_id=self.guru_type.id,
            old_model="old_model",
            new_model="new_model"
        )
        
        # Refresh data sources from database
        self.github_repo1.refresh_from_db()
        self.github_repo2.refresh_from_db()
        self.website_data_source.refresh_from_db()
        
        # Verify GitHub repos were processed
        self.assertEqual(self.github_repo1.status, DataSource.Status.SUCCESS)
        self.assertEqual(self.github_repo2.status, DataSource.Status.SUCCESS)
        
        # Verify non-GitHub data source was not touched
        self.assertEqual(self.website_data_source.status, DataSource.Status.SUCCESS)
        
        # Verify delete_from_milvus and write_to_milvus were called for GitHub repos only
        self.assertEqual(mock_delete_from_milvus.call_count, 2)
        self.assertEqual(mock_write_to_milvus.call_count, 2)
        
        # Verify the correct models were passed to delete_from_milvus and write_to_milvus
        mock_delete_from_milvus.assert_any_call(overridden_model="old_model")
        mock_write_to_milvus.assert_any_call(overridden_model="new_model")
    
    @patch('core.models.DataSource.delete_from_milvus')
    @patch('core.tasks.logger.error')
    def test_reindex_code_embedding_model_error_handling(
        self, 
        mock_logger_error, 
        mock_delete_from_milvus
    ):
        """
        Test error handling during code embedding model reindexing.
        This should:
        1. Set GitHub repos to NOT_PROCESSED
        2. Log the error if delete_from_milvus fails
        3. Mark GitHub repos as FAILED
        4. Re-raise the exception
        """
        # Mock delete_from_milvus to raise an exception
        mock_delete_from_milvus.side_effect = Exception("Test error")
        
        # Call the task function and expect an exception
        with self.assertRaises(Exception):
            reindex_code_embedding_model(
                guru_type_id=self.guru_type.id,
                old_model="old_model",
                new_model="new_model"
            )
        
        # Verify GitHub repos were marked as FAILED
        self.github_repo1.refresh_from_db()
        self.github_repo2.refresh_from_db()
        self.website_data_source.refresh_from_db()
        
        self.assertEqual(self.github_repo1.status, DataSource.Status.FAIL)
        self.assertEqual(self.github_repo2.status, DataSource.Status.FAIL)
        
        # Verify non-GitHub data source was not touched
        self.assertEqual(self.website_data_source.status, DataSource.Status.SUCCESS)
        
        # Verify error was logged
        mock_logger_error.assert_called_once()
    
    @patch('core.models.DataSource.delete_from_milvus')
    @patch('core.models.DataSource.write_to_milvus')
    def test_reindex_code_embedding_model_no_github_repos(
        self, 
        mock_write_to_milvus, 
        mock_delete_from_milvus
    ):
        """
        Test reindexing when there are no GitHub repositories.
        The function should complete without errors even if no repositories are found.
        """
        # Delete existing GitHub repos
        DataSource.objects.filter(type=DataSource.Type.GITHUB_REPO).delete()
        
        # Call the task function
        reindex_code_embedding_model(
            guru_type_id=self.guru_type.id,
            old_model="old_model",
            new_model="new_model"
        )
        
        # Verify delete_from_milvus and write_to_milvus were not called
        mock_delete_from_milvus.assert_not_called()
        mock_write_to_milvus.assert_not_called()
    
    @patch('core.tasks.GuruType.objects.get')
    @patch('core.tasks.logger.error')
    def test_reindex_code_embedding_model_guru_type_not_found(
        self,
        mock_logger_error,
        mock_guru_type_get
    ):
        """
        Test error handling when the GuruType is not found.
        This should log an error and re-raise the exception.
        """
        # Mock GuruType.objects.get to raise an exception
        mock_guru_type_get.side_effect = GuruType.DoesNotExist("GuruType does not exist")
        
        # Call the task function and expect an exception
        with self.assertRaises(GuruType.DoesNotExist):
            reindex_code_embedding_model(
                guru_type_id=999,  # Non-existent ID
                old_model="old_model",
                new_model="new_model"
            )
        
        # Verify error was logged
        mock_logger_error.assert_called_once()
    
    @patch('core.models.DataSource.delete_from_milvus')
    @patch('core.models.DataSource.write_to_milvus')
    def test_reindex_code_embedding_model_with_file_content(
        self,
        mock_write_to_milvus,
        mock_delete_from_milvus
    ):
        """
        Test reindexing with GitHub repositories that contain file content.
        This should properly handle repositories with content.
        """
        # Update GitHub repo with file content
        self.github_repo1.content = "# Test GitHub Repository\nThis is a test repository content."
        self.github_repo1.save()
        
        # Call the task function
        reindex_code_embedding_model(
            guru_type_id=self.guru_type.id,
            old_model="old_model",
            new_model="new_model"
        )
        
        # Refresh data source from database
        self.github_repo1.refresh_from_db()
        
        # Verify GitHub repo was processed
        self.assertEqual(self.github_repo1.status, DataSource.Status.SUCCESS)
        
        # Verify delete_from_milvus and write_to_milvus were called
        mock_delete_from_milvus.assert_any_call(overridden_model="old_model")
        mock_write_to_milvus.assert_any_call(overridden_model="new_model")
