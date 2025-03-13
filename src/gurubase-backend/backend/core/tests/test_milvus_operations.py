from django.test import TestCase
from unittest.mock import patch, MagicMock, call
from django.contrib.auth import get_user_model
from core.utils import get_default_embedding_dimensions
from core.models import GuruType, DataSource, GithubFile
from django.conf import settings
import os

User = get_user_model()

class MilvusOperationsTests(TestCase):
    def setUp(self):
        # Create a test user
        self.user = User.objects.create(email='testuser@getanteon.com')
        
        # Create a test guru type
        self.guru_type = GuruType.objects.create(
            name='Test Guru',
            slug='test-guru',
            domain_knowledge='Test domain knowledge',
            milvus_collection_name='test_guru_collection'
        )
        
        # Create a test data source
        self.data_source = DataSource.objects.create(
            type=DataSource.Type.WEBSITE,
            title='Test Website',
            guru_type=self.guru_type,
            content='Test content for Website',
            url='https://example.com/test'
        )
        
        # Create a test GitHub data source
        self.github_data_source = DataSource.objects.create(
            type=DataSource.Type.GITHUB_REPO,
            title='Test GitHub Repo',
            guru_type=self.guru_type,
            url='https://github.com/test/repo',
            default_branch='main'
        )
        
        # Create a test GitHub file
        self.github_file = GithubFile.objects.create(
            data_source=self.github_data_source,
            path='test/file.py',
            link='https://github.com/test/repo/blob/main/test/file.py',
            content='def test_function():\n    return "Hello, World!"',
            size=100
        )

    @patch('core.utils.embed_texts')
    @patch('core.milvus_utils.insert_vectors')
    def test_datasource_write_to_milvus(self, mock_insert_vectors, mock_embed_texts):
        """Test that DataSource.write_to_milvus correctly updates doc_ids and in_milvus flag"""
        # Mock the embedding and vector insertion
        mock_embed_texts.return_value = [[0.1] * get_default_embedding_dimensions()]
        mock_insert_vectors.return_value = ['doc_id_1', 'doc_id_2']
        
        # Call the method
        self.data_source.write_to_milvus()
        
        # Check that the mocks were called correctly
        mock_embed_texts.assert_called_once()
        mock_insert_vectors.assert_called_once()
        
        # Refresh from database
        self.data_source.refresh_from_db()
        
        # Check that the model was updated correctly
        self.assertTrue(self.data_source.in_milvus)
        self.assertEqual(self.data_source.doc_ids, ['doc_id_1', 'doc_id_2'])
        self.assertEqual(self.data_source.status, DataSource.Status.SUCCESS)
        self.assertIsNotNone(self.data_source.last_successful_index_date)

    @patch('core.milvus_utils.delete_vectors')
    def test_datasource_delete_from_milvus(self, mock_delete_vectors):
        """Test that DataSource.delete_from_milvus correctly clears doc_ids and in_milvus flag"""
        # Set up the data source with mock doc_ids
        self.data_source.doc_ids = ['doc_id_1', 'doc_id_2']
        self.data_source.in_milvus = True
        self.data_source.save()
        
        # Call the method
        self.data_source.delete_from_milvus()
        
        # Check that the mock was called correctly
        mock_delete_vectors.assert_called_once_with(
            self.guru_type.milvus_collection_name, 
            ['doc_id_1', 'doc_id_2']
        )
        
        # Refresh from database
        self.data_source.refresh_from_db()
        
        # Check that the model was updated correctly
        self.assertFalse(self.data_source.in_milvus)
        self.assertEqual(self.data_source.doc_ids, [])

    @patch('core.utils.embed_texts')
    @patch('core.milvus_utils.insert_vectors')
    def test_github_file_write_to_milvus(self, mock_insert_vectors, mock_embed_texts):
        """Test that GithubFile.write_to_milvus correctly updates doc_ids and in_milvus flag"""
        # Mock the embedding and vector insertion
        mock_embed_texts.return_value = [[0.1] * get_default_embedding_dimensions()]
        mock_insert_vectors.return_value = ['doc_id_1', 'doc_id_2']
        
        # Call the method
        self.github_file.write_to_milvus()
        
        # Check that the mocks were called correctly
        mock_embed_texts.assert_called_once()
        mock_insert_vectors.assert_called_once()
        
        # Refresh from database
        self.github_file.refresh_from_db()
        
        # Check that the model was updated correctly
        self.assertTrue(self.github_file.in_milvus)
        self.assertEqual(self.github_file.doc_ids, ['doc_id_1', 'doc_id_2'])

    @patch('core.milvus_utils.delete_vectors')
    def test_github_file_delete_from_milvus(self, mock_delete_vectors):
        """Test that GithubFile.delete_from_milvus correctly clears doc_ids and in_milvus flag"""
        # Set up the GitHub file with mock doc_ids
        self.github_file.doc_ids = ['doc_id_1', 'doc_id_2']
        self.github_file.in_milvus = True
        self.github_file.save()
        
        # Set up the data source with the same doc_ids
        self.github_data_source.doc_ids = ['doc_id_1', 'doc_id_2']
        self.github_data_source.save()
        
        # Call the method
        self.github_file.delete_from_milvus()
        
        # Check that the mock was called correctly
        mock_delete_vectors.assert_called_once_with(
            settings.GITHUB_REPO_CODE_COLLECTION_NAME, 
            ['doc_id_1', 'doc_id_2']
        )
        
        # Refresh from database
        self.github_file.refresh_from_db()
        self.github_data_source.refresh_from_db()
        
        # Check that the models were updated correctly
        self.assertFalse(self.github_file.in_milvus)
        self.assertEqual(self.github_file.doc_ids, [])
        self.assertEqual(self.github_data_source.doc_ids, [])

    @patch('core.utils.embed_texts')
    @patch('core.milvus_utils.insert_vectors')
    def test_github_datasource_write_to_milvus(self, mock_insert_vectors, mock_embed_texts):
        """Test that GitHub DataSource.write_to_milvus correctly updates doc_ids and in_milvus flag for all files"""
        # Mock the embedding and vector insertion
        mock_embed_texts.return_value = [[0.1] * get_default_embedding_dimensions()] * 2
        mock_insert_vectors.return_value = ['doc_id_1', 'doc_id_2']
        
        # Create a second GitHub file
        github_file2 = GithubFile.objects.create(
            data_source=self.github_data_source,
            path='test/file2.py',
            link='https://github.com/test/repo/blob/main/test/file2.py',
            content='def another_function():\n    return "Hello again!"',
            size=120
        )
        
        # Call the method
        self.github_data_source.in_milvus = False
        self.github_data_source.write_to_milvus()
        
        # Check that the mocks were called correctly
        self.assertEqual(mock_embed_texts.call_count, 1)
        self.assertEqual(mock_insert_vectors.call_count, 1)
        
        # Refresh from database
        self.github_data_source.refresh_from_db()
        self.github_file.refresh_from_db()
        github_file2.refresh_from_db()
        
        # Check that the models were updated correctly
        self.assertTrue(self.github_data_source.in_milvus)
        self.assertTrue(self.github_file.in_milvus)
        self.assertTrue(github_file2.in_milvus)
        self.assertEqual(len(self.github_data_source.doc_ids), 2)  # 2 doc_ids per file
        self.assertEqual(self.github_file.doc_ids, ['doc_id_1'])
        self.assertEqual(github_file2.doc_ids, ['doc_id_2'])

    @patch('core.milvus_utils.delete_vectors')
    def test_github_datasource_delete_from_milvus(self, mock_delete_vectors):
        """Test that GitHub DataSource.delete_from_milvus correctly deletes all files"""
        # Set up the GitHub file with mock doc_ids
        self.github_file.doc_ids = ['doc_id_1', 'doc_id_2']
        self.github_file.in_milvus = True
        self.github_file.save()
        
        # Set up the data source with the same doc_ids
        self.github_data_source.doc_ids = ['doc_id_1', 'doc_id_2']
        self.github_data_source.in_milvus = True
        self.github_data_source.save()
        
        # Call the method
        self.github_data_source.delete_from_milvus()
        
        # Check that the mock was called correctly
        mock_delete_vectors.assert_has_calls([
            call(
                self.guru_type.milvus_collection_name, 
                ['doc_id_1', 'doc_id_2']
            ),
            call(
                settings.GITHUB_REPO_CODE_COLLECTION_NAME, 
                ['doc_id_1', 'doc_id_2']
            )
        ])
        
        # Refresh from database
        self.github_data_source.refresh_from_db()
        
        # Check that the model was updated correctly
        self.assertFalse(self.github_data_source.in_milvus)
        self.assertEqual(self.github_data_source.doc_ids, [])
        
        # Check that all GitHub files were deleted
        self.assertEqual(GithubFile.objects.filter(data_source=self.github_data_source).count(), 0)

    @patch('core.milvus_utils.delete_vectors')
    def test_clear_github_file_signal(self, mock_delete_vectors):
        """Test that the clear_github_file signal correctly calls delete_from_milvus"""
        # Set up the GitHub file with mock doc_ids
        self.github_file.doc_ids = ['doc_id_1', 'doc_id_2']
        self.github_file.in_milvus = True
        self.github_file.save()
        
        # Set up the data source with the same doc_ids
        self.github_data_source.doc_ids = ['doc_id_1', 'doc_id_2']
        self.github_data_source.save()
        
        # Delete the GitHub file (should trigger the signal)
        self.github_file.delete()
        
        # Check that the mock was called correctly
        mock_delete_vectors.assert_called_once_with(
            settings.GITHUB_REPO_CODE_COLLECTION_NAME, 
            ['doc_id_1', 'doc_id_2']
        )
        
        # Refresh from database
        self.github_data_source.refresh_from_db()
        
        # Check that the data source was updated correctly
        self.assertEqual(self.github_data_source.doc_ids, [])

    @patch('core.milvus_utils.delete_vectors')
    def test_clear_data_source_signal(self, mock_delete_vectors):
        """Test that the clear_data_source signal correctly calls delete_from_milvus"""
        # Set up the data source with mock doc_ids
        self.data_source.doc_ids = ['doc_id_1', 'doc_id_2']
        self.data_source.in_milvus = True
        self.data_source.save()
        
        # Delete the data source (should trigger the signal)
        self.data_source.delete()
        
        # Check that the mock was called correctly
        mock_delete_vectors.assert_called_once_with(
            self.guru_type.milvus_collection_name, 
            ['doc_id_1', 'doc_id_2']
        )

    @patch('core.milvus_utils.delete_vectors')
    @patch('core.milvus_utils.insert_vectors')
    @patch('core.milvus_utils.fetch_vectors')
    def test_update_data_source_in_milvus_signal(self, mock_fetch_vectors, mock_insert_vectors, mock_delete_vectors):
        """Test that the update_data_source_in_milvus signal correctly calls delete_from_milvus when title changes"""
        # Set up the data source with mock doc_ids
        self.data_source.doc_ids = ['doc_id_1', 'doc_id_2']
        self.data_source.in_milvus = True
        self.data_source.save()

        mock_fetch_vectors.return_value = [
            {'id': 'doc_id_1', 'metadata': {'title': 'Old Title'}},
            {'id': 'doc_id_2', 'metadata': {'title': 'Old Title'}}
        ]
        
        # Change the title and save (should trigger the signal)
        self.data_source.title = 'Updated Title'
        self.data_source.save()
        
        # Check that the mock was called correctly
        mock_delete_vectors.assert_called_once_with(
            self.guru_type.milvus_collection_name, 
            ['doc_id_1', 'doc_id_2']
        ) 
        mock_insert_vectors.assert_called_once_with(
            self.guru_type.milvus_collection_name, 
            [{'metadata': {'title': 'Updated Title'}}, {'metadata': {'title': 'Updated Title'}}]
        ) 

    