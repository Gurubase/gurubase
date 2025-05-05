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
            'domain_knowledge': 'Test domain knowledge',
            'github_repo_count_limit': 2
        }
        self.valid_github_urls = [
            'https://github.com/username/repo1',
            'https://github.com/username/repo2'
        ]
        
    def create_guru_type(self, **kwargs):
        data = self.valid_guru_type_data.copy()
        data.update(kwargs)
        return GuruType.objects.create(**data)

    def test_initial_state(self):
        """Test initial state with no GitHub settings"""
        guru_type = self.create_guru_type()
        self.assertTrue(guru_type.index_repo)
        self.assertEqual(guru_type.github_repos, [])
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
                self.create_guru_type(github_repos=[url])

    def test_add_urls_without_indexing(self):
        """Test adding GitHub URLs without enabling indexing"""
        guru_type = self.create_guru_type(
            github_repos=self.valid_github_urls,
            index_repo=False
        )
        self.assertEqual(sorted(guru_type.github_repos), sorted(self.valid_github_urls))
        self.assertEqual(DataSource.objects.count(), 0)

    def test_add_urls_and_enable_indexing(self):
        """Test adding URLs and enabling indexing"""
        guru_type = self.create_guru_type(
            github_repos=self.valid_github_urls,
            index_repo=True
        )
        self.assertEqual(DataSource.objects.count(), 2)
        for i, url in enumerate(self.valid_github_urls):
            datasource = DataSource.objects.get(url=url)
            self.assertEqual(datasource.type, DataSource.Type.GITHUB_REPO)
            self.assertEqual(datasource.status, DataSource.Status.NOT_PROCESSED)

    def test_update_urls_while_indexed(self):
        """Test updating URLs while indexing is enabled"""
        guru_type = self.create_guru_type(
            github_repos=self.valid_github_urls[:1],  # Start with one repo
            index_repo=True
        )
        self.assertEqual(DataSource.objects.count(), 1)
        
        # Update URLs to include both repos
        guru_type.github_repos = self.valid_github_urls
        guru_type.save()
        
        self.assertEqual(DataSource.objects.count(), 2)
        for url in self.valid_github_urls:
            datasource = DataSource.objects.get(url=url)
            self.assertEqual(datasource.type, DataSource.Type.GITHUB_REPO)

    def test_disable_indexing(self):
        """Test disabling indexing"""
        guru_type = self.create_guru_type(
            github_repos=self.valid_github_urls,
            index_repo=True
        )
        self.assertEqual(DataSource.objects.count(), 2)
        
        # Disable indexing
        guru_type.index_repo = False
        guru_type.save()
        
        self.assertEqual(DataSource.objects.count(), 0)

    def test_remove_urls_while_indexed(self):
        """Test removing URLs while indexed"""
        guru_type = self.create_guru_type(
            github_repos=self.valid_github_urls,
            index_repo=True
        )
        self.assertEqual(DataSource.objects.count(), 2)
        
        # Remove URLs
        guru_type.github_repos = []
        guru_type.index_repo = False
        guru_type.save()
        
        self.assertEqual(DataSource.objects.count(), 0)

    def test_multiple_updates(self):
        """Test multiple sequential updates"""
        guru_type = self.create_guru_type()
        
        # Add first URL
        guru_type.github_repos = [self.valid_github_urls[0]]
        guru_type.save()
        self.assertEqual(DataSource.objects.count(), 1)
        
        # Add second URL
        guru_type.github_repos = self.valid_github_urls
        guru_type.save()
        self.assertEqual(DataSource.objects.count(), 2)
        
        # Remove first URL
        guru_type.github_repos = [self.valid_github_urls[1]]
        guru_type.save()
        self.assertEqual(DataSource.objects.count(), 1)
        self.assertEqual(DataSource.objects.first().url, self.valid_github_urls[1])
        
        # Disable indexing
        guru_type.index_repo = False
        guru_type.save()
        self.assertEqual(DataSource.objects.count(), 0)

    def test_concurrent_url_and_index_changes(self):
        """Test changing URLs and index status simultaneously"""
        guru_type = self.create_guru_type(
            github_repos=self.valid_github_urls,
            index_repo=True
        )
        new_url = 'https://github.com/username/another-repo'
        
        # Update both fields
        guru_type.github_repos = [new_url]
        guru_type.index_repo = False
        guru_type.save()
        
        self.assertEqual(DataSource.objects.count(), 0)

    def test_reactivate_indexing(self):
        """Test re-enabling indexing after it was disabled"""
        guru_type = self.create_guru_type(
            github_repos=self.valid_github_urls,
            index_repo=True
        )
        
        # Disable indexing
        guru_type.index_repo = False
        guru_type.save()
        self.assertEqual(DataSource.objects.count(), 0)
        
        # Re-enable indexing
        guru_type.index_repo = True
        guru_type.save()
        self.assertEqual(DataSource.objects.count(), 2)
        for url in self.valid_github_urls:
            self.assertTrue(DataSource.objects.filter(url=url).exists())

    def test_repo_limit(self):
        """Test repository count limit"""
        guru_type = self.create_guru_type(
            github_repos=self.valid_github_urls[:1],
            index_repo=True,
            github_repo_count_limit=1  # Set limit to 1
        )
        
        # Try to add a third repository
        new_url = 'https://github.com/username/repo3'
        guru_type.github_repos.append(new_url)
        
        with self.assertRaises(Exception):
            guru_type.save() 

    def test_repo_limit_with_multiple_urls(self):
        """Test repository count limit with multiple URLs"""
        with self.assertRaises(Exception):
            guru_type = self.create_guru_type(
                github_repos=self.valid_github_urls,
                index_repo=True,
                github_repo_count_limit=1  # Set limit to 1
            )
