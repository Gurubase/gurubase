from django.test import TestCase, override_settings
from django.utils import timezone
from unittest.mock import patch, MagicMock
import redis
from accounts.models import User
from core.models import Question, GuruType, DataSource, Integration, Settings, LLMEval, LLMEvalResult, SummaryQuestionGeneration, LinkReference, Favicon
from core.tasks import fill_empty_og_images, update_question_as_the_question_content_h1, find_duplicate_question_titles, process_titles, data_source_retrieval, llm_eval, llm_eval_result, check_favicon_validity
from core.utils import get_default_settings
from core.tasks import rewrite_content_for_wrong_markdown_content
from core.exceptions import WebsiteContentExtractionThrottleError, GithubInvalidRepoError, GithubRepoSizeLimitError, GithubRepoFileCountLimitError, YouTubeContentExtractionError
from core.requester import FirecrawlScraper # For type checking
import time
from datetime import datetime

class ProcessTitlesTaskTests(TestCase):
    def setUp(self):
        get_default_settings()
        self.guru_type = GuruType.objects.create(
            slug="test-guru", name="Test Guru", custom=True, active=True
        )
        self.q_process1 = Question.objects.create(
            guru_type=self.guru_type,
            question="Can you explain this topic?", # Matches filter
            slug="process-1",
            content="# Can you explain this topic?\nContent",
            title_processed=False
        )
        self.q_process2 = Question.objects.create(
            guru_type=self.guru_type,
            question="Describe how that works.", # Matches filter
            slug="process-2",
            content="# Describe how that works.\nContent",
            title_processed=False
        )
        self.q_skip_processed = Question.objects.create(
            guru_type=self.guru_type,
            question="Can I use this feature?",
            slug="skip-processed",
            content="# Can I use this feature?\nContent",
            title_processed=True # Already processed
        )
        self.q_skip_no_match = Question.objects.create(
            guru_type=self.guru_type,
            question="How does this work?", # Doesn't match filter keywords
            slug="skip-no-match",
            content="# How does this work?\nContent",
            title_processed=False
        )

    @patch('core.tasks.get_more_seo_friendly_title')
    @patch('core.tasks.logger')
    @patch('core.tasks.redis_client') # Mock redis lock
    def test_process_titles_success(self, mock_redis, mock_logger, mock_get_seo_title):
        """Test processing titles that match criteria and successful SEO update."""
        mock_get_seo_title.side_effect = [
            "Explained Topic Title", # For q_process1
            "How That Works Described" # For q_process2
        ]

        process_titles()

        self.q_process1.refresh_from_db()
        self.q_process2.refresh_from_db()
        self.q_skip_processed.refresh_from_db()
        self.q_skip_no_match.refresh_from_db()

        # Assertions for processed questions
        self.assertEqual(mock_get_seo_title.call_count, 2)
        mock_get_seo_title.assert_any_call("Can you explain this topic?")
        mock_get_seo_title.assert_any_call("Describe how that works.")

        self.assertEqual(self.q_process1.question, "Explained Topic Title")
        self.assertEqual(self.q_process1.old_question, "Can you explain this topic?")
        self.assertTrue(self.q_process1.title_processed)
        self.assertEqual(self.q_process1.content, "# Explained Topic Title\nContent")

        self.assertEqual(self.q_process2.question, "How That Works Described")
        self.assertEqual(self.q_process2.old_question, "Describe how that works.")
        self.assertTrue(self.q_process2.title_processed)
        self.assertEqual(self.q_process2.content, "# How That Works Described\nContent")

        # Assertions for skipped questions
        self.assertEqual(self.q_skip_processed.question, "Can I use this feature?")
        self.assertFalse(self.q_skip_processed.old_question) # Should not be set
        self.assertTrue(self.q_skip_processed.title_processed) # Remains true

        self.assertEqual(self.q_skip_no_match.question, "How does this work?")
        self.assertFalse(self.q_skip_no_match.old_question)
        self.assertFalse(self.q_skip_no_match.title_processed) # Remains false

        mock_logger.info.assert_any_call(f"Updated question: {self.q_process1.id}")
        mock_logger.info.assert_any_call(f"Updated question: {self.q_process2.id}")

    @patch('core.tasks.get_more_seo_friendly_title')
    @patch('core.tasks.logger')
    @patch('core.tasks.redis_client')
    def test_process_titles_seo_fail(self, mock_redis, mock_logger, mock_get_seo_title):
        """Test processing titles when get_more_seo_friendly_title returns empty."""
        mock_get_seo_title.return_value = "" # Simulate failure

        original_title = self.q_process1.question
        original_content = self.q_process1.content

        process_titles()

        self.q_process1.refresh_from_db()

        # Assertions
        self.assertEqual(mock_get_seo_title.call_count, 2)
        mock_get_seo_title.assert_any_call(original_title)
        mock_get_seo_title.assert_any_call(self.q_process2.question)
        self.assertEqual(self.q_process1.question, original_title) # Should not change
        self.assertFalse(self.q_process1.old_question)
        self.assertFalse(self.q_process1.title_processed) # Should remain False
        self.assertEqual(self.q_process1.content, original_content) # Should not change
        # Check logger info was not called for this question ID
        for call_args, _ in mock_logger.info.call_args_list:
            self.assertNotIn(f"Updated question: {self.q_process1.id}", call_args[0])
