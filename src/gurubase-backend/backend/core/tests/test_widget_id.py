from django.test import TestCase
from django.core.exceptions import ValidationError
from core.models import GuruType, WidgetId
import secrets


class WidgetIdTests(TestCase):
    def setUp(self):
        # Mock the secrets.token_urlsafe to return a predictable value for testing
        self.original_token_urlsafe = secrets.token_urlsafe
        secrets.token_urlsafe = lambda x: "test_widget_key"
        
        # Create a test guru type
        self.guru_type = GuruType.objects.create(
            slug="test-guru",
            name="Test Guru",
            domain_knowledge="Test domain knowledge",
            custom=True,
            active=True
        )
    
    def tearDown(self):
        # Restore the original token_urlsafe function
        secrets.token_urlsafe = self.original_token_urlsafe
    
    def test_generate_widget_id_standard_url(self):
        """Test generating a widget ID with a standard URL."""
        domain_url = "https://example.com"
        key = self.guru_type.generate_widget_id(domain_url)
        
        self.assertEqual(key, "test_widget_key")
        
        # Verify the widget ID was created correctly
        widget = WidgetId.objects.get(key=key)
        self.assertEqual(widget.domain_url, domain_url)
        self.assertEqual(widget.guru_type, self.guru_type)
        self.assertFalse(widget.is_wildcard)
    
    def test_generate_widget_id_wildcard_universal(self):
        """Test generating a widget ID with a universal wildcard."""
        domain_url = "*"
        key = self.guru_type.generate_widget_id(domain_url)
        
        # Verify the widget ID was created correctly
        widget = WidgetId.objects.get(key=key)
        self.assertEqual(widget.domain_url, domain_url)
        self.assertTrue(widget.is_wildcard)
    
    def test_generate_widget_id_wildcard_port(self):
        """Test generating a widget ID with a port wildcard."""
        domain_url = "http://localhost:*"
        key = self.guru_type.generate_widget_id(domain_url)
        
        # Verify the widget ID was created correctly
        widget = WidgetId.objects.get(key=key)
        self.assertEqual(widget.domain_url, domain_url)
        self.assertTrue(widget.is_wildcard)
    
    def test_generate_widget_id_wildcard_subdomain(self):
        """Test generating a widget ID with a subdomain wildcard."""
        domain_url = "https://*.example.com"
        key = self.guru_type.generate_widget_id(domain_url)
        
        # Verify the widget ID was created correctly
        widget = WidgetId.objects.get(key=key)
        self.assertEqual(widget.domain_url, domain_url)
        self.assertTrue(widget.is_wildcard)
    
    def test_generate_widget_id_wildcard_prefix(self):
        """Test generating a widget ID with a prefix wildcard."""
        domain_url = "*example.com"
        key = self.guru_type.generate_widget_id(domain_url)
        
        # Verify the widget ID was created correctly
        widget = WidgetId.objects.get(key=key)
        self.assertEqual(widget.domain_url, domain_url)
        self.assertTrue(widget.is_wildcard)
    
    def test_generate_widget_id_wildcard_suffix(self):
        """Test generating a widget ID with a suffix wildcard."""
        domain_url = "example*"
        key = self.guru_type.generate_widget_id(domain_url)
        
        # Verify the widget ID was created correctly
        widget = WidgetId.objects.get(key=key)
        self.assertEqual(widget.domain_url, domain_url)
        self.assertTrue(widget.is_wildcard)
    
    def test_generate_widget_id_wildcard_contains(self):
        """Test generating a widget ID with a contains wildcard."""
        domain_url = "*example*"
        key = self.guru_type.generate_widget_id(domain_url)
        
        # Verify the widget ID was created correctly
        widget = WidgetId.objects.get(key=key)
        self.assertEqual(widget.domain_url, domain_url)
        self.assertTrue(widget.is_wildcard)
    
    def test_generate_widget_id_wildcard_multiple_asterisks(self):
        """Test generating a widget ID with multiple asterisks."""
        domain_url = "*.example.*.com"
        key = self.guru_type.generate_widget_id(domain_url)
        
        # Verify the widget ID was created correctly
        widget = WidgetId.objects.get(key=key)
        self.assertEqual(widget.domain_url, domain_url)
        self.assertTrue(widget.is_wildcard)
    
    def test_generate_widget_id_wildcard_complex_pattern(self):
        """Test generating a widget ID with a complex wildcard pattern."""
        domain_url = "https://*-app.example.com/*/path"
        key = self.guru_type.generate_widget_id(domain_url)
        
        # Verify the widget ID was created correctly
        widget = WidgetId.objects.get(key=key)
        self.assertEqual(widget.domain_url, domain_url)
        self.assertTrue(widget.is_wildcard)
    
    def test_generate_widget_id_empty_domain(self):
        """Test generating a widget ID with an empty domain."""
        domain_url = ""
        key = self.guru_type.generate_widget_id(domain_url)
        
        # Verify the widget ID was created correctly
        widget = WidgetId.objects.get(key=key)
        self.assertEqual(widget.domain_url, domain_url)
        self.assertFalse(widget.is_wildcard)
    
    def test_generate_widget_id_invalid_url(self):
        """Test generating a widget ID with an invalid URL."""
        with self.assertRaises(ValidationError):
            self.guru_type.generate_widget_id("not-a-valid-url")
    
    def test_generate_widget_id_duplicate(self):
        """Test that generating a duplicate widget ID raises an error."""
        domain_url = "https://example.com"
        self.guru_type.generate_widget_id(domain_url)
        
        # Try to create another widget ID with the same domain URL
        with self.assertRaises(ValidationError):
            self.guru_type.generate_widget_id(domain_url)
    
    def test_generate_widget_id_trailing_slash(self):
        """Test that trailing slashes are removed from domain URLs."""
        domain_url = "https://example.com/"
        key = self.guru_type.generate_widget_id(domain_url)
        
        # Verify the widget ID was created correctly
        widget = WidgetId.objects.get(key=key)
        self.assertEqual(widget.domain_url, "https://example.com")


