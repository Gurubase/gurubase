from django.test import TestCase, override_settings
from django.utils import timezone
from datetime import timedelta
from core.models import Question, GuruType, Binge, OutOfContextQuestion, DataSource, GithubFile, User
from .services import AnalyticsService
from .utils import get_date_range
from rest_framework.test import APIClient
from django.urls import reverse
from django.conf import settings

@override_settings(ENV='selfhosted')
class AnalyticsFilteringTests(TestCase):
    def setUp(self):
        # Set up API client
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
        
        # Non-slack root question with binge (should be excluded)
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
        # - child_binge_question
        # Should exclude:
        # - root_binge_question (non-slack/discord root binge question)
        self.assertEqual(total_questions, 5)
        
        # Referenced sources should be 1 (from regular_question)
        self.assertEqual(referenced_sources, 1)

    def test_analytics_table_filtering(self):
        """Test analytics table view filtering logic"""
        url = reverse('analytics_table', kwargs={'guru_type': self.guru_type.slug})
        
        response = self.client.get(url, {
            'metric_type': 'questions',
            'interval': 'today'
        })
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        # Should return 5 questions (excluding root_binge_question)
        self.assertEqual(data['total_items'], 5)
        
        # Verify that root_binge_question is not in results
        question_titles = [result['title'] for result in data['results']]
        self.assertNotIn("Root binge question", question_titles)
        
        # Verify that slack/discord root questions are in results
        self.assertIn("Slack root question", question_titles)
        self.assertIn("Discord root question", question_titles)
        
        # Test filtering by source
        response = self.client.get(url, {
            'metric_type': 'questions',
            'interval': 'today',
            'filter_type': 'slack'
        })
        
        data = response.json()
        # Should return both slack questions (root and child)
        self.assertEqual(data['total_items'], 2)
        slack_titles = [result['title'] for result in data['results']]
        self.assertIn("Slack root question", slack_titles)
        self.assertIn("Slack child question", slack_titles)
        
        # Test filtering by discord
        response = self.client.get(url, {
            'metric_type': 'questions',
            'interval': 'today',
            'filter_type': 'discord'
        })
        
        data = response.json()
        # Should return the discord root question
        self.assertEqual(data['total_items'], 1)
        self.assertEqual(data['results'][0]['title'], "Discord root question")

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
        # - Previous questions (5)
        # - child1
        # - child2
        # Should exclude:
        # - root (non-slack/discord root)
        expected_total = 7  # 5 previous + child1 + child2
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
        
        # Test analytics table view for these cases
        url = reverse('analytics_table', kwargs={'guru_type': self.guru_type.slug})
        
        response = self.client.get(url, {
            'metric_type': 'questions',
            'interval': 'today'
        })
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        # Should include:
        # - Previous questions (5)
        # - api_child
        # - widget_child
        self.assertEqual(data['total_items'], 7)
        
        question_titles = [result['title'] for result in data['results']]
        
        # Verify root questions are properly filtered
        self.assertIn("Slack root question", question_titles)
        self.assertIn("Discord root question", question_titles)
        self.assertNotIn("API root question", question_titles)
        self.assertNotIn("Widget root question", question_titles)
        
        # Verify children are included regardless of source
        self.assertIn("API child question", question_titles)
        self.assertIn("Widget child question", question_titles)
