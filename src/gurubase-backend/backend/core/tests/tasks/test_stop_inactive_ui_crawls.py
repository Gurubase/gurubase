from django.test import TestCase, override_settings
from django.utils.timezone import now
from datetime import timedelta
from core.models import CrawlState, GuruType
from core.tasks import stop_inactive_ui_crawls
from core.utils import get_default_settings


class TestStopInactiveUICrawls(TestCase):
    def setUp(self):
        """
        Set up test environment with necessary objects:
        1. Default settings
        2. GuruType for testing
        3. CrawlState objects representing various crawl statuses
        """
        # Initialize default settings
        get_default_settings()
        
        # Create test GuruType
        self.guru_type = GuruType.objects.create(
            slug="test-guru",
            name="Test Guru",
            custom=True,
            active=True
        )
        
        # Current time for reference
        self.now = now()

        inactive_time = self.now - timedelta(seconds=30)
        active_time = self.now - timedelta(seconds=5)
        
        # Create an inactive UI crawl (last polled long ago)
        self.inactive_crawl = CrawlState.objects.create(
            url="https://inactive.example.com",
            guru_type=self.guru_type,
            status=CrawlState.Status.RUNNING,
            start_time=self.now - timedelta(minutes=5),
            source=CrawlState.Source.UI,
        )
        self.inactive_crawl.last_polled_at = inactive_time # Polled 30 seconds ago
        self.inactive_crawl.save()
        
        # Create a recently polled UI crawl (active)
        self.active_crawl = CrawlState.objects.create(
            url="https://active.example.com",
            guru_type=self.guru_type,
            status=CrawlState.Status.RUNNING,
            start_time=self.now - timedelta(minutes=5),
            source=CrawlState.Source.UI,
        )
        self.active_crawl.last_polled_at = active_time # Polled 5 seconds ago
        self.active_crawl.save()
        
        # Create a non-UI crawl (API source)
        self.api_crawl = CrawlState.objects.create(
            url="https://api.example.com",
            guru_type=self.guru_type,
            status=CrawlState.Status.RUNNING,
            start_time=self.now - timedelta(minutes=5),
            source=CrawlState.Source.API,
        )
        self.api_crawl.last_polled_at = inactive_time # Polled 30 seconds ago
        self.api_crawl.save()
        
        # Create a UI crawl that's not running
        self.completed_crawl = CrawlState.objects.create(
            url="https://completed.example.com",
            guru_type=self.guru_type,
            status=CrawlState.Status.COMPLETED,
            start_time=self.now - timedelta(minutes=10),
            end_time=self.now - timedelta(minutes=5),
            source=CrawlState.Source.UI,
        )
        self.completed_crawl.last_polled_at = inactive_time # Polled 30 seconds ago
        self.completed_crawl.save()

    @override_settings(CRAWL_INACTIVE_THRESHOLD_SECONDS=20)
    def test_stop_inactive_ui_crawls(self):
        """
        Test that inactive UI crawls are stopped correctly.
        
        This test verifies that:
        1. UI crawls that haven't been polled for longer than the threshold are stopped
        2. Active UI crawls, non-UI crawls, and already completed crawls are not affected
        """
        # Run the task
        stop_inactive_ui_crawls()
        
        # Refresh objects from database
        self.inactive_crawl.refresh_from_db()
        self.active_crawl.refresh_from_db()
        self.api_crawl.refresh_from_db()
        self.completed_crawl.refresh_from_db()
        
        # Verify inactive UI crawl was stopped
        self.assertEqual(self.inactive_crawl.status, CrawlState.Status.STOPPED)
        self.assertIsNotNone(self.inactive_crawl.end_time)
        self.assertIn("automatically stopped due to inactivity", self.inactive_crawl.error_message)
        self.assertIn("20 seconds", self.inactive_crawl.error_message)
        
        # Verify active UI crawl was not affected
        self.assertEqual(self.active_crawl.status, CrawlState.Status.RUNNING)
        self.assertIsNone(self.active_crawl.end_time)
        self.assertIsNone(self.active_crawl.error_message)
        
        # Verify API crawl was not affected
        self.assertEqual(self.api_crawl.status, CrawlState.Status.RUNNING)
        self.assertIsNone(self.api_crawl.end_time)
        self.assertIsNone(self.api_crawl.error_message)
        
        # Verify completed crawl was not affected
        self.assertEqual(self.completed_crawl.status, CrawlState.Status.COMPLETED)
        self.assertIsNotNone(self.completed_crawl.end_time)

    @override_settings(CRAWL_INACTIVE_THRESHOLD_SECONDS=5)
    def test_stop_inactive_ui_crawls_shorter_threshold(self):
        """
        Test with a shorter inactivity threshold that affects more crawls.
        
        This test verifies that:
        1. When the threshold is decreased, more crawls may be affected
        2. Threshold change is properly reflected in the error message
        """
        # Run the task with a shorter threshold
        stop_inactive_ui_crawls()
        
        # Refresh objects from database
        self.inactive_crawl.refresh_from_db()
        self.active_crawl.refresh_from_db()
        
        # Both crawls should now be stopped since both exceed the 5 second threshold
        self.assertEqual(self.inactive_crawl.status, CrawlState.Status.STOPPED)
        self.assertEqual(self.active_crawl.status, CrawlState.Status.STOPPED)
        
        # Verify correct threshold in error messages
        self.assertIn("5 seconds", self.inactive_crawl.error_message)
        self.assertIn("5 seconds", self.active_crawl.error_message)

    @override_settings(CRAWL_INACTIVE_THRESHOLD_SECONDS=60)
    def test_stop_inactive_ui_crawls_longer_threshold(self):
        """
        Test with a longer inactivity threshold that doesn't affect any crawls.
        
        This test verifies that:
        1. When the threshold is increased, fewer crawls may be affected
        """
        # Run the task with a longer threshold
        stop_inactive_ui_crawls()
        
        # Refresh objects from database
        self.inactive_crawl.refresh_from_db()
        self.active_crawl.refresh_from_db()
        
        # None of the crawls should be stopped since they don't exceed the 60 second threshold
        self.assertEqual(self.inactive_crawl.status, CrawlState.Status.RUNNING)
        self.assertEqual(self.active_crawl.status, CrawlState.Status.RUNNING)

    def test_stop_inactive_ui_crawls_multiple_inactive(self):
        """
        Test with multiple inactive UI crawls.
        
        This test verifies that:
        1. Multiple inactive crawls are all processed correctly
        """
        # Create additional inactive UI crawls
        inactive_crawl2 = CrawlState.objects.create(
            url="https://inactive2.example.com",
            guru_type=self.guru_type,
            status=CrawlState.Status.RUNNING,
            start_time=self.now - timedelta(minutes=10),
            source=CrawlState.Source.UI,
        )
        inactive_crawl2.last_polled_at = self.now - timedelta(seconds=40)
        inactive_crawl2.save()
        
        inactive_crawl3 = CrawlState.objects.create(
            url="https://inactive3.example.com",
            guru_type=self.guru_type,
            status=CrawlState.Status.RUNNING,
            start_time=self.now - timedelta(minutes=15),
            source=CrawlState.Source.UI,
        )
        inactive_crawl3.last_polled_at = self.now - timedelta(seconds=50)
        inactive_crawl3.save()
        
        # Override setting directly for this test
        with override_settings(CRAWL_INACTIVE_THRESHOLD_SECONDS=20):
            # Run the task
            stop_inactive_ui_crawls()
        
        # Refresh objects from database
        inactive_crawl2.refresh_from_db()
        inactive_crawl3.refresh_from_db()
        
        # All inactive crawls should be stopped
        self.assertEqual(inactive_crawl2.status, CrawlState.Status.STOPPED)
        self.assertEqual(inactive_crawl3.status, CrawlState.Status.STOPPED)
        self.assertIsNotNone(inactive_crawl2.end_time)
        self.assertIsNotNone(inactive_crawl3.end_time)
