from django.test import TestCase
from django.core.exceptions import ValidationError
from core.models import GuruType, DataSource
from django.contrib.auth import get_user_model

User = get_user_model()

class GuruTypeGithubTests(TestCase):
    def setUp(self):
        self.user = User.objects.create(email='testuser@getanteon.com')
        self.valid_guru_type_data = {
            'name': 'Test Guru',
            'slug': 'test-guru',
            'domain_knowledge': 'Test domain knowledge'
        }
        self.valid_github_url = 'https://github.com/username/repo'
        
    def create_guru_type(self, **kwargs):
        data = self.valid_guru_type_data.copy()
        data.update(kwargs)
        return GuruType.objects.create(**data)

    def test_initial_state(self):
        """Test initial state with no GitHub settings"""
        guru_type = self.create_guru_type()
        self.assertFalse(guru_type.index_repo)
        self.assertEqual(guru_type.github_repo, '')
        self.assertEqual(DataSource.objects.count(), 0)

    def test_url_validation(self):
        """Test GitHub URL validation"""
        invalid_urls = [
            'not-a-url',
            'http://not-github.com/user/repo',
            'https://github.com',  # Missing repository path
            'ftp://github.com/user/repo',  # Invalid protocol
        ]
        
        for url in invalid_urls:
            with self.assertRaises(ValidationError):
                self.create_guru_type(github_repo=url)

    def test_add_url_without_indexing(self):
        """Test adding GitHub URL without enabling indexing"""
        guru_type = self.create_guru_type(
            github_repo=self.valid_github_url,
            index_repo=False
        )
        self.assertEqual(guru_type.github_repo, self.valid_github_url)
        self.assertEqual(DataSource.objects.count(), 0)

    def test_add_url_and_enable_indexing(self):
        """Test adding URL and enabling indexing"""
        guru_type = self.create_guru_type(
            github_repo=self.valid_github_url,
            index_repo=True
        )
        self.assertEqual(DataSource.objects.count(), 1)
        datasource = DataSource.objects.first()
        self.assertEqual(datasource.url, self.valid_github_url)
        self.assertEqual(datasource.type, DataSource.Type.GITHUB_REPO)
        self.assertEqual(datasource.status, DataSource.Status.NOT_PROCESSED)

    def test_update_url_while_indexed(self):
        """Test updating URL while indexing is enabled"""
        guru_type = self.create_guru_type(
            github_repo=self.valid_github_url,
            index_repo=True
        )
        new_url = 'https://github.com/username/another-repo'
        
        # Update URL
        guru_type.github_repo = new_url
        guru_type.save()
        
        self.assertEqual(DataSource.objects.count(), 1)
        datasource = DataSource.objects.first()
        self.assertEqual(datasource.url, new_url)

    def test_disable_indexing(self):
        """Test disabling indexing"""
        guru_type = self.create_guru_type(
            github_repo=self.valid_github_url,
            index_repo=True
        )
        self.assertEqual(DataSource.objects.count(), 1)
        
        # Disable indexing
        guru_type.index_repo = False
        guru_type.save()
        
        self.assertEqual(DataSource.objects.count(), 0)

    def test_remove_url_while_indexed(self):
        """Test removing URL while indexed"""
        guru_type = self.create_guru_type(
            github_repo=self.valid_github_url,
            index_repo=True
        )
        self.assertEqual(DataSource.objects.count(), 1)
        
        # Remove URL
        guru_type.github_repo = ''
        guru_type.index_repo = False
        guru_type.save()
        
        self.assertEqual(DataSource.objects.count(), 0)

    def test_multiple_updates(self):
        """Test multiple sequential updates"""
        guru_type = self.create_guru_type()
        
        # Add URL without indexing
        guru_type.github_repo = self.valid_github_url
        guru_type.save()
        self.assertEqual(DataSource.objects.count(), 0)
        
        # Enable indexing
        guru_type.index_repo = True
        guru_type.save()
        self.assertEqual(DataSource.objects.count(), 1)
        
        # Update URL
        new_url = 'https://github.com/username/another-repo'
        guru_type.github_repo = new_url
        guru_type.save()
        self.assertEqual(DataSource.objects.count(), 1)
        self.assertEqual(DataSource.objects.first().url, new_url)
        
        # Disable indexing
        guru_type.index_repo = False
        guru_type.save()
        self.assertEqual(DataSource.objects.count(), 0)

    def test_concurrent_url_and_index_changes(self):
        """Test changing URL and index status simultaneously"""
        guru_type = self.create_guru_type(
            github_repo=self.valid_github_url,
            index_repo=True
        )
        new_url = 'https://github.com/username/another-repo'
        
        # Update both fields
        guru_type.github_repo = new_url
        guru_type.index_repo = False
        guru_type.save()
        
        self.assertEqual(DataSource.objects.count(), 0)

    def test_reactivate_indexing(self):
        """Test re-enabling indexing after it was disabled"""
        guru_type = self.create_guru_type(
            github_repo=self.valid_github_url,
            index_repo=True
        )
        
        # Disable indexing
        guru_type.index_repo = False
        guru_type.save()
        self.assertEqual(DataSource.objects.count(), 0)
        
        # Re-enable indexing
        guru_type.index_repo = True
        guru_type.save()
        self.assertEqual(DataSource.objects.count(), 1)
        self.assertEqual(DataSource.objects.first().url, self.valid_github_url)

    def test_unique_datasource_constraint(self):
        """Test that only one DataSource is created per GuruType"""
        guru_type = self.create_guru_type(
            github_repo=self.valid_github_url,
            index_repo=True
        )
        self.assertEqual(DataSource.objects.count(), 1)

        new_url = self.valid_github_url + '/2'
        
        # Try to create another DataSource manually
        with self.assertRaises(Exception):
            DataSource.objects.create(
                guru_type=guru_type,
                type=DataSource.Type.GITHUB_REPO,
                url=new_url
            ) 