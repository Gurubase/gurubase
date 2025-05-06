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

class UpdateQuestionFromH1TaskTests(TestCase):
    def setUp(self):
        get_default_settings()
        self.guru_type = GuruType.objects.create(
            slug="test-guru", name="Test Guru", custom=True, active=True
        )
        self.q_correct = Question.objects.create(
            guru_type=self.guru_type,
            question="Correct Title",
            slug="correct",
            content="# Correct Title\nSome content."
        )
        self.q_mismatch = Question.objects.create(
            guru_type=self.guru_type,
            question="Old Title", # Different from H1
            slug="mismatch",
            content="# New Title From H1\nSome content."
        )



    @patch('core.tasks.logger')
    def test_update_question_from_h1_mismatch(self, mock_logger):
        """Test updating question.question when it mismatches the content H1."""
        update_question_as_the_question_content_h1()

        self.q_mismatch.refresh_from_db()
        self.assertEqual(self.q_mismatch.question, "New Title From H1")
        mock_logger.info.assert_any_call("Updating question title: Old Title to New Title From H1")

    @patch('core.tasks.logger')
    def test_update_question_from_h1_correct(self, mock_logger):
        """Test that question.question is not updated if it matches the content H1."""
        original_question = self.q_correct.question
        update_question_as_the_question_content_h1()

        self.q_correct.refresh_from_db()
        self.assertEqual(self.q_correct.question, original_question)
        # Ensure no 'Updating' log message for this question
        for call_args, _ in mock_logger.info.call_args_list:
            self.assertNotIn("Updating question title: Correct Title", call_args[0])

    @patch('core.tasks.logger')
    def test_update_question_from_h1_no_h1(self, mock_logger):
        """Test that the question is skipped if content doesn't start with H1."""
        self.q_no_h1 = Question.objects.create(
            guru_type=self.guru_type,
            question="No H1",
            slug="no-h1",
            content="## Not an H1\nSome content."
        )        
        original_question = self.q_no_h1.question
        update_question_as_the_question_content_h1()

        self.q_no_h1.refresh_from_db()
        self.assertEqual(self.q_no_h1.question, original_question) # Should not change
        mock_logger.fatal.assert_called_once_with(f"Title not starting with '# ': ## Not an H1. ID: {self.q_no_h1.id}")

    @patch('core.tasks.get_more_seo_friendly_title')
    @patch('core.tasks.logger')
    def test_update_question_from_h1_long_h1_success(self, mock_logger, mock_get_seo_title):
        """Test handling of long H1 title with successful shortening."""
        long_title_original = 'a' * 160
        shortened_title = "Shortened Title" # Mocked SEO title
        mock_get_seo_title.return_value = shortened_title
        self.q_long_h1 = Question.objects.create(
            guru_type=self.guru_type,
            question="Long H1 Original",
            slug="long-h1",
            content=f"# {'a' * 160}\nSome content." # Title > 150 chars
        )

        update_question_as_the_question_content_h1()

        self.q_long_h1.refresh_from_db()
        mock_get_seo_title.assert_called_once_with(long_title_original)
        self.assertEqual(self.q_long_h1.question, shortened_title)
        # Check that content was also updated
        self.assertTrue(self.q_long_h1.content.startswith(f"# {shortened_title}\n"))
        mock_logger.fatal.assert_not_called()

    @patch('core.tasks.get_more_seo_friendly_title')
    @patch('core.tasks.logger')
    def test_update_question_from_h1_long_h1_fail(self, mock_logger, mock_get_seo_title):
        """Test handling of long H1 title when shortening fails."""
        self.q_long_h1 = Question.objects.create(
            guru_type=self.guru_type,
            question="Long H1 Original",
            slug="long-h1",
            content=f"# {'a' * 160}\nSome content." # Title > 150 chars
        )
        long_title_original = 'a' * 160
        mock_get_seo_title.return_value = "" # Simulate shortening failure

        update_question_as_the_question_content_h1()

        self.q_long_h1.refresh_from_db()
        mock_get_seo_title.assert_called_once_with(long_title_original)
        self.assertEqual(self.q_long_h1.question, "Long H1 Original") # Question should not change
        self.assertTrue(self.q_long_h1.content.startswith(f"# {long_title_original}\n")) # Content should not change
        mock_logger.fatal.assert_called_once_with(f"Title length greater than 150, shortening attempt failed: {long_title_original}. ID: {self.q_long_h1.id}")
