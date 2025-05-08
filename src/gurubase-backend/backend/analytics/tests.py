from django.conf import settings
from django.test import TestCase
from django.utils import timezone
from datetime import timedelta
from core.models import Question, GuruType, Binge, OutOfContextQuestion, DataSource, GithubFile, User
from .services import AnalyticsService
from .utils import get_date_range
from rest_framework.test import APIClient
from django.urls import reverse
from core.utils import get_default_settings

class AnalyticsFilteringTests(TestCase):
    def setUp(self):
        # Set up API client
        get_default_settings()
        User.objects.create_superuser(email=settings.ROOT_EMAIL, password=settings.ROOT_PASSWORD, name='Admin')
        self.client = APIClient()
        
        # Create a guru type for testing
        self.guru_type = GuruType.objects.create(
            name="Test Guru",
            slug="test-guru"
        )
        
        # Create a binge for testing
        self.binge = Binge.objects.create(
            guru_type=self.guru_type
        )
        
        # Create test questions with different configurations
        self.now = timezone.now()
        
        # Regular question (should be included)
        self.regular_question = Question.objects.create(
            guru_type=self.guru_type,
            question="Regular question",
            user_question="Regular question",
            source=Question.Source.USER.value,
            slug="regular-question"
        )
        
        # Slack question with binge and parent (should be included)
        self.slack_child_question = Question.objects.create(
            guru_type=self.guru_type,
            question="Slack child question",
            user_question="Slack child question",
            source=Question.Source.SLACK.value,
            binge=self.binge,
            slug="slack-child-question"
        )
        
        # Slack binge root question (should be included)
        self.slack_root_question = Question.objects.create(
            guru_type=self.guru_type,
            question="Slack root question",
            user_question="Slack root question",
            source=Question.Source.SLACK.value,
            binge=self.binge,
            slug="slack-root-question"
        )
        
        # Discord binge root question (should be included)
        self.discord_root_question = Question.objects.create(
            guru_type=self.guru_type,
            question="Discord root question",
            user_question="Discord root question",
            source=Question.Source.DISCORD.value,
            binge=self.binge,
            slug="discord-root-question"
        )
        
        # Github binge root question (should be included)
        self.github_root_question = Question.objects.create(
            guru_type=self.guru_type,
            question="Github root question",
            user_question="Github root question",
            source=Question.Source.GITHUB.value,
            binge=self.binge,
            slug="github-root-question"
        )
        
        # Non-slack-discord-github root question with binge (should be excluded)
        self.root_binge_question = Question.objects.create(
            guru_type=self.guru_type,
            question="Root binge question",
            user_question="Root binge question",
            source=Question.Source.USER.value,
            binge=self.binge,
            slug="root-binge-question"
        )
        
        # Child of root binge question (should be included)
        self.child_binge_question = Question.objects.create(
            guru_type=self.guru_type,
            question="Child binge question",
            user_question="Child binge question",
            source=Question.Source.USER.value,
            binge=self.binge,
            parent=self.root_binge_question,
            slug="child-binge-question"
        )
        
        # Create a data source for testing referenced sources
        self.data_source = DataSource.objects.create(
            guru_type=self.guru_type,
            url="https://test.com",
            title="Test Source",
            type="website",
            status=DataSource.Status.SUCCESS
        )
        
        # Add reference to regular question
        self.regular_question.references = [{'link': 'https://test.com'}]
        self.regular_question.save()

    def test_get_stats_for_period(self):
        """Test that get_stats_for_period correctly filters questions"""
        start_date = self.now - timedelta(days=1)
        end_date = self.now + timedelta(days=1)
        
        stats = AnalyticsService.get_stats_for_period(self.guru_type, start_date, end_date)
        total_questions, out_of_context, referenced_sources = stats
        
        # Should include:
        # - regular_question
        # - slack_child_question
        # - slack_root_question
        # - discord_root_question
        # - github_root_question
        # - child_binge_question
        # Should exclude:
        # - root_binge_question (non-slack/discord/github root binge question)
        self.assertEqual(total_questions, 6)
        
        # Referenced sources should be 1 (from regular_question)
        self.assertEqual(referenced_sources, 1)

    def test_analytics_table_filtering(self):
        """Test analytics table view filtering logic"""
        start_date = self.now - timedelta(days=1)
        end_date = self.now + timedelta(days=1)
        
        # Test getting all questions
        queryset = AnalyticsService._get_filtered_questions(
            self.guru_type, start_date, end_date, None, '', 'desc'
        )
        paginated_data = AnalyticsService.get_paginated_data(queryset, 1)
        
        # Should return 6 questions (excluding root_binge_question)
        self.assertEqual(paginated_data['total_items'], 6)
        
        # Verify that root_binge_question is not in results
        question_titles = [item.user_question for item in paginated_data['items']]
        self.assertNotIn("Root binge question", question_titles)
        
        # Verify that slack/discord/github root questions are in results
        self.assertIn("Slack root question", question_titles)
        self.assertIn("Discord root question", question_titles)
        self.assertIn("Github root question", question_titles)
        
        # Test filtering by source
        queryset = AnalyticsService._get_filtered_questions(
            self.guru_type, start_date, end_date, 'slack', '', 'desc'
        )
        paginated_data = AnalyticsService.get_paginated_data(queryset, 1)
        
        # Should return both slack questions (root and child)
        self.assertEqual(paginated_data['total_items'], 2)
        slack_titles = [item.user_question for item in paginated_data['items']]
        self.assertIn("Slack root question", slack_titles)
        self.assertIn("Slack child question", slack_titles)
        
        # Test filtering by discord
        queryset = AnalyticsService._get_filtered_questions(
            self.guru_type, start_date, end_date, 'discord', '', 'desc'
        )
        paginated_data = AnalyticsService.get_paginated_data(queryset, 1)
        
        # Should return the discord root question
        self.assertEqual(paginated_data['total_items'], 1)
        self.assertEqual(paginated_data['items'][0].user_question, "Discord root question")

        # Test filtering by github
        queryset = AnalyticsService._get_filtered_questions(
            self.guru_type, start_date, end_date, 'github', '', 'desc'
        )
        paginated_data = AnalyticsService.get_paginated_data(queryset, 1)
        
        # Should return the github root question
        self.assertEqual(paginated_data['total_items'], 1)
        self.assertEqual(paginated_data['items'][0].user_question, "Github root question")

    def test_binge_question_hierarchy(self):
        """Test that binge question hierarchy is correctly handled"""
        start_date = self.now - timedelta(days=1)
        end_date = self.now + timedelta(days=1)
        
        # Create a new binge with multiple levels
        deep_binge = Binge.objects.create(guru_type=self.guru_type)
        
        # Create a chain of questions: root -> child1 -> child2
        root = Question.objects.create(
            guru_type=self.guru_type,
            question="Deep root",
            user_question="Deep root",
            source=Question.Source.USER.value,
            binge=deep_binge,
            slug="deep-root"
        )
        
        child1 = Question.objects.create(
            guru_type=self.guru_type,
            question="Child 1",
            user_question="Child 1",
            source=Question.Source.USER.value,
            binge=deep_binge,
            parent=root,
            slug="child-1"
        )
        
        child2 = Question.objects.create(
            guru_type=self.guru_type,
            question="Child 2",
            user_question="Child 2",
            source=Question.Source.USER.value,
            binge=deep_binge,
            parent=child1,
            slug="child-2"
        )
        
        stats = AnalyticsService.get_stats_for_period(self.guru_type, start_date, end_date)
        total_questions, _, _ = stats
        
        # Should include:
        # - Previous questions (6)
        # - child1
        # - child2
        # Should exclude:
        # - root (non-slack/discord root)
        expected_total = 8  # 6 previous + child1 + child2
        self.assertEqual(total_questions, expected_total)

    def test_binge_root_filtering(self):
        """Test specific cases for binge root filtering"""
        start_date = self.now - timedelta(days=1)
        end_date = self.now + timedelta(days=1)
        
        # Create additional test cases
        api_root = Question.objects.create(
            guru_type=self.guru_type,
            question="API root question",
            user_question="API root question",
            source=Question.Source.API.value,
            binge=self.binge,
            slug="api-root-question"
        )
        
        widget_root = Question.objects.create(
            guru_type=self.guru_type,
            question="Widget root question",
            user_question="Widget root question",
            source=Question.Source.WIDGET_QUESTION.value,
            binge=self.binge,
            slug="widget-root-question"
        )
        
        # Create children for different types of roots
        api_child = Question.objects.create(
            guru_type=self.guru_type,
            question="API child question",
            user_question="API child question",
            source=Question.Source.API.value,
            binge=self.binge,
            parent=api_root,
            slug="api-child-question"
        )
        
        widget_child = Question.objects.create(
            guru_type=self.guru_type,
            question="Widget child question",
            user_question="Widget child question",
            source=Question.Source.WIDGET_QUESTION.value,
            binge=self.binge,
            parent=widget_root,
            slug="widget-child-question"
        )
        
        # Test getting all questions
        queryset = AnalyticsService._get_filtered_questions(
            self.guru_type, start_date, end_date, None, '', 'desc'
        )
        paginated_data = AnalyticsService.get_paginated_data(queryset, 1)
        
        # Should include:
        # - Previous questions (6)
        # - api_child
        # - widget_child
        self.assertEqual(paginated_data['total_items'], 8)
        
        question_titles = [item.user_question for item in paginated_data['items']]
        
        # Verify root questions are properly filtered
        self.assertIn("Slack root question", question_titles)
        self.assertIn("Discord root question", question_titles)
        self.assertIn("Github root question", question_titles)
        self.assertNotIn("API root question", question_titles)
        self.assertNotIn("Widget root question", question_titles)
        
        # Verify children are included regardless of source
        self.assertIn("API child question", question_titles)
        self.assertIn("Widget child question", question_titles)

