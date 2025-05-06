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

class FindDuplicateTitlesTaskTests(TestCase):
    def setUp(self):
        get_default_settings()
        self.guru_type = GuruType.objects.create(
            slug="test-guru", name="Test Guru", custom=True, active=True
        )
        self.q1 = Question.objects.create(
            guru_type=self.guru_type,
            question="Unique Title 1",
            slug="unique-1",
            content="# Unique Title 1",
            add_to_sitemap=True
        )
        self.q2 = Question.objects.create(
            guru_type=self.guru_type,
            question="Duplicate Title",
            slug="duplicate-1",
            content="# Duplicate Title v1",
            add_to_sitemap=True
        )
        self.q3 = Question.objects.create(
            guru_type=self.guru_type,
            question="Duplicate Title",
            slug="duplicate-2",
            content="# Duplicate Title v2",
            add_to_sitemap=True
        )
        self.q4 = Question.objects.create(
            guru_type=self.guru_type,
            question="Unique Title 2",
            slug="unique-2",
            content="# Unique Title 2",
            add_to_sitemap=True
        )
        self.q5_not_sitemap = Question.objects.create(
            guru_type=self.guru_type,
            question="Duplicate Title",
            slug="duplicate-not-sitemap",
            content="# Duplicate Title v3",
            add_to_sitemap=False # Not on sitemap
        )

    @patch('core.tasks.logger')
    def test_find_duplicate_titles(self, mock_logger):
        """Test that duplicate titles among sitemap questions are logged."""
        find_duplicate_question_titles()

        # Assertions
        # Logger should be called twice, once for q2 finding q3, once for q3 finding q2
        self.assertEqual(mock_logger.fatal.call_count, 2)
        mock_logger.fatal.assert_any_call(f"Question has duplicate title: Duplicate Title. ID: {self.q2.id}")
        mock_logger.fatal.assert_any_call(f"Question has duplicate title: Duplicate Title. ID: {self.q3.id}")

    @patch('core.tasks.logger')
    def test_find_duplicate_titles_no_duplicates(self, mock_logger):
        """Test that no logs are generated when there are no duplicate titles."""
        # Make titles unique
        self.q3.question = "Duplicate Title Made Unique"
        self.q3.save()

        find_duplicate_question_titles()

        # Assertions
        mock_logger.fatal.assert_not_called()

    @patch('core.tasks.logger')
    def test_find_duplicate_titles_ignores_not_sitemap(self, mock_logger):
        """Test that questions not on the sitemap are ignored."""
        # Remove q3, leaving q2 (sitemap=True) and q5 (sitemap=False) with same title
        self.q3.delete()

        find_duplicate_question_titles()

        # Assertions
        # No fatal log should be called because q5 is not on the sitemap
        mock_logger.fatal.assert_not_called()
