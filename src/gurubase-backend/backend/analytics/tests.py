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