class DomainMatchesPatternTests(TestCase):
    def test_exact_match(self):
        """Test exact domain matching."""
        self.assertTrue(WidgetId.domain_matches_pattern(
            "https://example.com", "https://example.com"))
        self.assertFalse(WidgetId.domain_matches_pattern(
            "https://example.com", "https://other.com"))
    
    def test_universal_wildcard(self):
        """Test universal wildcard matching."""
        self.assertTrue(WidgetId.domain_matches_pattern(
            "https://example.com", "*"))
        self.assertTrue(WidgetId.domain_matches_pattern(
            "http://localhost:3000", "*"))
    
    def test_port_wildcard(self):
        """Test port wildcard matching."""
        self.assertTrue(WidgetId.domain_matches_pattern(
            "http://localhost:3000", "http://localhost:*"))
        self.assertTrue(WidgetId.domain_matches_pattern(
            "http://localhost:8080", "http://localhost:*"))
        self.assertFalse(WidgetId.domain_matches_pattern(
            "https://localhost:3000", "http://localhost:*"))
    
    def test_subdomain_wildcard(self):
        """Test subdomain wildcard matching."""
        self.assertTrue(WidgetId.domain_matches_pattern(
            "https://app.example.com", "https://*.example.com"))
        self.assertTrue(WidgetId.domain_matches_pattern(
            "https://api.example.com", "https://*.example.com"))
        self.assertFalse(WidgetId.domain_matches_pattern(
            "http://app.example.com", "https://*.example.com"))
        self.assertFalse(WidgetId.domain_matches_pattern(
            "https://app.other.com", "https://*.example.com"))
    
    def test_general_wildcard(self):
        """Test general wildcard matching."""
        # Test prefix wildcard
        self.assertTrue(WidgetId.domain_matches_pattern(
            "example.com", "*example.com"))
        self.assertTrue(WidgetId.domain_matches_pattern(
            "test.example.com", "*example.com"))
        self.assertFalse(WidgetId.domain_matches_pattern(
            "example.org", "*example.com"))
        
        # Test suffix wildcard
        self.assertTrue(WidgetId.domain_matches_pattern(
            "example.com", "example*"))
        self.assertTrue(WidgetId.domain_matches_pattern(
            "example.org", "example*"))
        self.assertFalse(WidgetId.domain_matches_pattern(
            "test.com", "example*"))
        
        # Test contains wildcard
        self.assertTrue(WidgetId.domain_matches_pattern(
            "test.example.org", "*example*"))
        self.assertFalse(WidgetId.domain_matches_pattern(
            "test.org", "*example*"))
    
    def test_multiple_wildcards(self):
        """Test matching with multiple wildcards."""
        self.assertTrue(WidgetId.domain_matches_pattern(
            "test.example.com", "*.example.*"))
        self.assertTrue(WidgetId.domain_matches_pattern(
            "sub.example.org", "*.example.*"))
        self.assertFalse(WidgetId.domain_matches_pattern(
            "test.other.com", "*.example.*"))
    
    def test_complex_patterns(self):
        """Test matching with complex wildcard patterns."""
        self.assertTrue(WidgetId.domain_matches_pattern(
            "https://dev-app.example.com", "https://*-app.example.com"))
        self.assertTrue(WidgetId.domain_matches_pattern(
            "https://staging-app.example.com", "https://*-app.example.com"))
        self.assertFalse(WidgetId.domain_matches_pattern(
            "https://devapp.example.com", "https://*-app.example.com"))
    
    def test_edge_cases(self):
        """Test edge cases for wildcard matching."""
        # Empty strings
        self.assertTrue(WidgetId.domain_matches_pattern("", "*"))
        self.assertFalse(WidgetId.domain_matches_pattern("example.com", ""))
        
        # Pattern with just wildcards
        self.assertTrue(WidgetId.domain_matches_pattern("example.com", "*****"))
        
        # Pattern with special characters
        self.assertTrue(WidgetId.domain_matches_pattern(
            "example.com/path?query=value", "example.com*"))
    
    def test_case_sensitivity(self):
        """Test case sensitivity in domain matching."""
        self.assertTrue(WidgetId.domain_matches_pattern(
            "example.com", "EXAMPLE.COM"))
        self.assertTrue(WidgetId.domain_matches_pattern(
            "EXAMPLE.COM", "example.com"))
        self.assertTrue(WidgetId.domain_matches_pattern(
            "Example.Com", "*example*"))
    
    def test_ip_addresses(self):
        """Test matching with IP addresses."""
        self.assertTrue(WidgetId.domain_matches_pattern(
            "http://127.0.0.1:8000", "http://127.0.0.1:*"))
        self.assertTrue(WidgetId.domain_matches_pattern(
            "https://192.168.1.1", "https://192.168.*.*"))
        self.assertFalse(WidgetId.domain_matches_pattern(
            "https://192.168.2.1", "https://192.168.1.*")) 