class UtilsTests(TestCase):
    def test_get_date_range(self):
        """Test the get_date_range function for different intervals"""
        from .utils import get_date_range
        from datetime import UTC, datetime

        # Mock current time for consistent testing
        mock_now = datetime(2023, 1, 15, 14, 30, 0, tzinfo=UTC)
        
        # Test 'today' interval
        with self.subTest("today interval"):
            start, end = get_date_range('today')
            self.assertEqual(start.date(), datetime.now(UTC).date())
            self.assertEqual(start.hour, 0)
            self.assertEqual(start.minute, 0)
            self.assertEqual(end.date(), datetime.now(UTC).date())
        
        # Test 'yesterday' interval
        with self.subTest("yesterday interval"):
            start, end = get_date_range('yesterday')
            yesterday = datetime.now(UTC).date() - timedelta(days=1)
            self.assertEqual(start.date(), yesterday)
            self.assertEqual(end.date(), datetime.now(UTC).date())
            self.assertEqual(end.hour, 0)
            self.assertEqual(end.minute, 59)
        
        # Test '7d' interval
        with self.subTest("7d interval"):
            start, end = get_date_range('7d')
            self.assertEqual((end.date() - start.date()).days, 7)
            
        # Test '30d' interval
        with self.subTest("30d interval"):
            start, end = get_date_range('30d')
            self.assertEqual((end.date() - start.date()).days, 30)
            
        # Test '3m' interval
        with self.subTest("3m interval"):
            start, end = get_date_range('3m')
            self.assertEqual((end.date() - start.date()).days, 90)
            
        # Test '6m' interval
        with self.subTest("6m interval"):
            start, end = get_date_range('6m')
            self.assertEqual((end.date() - start.date()).days, 180)
            
        # Test '12m' interval
        with self.subTest("12m interval"):
            start, end = get_date_range('12m')
            self.assertEqual((end.date() - start.date()).days, 365)
            
        # Test invalid interval defaults to today
        with self.subTest("invalid interval"):
            start, end = get_date_range('invalid')
            self.assertEqual(start.date(), datetime.now(UTC).date())
            self.assertEqual(start.hour, 0)
            self.assertEqual(start.minute, 0)

    def test_calculate_percentage_change(self):
        """Test the calculate_percentage_change function"""
        from .utils import calculate_percentage_change
        
        # Test normal case
        self.assertEqual(calculate_percentage_change(150, 100), 50)
        
        # Test decrease case
        self.assertEqual(calculate_percentage_change(80, 100), -20)
        
        # Test zero previous value
        self.assertEqual(calculate_percentage_change(100, 0), 100)
        
        # Test both zero values
        self.assertEqual(calculate_percentage_change(0, 0), 0)
        
        # Test fractional changes
        self.assertEqual(calculate_percentage_change(105, 100), 5)
        self.assertEqual(calculate_percentage_change(103.5, 100), 3.5)

    def test_format_filter_name_for_display(self):
        """Test the format_filter_name_for_display function"""
        from .utils import format_filter_name_for_display
        
        # Test known mappings
        self.assertEqual(format_filter_name_for_display('user'), 'Gurubase UI')
        self.assertEqual(format_filter_name_for_display('github_repo'), 'Codebase')
        self.assertEqual(format_filter_name_for_display('pdf'), 'PDF')
        
        # Test standard transformations
        self.assertEqual(format_filter_name_for_display('slack_message'), 'Slack Message')
        self.assertEqual(format_filter_name_for_display('raw_query'), 'Raw Query')
        
        # Test case preservation for known acronyms
        self.assertEqual(format_filter_name_for_display('PDF'), 'PDF')
        self.assertEqual(format_filter_name_for_display('YouTube'), 'YouTube')

    def test_get_histogram_increment(self):
        """Test the get_histogram_increment function"""
        from .utils import get_histogram_increment
        from datetime import UTC, datetime
        
        # Test today/yesterday interval (hourly increments)
        start = datetime(2023, 1, 1, 0, 0, 0, tzinfo=UTC)
        end = datetime(2023, 1, 1, 23, 59, 59, tzinfo=UTC)
        
        increment, formatter = get_histogram_increment(start, end, 'today')
        self.assertEqual(increment, timedelta(hours=1))
        
        result = formatter(start, start + increment)
        self.assertEqual(result, {'date_point': start.isoformat()})
        
        # Test short range (daily increments)
        start = datetime(2023, 1, 1, 0, 0, 0, tzinfo=UTC)
        end = datetime(2023, 1, 15, 23, 59, 59, tzinfo=UTC)
        
        increment, formatter = get_histogram_increment(start, end, '15d')
        self.assertEqual(increment, timedelta(days=1))
        
        # Test longer range (grouped days)
        start = datetime(2023, 1, 1, 0, 0, 0, tzinfo=UTC)
        end = datetime(2023, 3, 2, 23, 59, 59, tzinfo=UTC)  # ~60 days
        
        increment, formatter = get_histogram_increment(start, end, '60d')
        self.assertGreater(increment.days, 1)  # Should group multiple days
        
        # Test date range format
        result = formatter(start, start + timedelta(days=2))
        self.assertIn('date_start', result)
        self.assertIn('date_end', result)
        self.assertEqual(result['date_start'], start.isoformat())

    def test_map_filter_to_source(self):
        """Test the map_filter_to_source function"""
        from .utils import map_filter_to_source
        
        # Test None/all returns None
        self.assertIsNone(map_filter_to_source(None))
        self.assertIsNone(map_filter_to_source('all'))
        
        # Test known mappings
        self.assertEqual(map_filter_to_source('widget'), 'WIDGET QUESTION')
        self.assertEqual(map_filter_to_source('user'), 'USER')
        self.assertEqual(map_filter_to_source('github'), 'GITHUB')
        
        # Test case insensitivity
        self.assertEqual(map_filter_to_source('Widget'), 'WIDGET QUESTION')
        self.assertEqual(map_filter_to_source('USER'), 'USER')
        
        # Test unknown filter types (should convert to uppercase)
        self.assertEqual(map_filter_to_source('custom_type'), 'CUSTOM_TYPE')
