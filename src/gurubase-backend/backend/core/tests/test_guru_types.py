from django.test import TestCase
from django.contrib.auth import get_user_model
from core.utils import get_default_settings
from core.models import GuruType
from core.guru_types import get_guru_types, get_guru_type_object, get_guru_type_object_without_filters
from core.exceptions import GuruNotFoundError
from unittest.mock import patch, MagicMock
from django.db.models.signals import post_save
from core.signals import create_milvus_collection

User = get_user_model()

class GuruTypesTestCase(TestCase):
    @classmethod
    def setUpClass(cls):
        get_default_settings()
        super().setUpClass()
        # Disconnect the signal for all tests in this class
        post_save.disconnect(create_milvus_collection, sender=GuruType)

    @classmethod
    def tearDownClass(cls):
        # Reconnect the signal after all tests
        post_save.connect(create_milvus_collection, sender=GuruType)
        super().tearDownClass()

    def setUp(self):
        # Create test users
        self.admin_user = User.objects.create_superuser(
            name='admin',
            email='admin@example.com',
            password='password',
        )
        self.maintainer_user = User.objects.create_user(
            name='maintainer',
            email='maintainer@example.com',
            password='password',
        )
        self.non_maintainer_user = User.objects.create_user(
            name='non_maintainer',
            email='non_maintainer@example.com',
            password='password',
        )
        
        # Create test guru types with icon_urls
        self.public_active = GuruType.objects.create(
            slug='public-active',
            name='Public Active',
            active=True,
            private=False,
            icon_url='https://example.com/icon1.png'
        )
        self.public_inactive = GuruType.objects.create(
            slug='public-inactive',
            name='Public Inactive',
            active=False,
            private=False,
            icon_url='https://example.com/icon2.png'
        )
        self.private_active = GuruType.objects.create(
            slug='private-active',
            name='Private Active',
            active=True,
            private=True,
            icon_url='https://example.com/icon3.png'
        )
        self.private_inactive = GuruType.objects.create(
            slug='private-inactive',
            name='Private Inactive',
            active=False,
            private=True,
            icon_url='https://example.com/icon4.png'
        )
        
        # Add maintainer user as maintainer of private guru types
        self.private_active.maintainers.add(self.maintainer_user)
        self.private_inactive.maintainers.add(self.maintainer_user)

    def tearDown(self):
        pass

    @patch('core.guru_types.GuruTypeInternalSerializer')
    def test_get_guru_types_anonymous(self, mock_serializer):
        """Test get_guru_types for anonymous user"""
        # Setup mock serializer
        mock_serializer.return_value.data = [{'slug': 'public-active'}]
        
        guru_types = get_guru_types(only_active=True)
        self.assertEqual(len(guru_types), 1)
        self.assertEqual(guru_types[0]['slug'], 'public-active')

    @patch('core.guru_types.GuruTypeInternalSerializer')
    def test_get_guru_types_maintainer(self, mock_serializer):
        """Test get_guru_types for maintainer user"""
        # Setup mock serializer
        mock_serializer.return_value.data = [
            {'slug': 'public-active'},
            {'slug': 'private-active'}
        ]
        
        guru_types = get_guru_types(only_active=True, user=self.maintainer_user)
        self.assertEqual(len(guru_types), 2)
        slugs = [gt['slug'] for gt in guru_types]
        self.assertIn('public-active', slugs)
        self.assertIn('private-active', slugs)

    @patch('core.guru_types.GuruTypeInternalSerializer')
    def test_get_guru_types_non_maintainer(self, mock_serializer):
        """Test get_guru_types for non-maintainer user"""
        # Setup mock serializer
        mock_serializer.return_value.data = [{'slug': 'public-active'}]
        
        guru_types = get_guru_types(only_active=True, user=self.non_maintainer_user)
        self.assertEqual(len(guru_types), 1)
        self.assertEqual(guru_types[0]['slug'], 'public-active')

    @patch('core.guru_types.GuruTypeInternalSerializer')
    def test_get_guru_types_admin(self, mock_serializer):
        """Test get_guru_types for admin user"""
        # Setup mock serializer
        mock_serializer.return_value.data = [
            {'slug': 'public-active'},
            {'slug': 'private-active'}
        ]
        
        guru_types = get_guru_types(only_active=True, user=self.admin_user)
        self.assertEqual(len(guru_types), 2)
        slugs = [gt['slug'] for gt in guru_types]
        self.assertIn('public-active', slugs)
        self.assertIn('private-active', slugs)

    @patch('core.guru_types.GuruTypeInternalSerializer')
    def test_get_guru_types_inactive_maintainer(self, mock_serializer):
        """Test get_guru_types with only_active=False for maintainer"""
        # Setup mock serializer
        mock_serializer.return_value.data = [
            {'slug': 'public-active'},
            {'slug': 'public-inactive'},
            {'slug': 'private-active'},
            {'slug': 'private-inactive'}
        ]
        
        guru_types = get_guru_types(only_active=False, user=self.maintainer_user)
        self.assertEqual(len(guru_types), 4)
        slugs = [gt['slug'] for gt in guru_types]
        self.assertIn('public-active', slugs)
        self.assertIn('public-inactive', slugs)
        self.assertIn('private-active', slugs)
        self.assertIn('private-inactive', slugs)

    @patch('core.guru_types.GuruTypeInternalSerializer')
    def test_get_guru_types_inactive_non_maintainer(self, mock_serializer):
        """Test get_guru_types with only_active=False for non-maintainer"""
        # Setup mock serializer
        mock_serializer.return_value.data = [
            {'slug': 'public-active'},
            {'slug': 'public-inactive'}
        ]
        
        guru_types = get_guru_types(only_active=False, user=self.non_maintainer_user)
        self.assertEqual(len(guru_types), 2)
        slugs = [gt['slug'] for gt in guru_types]
        self.assertIn('public-active', slugs)
        self.assertIn('public-inactive', slugs)
        self.assertNotIn('private-active', slugs)
        self.assertNotIn('private-inactive', slugs)

    @patch('core.guru_types.GuruTypeInternalSerializer')
    def test_get_guru_types_inactive_admin(self, mock_serializer):
        """Test get_guru_types with only_active=False for admin"""
        # Setup mock serializer
        mock_serializer.return_value.data = [
            {'slug': 'public-active'},
            {'slug': 'public-inactive'},
            {'slug': 'private-active'},
            {'slug': 'private-inactive'}
        ]
        
        guru_types = get_guru_types(only_active=False, user=self.admin_user)
        self.assertEqual(len(guru_types), 4)
        slugs = [gt['slug'] for gt in guru_types]
        self.assertIn('public-active', slugs)
        self.assertIn('public-inactive', slugs)
        self.assertIn('private-active', slugs)
        self.assertIn('private-inactive', slugs)

    def test_get_guru_type_object_anonymous(self):
        """Test get_guru_type_object for anonymous user"""
        # Should be able to access public active guru
        guru = get_guru_type_object('public-active', only_active=True)
        self.assertEqual(guru.slug, 'public-active')
        
    def test_get_guru_type_object_maintainer(self):
        """Test get_guru_type_object for maintainer user"""
        # Should be able to access public active guru
        guru = get_guru_type_object('public-active', only_active=True, user=self.maintainer_user)
        self.assertEqual(guru.slug, 'public-active')
        
        # Should be able to access private guru they maintain
        guru = get_guru_type_object('private-active', only_active=True, user=self.maintainer_user)
        self.assertEqual(guru.slug, 'private-active')
        
    def test_get_guru_type_object_non_maintainer(self):
        """Test get_guru_type_object for non-maintainer user"""
        # Should be able to access public active guru
        guru = get_guru_type_object('public-active', only_active=True, user=self.non_maintainer_user)
        self.assertEqual(guru.slug, 'public-active')
        
    def test_get_guru_type_object_admin(self):
        """Test get_guru_type_object for admin user"""
        # Admin should be able to access any active guru
        guru = get_guru_type_object('private-active', only_active=True, user=self.admin_user)
        self.assertEqual(guru.slug, 'private-active')

    def test_get_guru_type_object_without_filters(self):
        """Test get_guru_type_object_without_filters"""
        # Should be able to access any guru regardless of status
        guru = get_guru_type_object_without_filters('public-active')
        self.assertEqual(guru.slug, 'public-active')
        
        guru = get_guru_type_object_without_filters('private-inactive')
        self.assertEqual(guru.slug, 'private-inactive')
        
        # Should raise error for non-existent guru
        with self.assertRaises(GuruNotFoundError):
            get_guru_type_object_without_filters('non-existent')
