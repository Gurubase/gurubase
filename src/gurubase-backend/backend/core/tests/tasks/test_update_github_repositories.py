from django.test import TestCase
from django.utils import timezone
from unittest.mock import patch, MagicMock
import os
from datetime import datetime, UTC, timedelta
from core.models import GuruType, DataSource, GithubFile
from core.tasks import update_github_repositories
from core.exceptions import GithubInvalidRepoError, GithubRepoSizeLimitError, GithubRepoFileCountLimitError
from core.utils import get_default_settings


class TestUpdateGithubRepositories(TestCase):
    def setUp(self):
        """
        Set up test environment with necessary objects:
        1. Default settings
        2. GuruType for testing
        3. Sample GitHub DataSource
        4. Sample GithubFiles
        """
        # Initialize default settings
        get_default_settings()
        
        # Create test GuruType
        self.guru_type = GuruType.objects.create(
            slug="test-guru",
            name="Test Guru",
            custom=True,
            active=True,
            github_repo_size_limit_mb=50,
            github_file_count_limit_per_repo_hard=1000
        )
        
        # Create test GitHub repo data source
        self.data_source = DataSource.objects.create(
            url="https://github.com/test/repo",
            type=DataSource.Type.GITHUB_REPO,
            status=DataSource.Status.SUCCESS,
            guru_type=self.guru_type,
            default_branch="main",
            github_glob_include=True,
            github_glob_pattern="**/*.py"
        )
        
        # Create test GitHub files
        self.github_file = GithubFile.objects.create(
            data_source=self.data_source,
            path="test_file.py",
            content="def test_function():\n    return True",
            size=42,
            link="https://github.com/test/repo/tree/main/test_file.py"
        )
        
        # Create a file that will be "deleted" in the repository
        self.deleted_file = GithubFile.objects.create(
            data_source=self.data_source,
            path="deleted_file.py",
            content="def deleted_function():\n    return True",
            size=48,
            link="https://github.com/test/repo/tree/main/deleted_file.py"
        )
        
        # Set the update time to the past to ensure "modified" detection works
        update_time = timezone.now() - timedelta(days=1)
        GithubFile.objects.filter(id=self.github_file.id).update(date_updated=update_time)
        GithubFile.objects.filter(id=self.deleted_file.id).update(date_updated=update_time)
        
        # Update our instance with the new timestamp
        self.github_file.refresh_from_db()
        self.deleted_file.refresh_from_db()

    @patch('core.tasks.get_milvus_client')
    @patch('core.github.data_source_handler.clone_repository')
    @patch('core.github.data_source_handler.read_repository')
    @patch('git.Repo')
    def test_update_github_repositories_success(self, mock_repo, mock_read_repository, mock_clone_repository, mock_get_milvus_client):
        """
        Test successful update of GitHub repositories
        - Should handle modified files
        - Should handle new files
        - Should handle deleted files
        """
        # Set up mock for clone_repository
        mock_temp_dir = "/tmp/test_repo"
        mock_clone_repository.return_value = (mock_temp_dir, mock_repo)
        
        # Set up the repository structure with updated and new files
        mock_read_repository.return_value = [
            {
                'path': 'test_file.py',  # Modified file
                'content': 'def test_function():\n    return True\n# Modified',
                'size': 62
            },
            {
                'path': 'new_file.py',  # New file
                'content': 'def new_function():\n    return True',
                'size': 40
            }
            # Note: deleted_file.py is intentionally missing
        ]
        
        # Mock the git commit history for the modified file with a specific commit
        mock_commit = MagicMock()
        # Set committed date to current time to ensure it's newer than the file's date_updated
        mock_commit.committed_date = (timezone.now() + timedelta(days=1)).timestamp()
        # Configure mock_repo to return our mock_commit for any path
        mock_repo.iter_commits.side_effect = [iter([mock_commit]), iter([mock_commit])]
        
        # Mock DataSource.objects.get to return our data source
        with patch('core.models.DataSource.objects.get') as mock_get_ds:
            mock_get_ds.return_value = self.data_source
            
            # Mock system call to remove temp directory
            with patch('os.system') as mock_system:
                # Run the task
                update_github_repositories()
                
                # Verify temp directory was cleaned up
                mock_system.assert_called_with(f"rm -rf {mock_temp_dir}")
        
        # Verify the mock functions were called correctly
        mock_clone_repository.assert_called_with(self.data_source.url)
        mock_read_repository.assert_called_with(
            mock_temp_dir,
            self.data_source.github_glob_include,
            self.data_source.github_glob_pattern
        )
        
        # Verify files were updated in the database
        self.data_source.refresh_from_db()
        
        # Check that old file was updated
        updated_file = GithubFile.objects.get(data_source=self.data_source, path='test_file.py')
        self.assertIn("# Modified", updated_file.content)
        self.assertEqual(updated_file.size, 62)
        
        # Check that new file was created
        self.assertTrue(GithubFile.objects.filter(data_source=self.data_source, path='new_file.py').exists())
        
        # Check that deleted file was removed
        self.assertFalse(GithubFile.objects.filter(data_source=self.data_source, path='deleted_file.py').exists())
        
        # Verify data source was marked as successfully processed
        self.assertEqual(self.data_source.status, DataSource.Status.SUCCESS)
        self.assertEqual(self.data_source.error, "")
        self.assertEqual(self.data_source.user_error, "")

    @patch('core.github.data_source_handler.clone_repository')
    @patch('core.github.data_source_handler.read_repository')
    def test_update_github_repositories_file_count_limit(self, mock_read_repository, mock_clone_repository):
        """
        Test when repository exceeds file count limit
        """
        # Set up mock for clone_repository
        mock_temp_dir = "/tmp/test_repo"
        mock_repo = MagicMock()
        mock_clone_repository.return_value = (mock_temp_dir, mock_repo)
        
        # Return a structure with too many files
        mock_read_repository.return_value = [
            {'path': f'file_{i}.py', 'content': f'# File {i}', 'size': 10}
            for i in range(1001)  # More than the limit of 1000
        ]
        
        # Mock system call to remove temp directory
        with patch('os.system'):
            # Run the task
            update_github_repositories()
        
        # Verify the data source was marked as failed with appropriate error
        self.data_source.refresh_from_db()
        self.assertEqual(self.data_source.status, DataSource.Status.FAIL)
        self.assertIn("exceeds the maximum file limit", self.data_source.user_error)
        self.assertIn("GithubRepoFileCountLimitError", self.data_source.error)

    @patch('core.github.data_source_handler.clone_repository')
    @patch('core.github.data_source_handler.read_repository')
    def test_update_github_repositories_size_limit(self, mock_read_repository, mock_clone_repository):
        """
        Test when repository exceeds size limit
        """
        # Set up mock for clone_repository
        mock_temp_dir = "/tmp/test_repo"
        mock_repo = MagicMock()
        mock_clone_repository.return_value = (mock_temp_dir, mock_repo)
        
        # Return a structure with files that exceed the size limit
        # 51MB total size (exceeds 50MB limit)
        mock_read_repository.return_value = [
            {'path': 'large_file.py', 'content': 'x' * 1024, 'size': 51 * 1024 * 1024}
        ]
        
        # Mock system call to remove temp directory
        with patch('os.system'):
            # Run the task
            update_github_repositories()
        
        # Verify the data source was marked as failed with appropriate error
        self.data_source.refresh_from_db()
        self.assertEqual(self.data_source.status, DataSource.Status.FAIL)
        self.assertIn("exceeds the maximum size limit", self.data_source.user_error)
        self.assertIn("GithubRepoSizeLimitError", self.data_source.error)

    @patch('core.github.data_source_handler.clone_repository')
    def test_update_github_repositories_invalid_repo(self, mock_clone_repository):
        """
        Test handling of invalid repository
        """
        # Make clone_repository raise an exception
        mock_clone_repository.side_effect = GithubInvalidRepoError("Repository doesn't exist or is private")
        
        # Run the task
        update_github_repositories()
        
        # Verify the data source was marked as failed with appropriate error
        self.data_source.refresh_from_db()
        self.assertEqual(self.data_source.status, DataSource.Status.FAIL)
        self.assertIn("repository doesn\'t exist or is private", self.data_source.user_error.lower())
        self.assertIn("GithubInvalidRepoError", self.data_source.error)

    @patch('core.github.data_source_handler.clone_repository')
    @patch('core.github.data_source_handler.read_repository')
    def test_update_github_repositories_general_exception(self, mock_read_repository, mock_clone_repository):
        """
        Test handling of general exceptions
        """
        # Set up mock for clone_repository
        mock_temp_dir = "/tmp/test_repo"
        mock_repo = MagicMock()
        mock_clone_repository.return_value = (mock_temp_dir, mock_repo)
        
        # Make read_repository raise a general exception
        mock_read_repository.side_effect = Exception("Unexpected error")
        
        # Mock system call to remove temp directory
        with patch('os.system'):
            # Run the task
            update_github_repositories()
        
        # Verify the data source was marked as failed with appropriate error
        self.data_source.refresh_from_db()
        self.assertEqual(self.data_source.status, DataSource.Status.FAIL)
        self.assertIn("Failed to index the repository", self.data_source.user_error)
        self.assertIn("Unexpected error", self.data_source.error)

    @patch('core.github.data_source_handler.clone_repository')
    @patch('core.github.data_source_handler.read_repository')
    def test_update_github_repositories_no_changes(self, mock_read_repository, mock_clone_repository):
        """
        Test when there are no changes to the repository
        """
        # Set up mock for clone_repository
        mock_temp_dir = "/tmp/test_repo"
        mock_repo = MagicMock()
        mock_clone_repository.return_value = (mock_temp_dir, mock_repo)
        
        # Return the same file structure as in the database (except the deleted file)
        mock_read_repository.return_value = [
            {
                'path': 'test_file.py',
                'content': 'def test_function():\n    return True',
                'size': 42
            }
        ]
        
        # Mock the git commit history with an old timestamp (older than the file's date_updated)
        mock_commit = MagicMock()
        old_timestamp = (timezone.now() - timedelta(days=2)).timestamp()
        mock_commit.committed_date = old_timestamp
        mock_repo.iter_commits.return_value = iter([mock_commit])
        
        # Mock system call to remove temp directory
        with patch('os.system'):
            # Run the task
            update_github_repositories()
        
        # Verify the data source status
        self.data_source.refresh_from_db()
        self.assertEqual(self.data_source.status, DataSource.Status.SUCCESS)
        
        # Verify no changes were made to the test_file.py
        updated_file = GithubFile.objects.get(data_source=self.data_source, path='test_file.py')
        self.assertEqual(updated_file.content, 'def test_function():\n    return True')
        self.assertEqual(updated_file.size, 42)
        
        # The deleted file should still be deleted
        self.assertFalse(GithubFile.objects.filter(data_source=self.data_source, path='deleted_file.py').exists())
