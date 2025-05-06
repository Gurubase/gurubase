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

class FillEmptyOgImagesTaskTests(TestCase):
    def setUp(self):
        get_default_settings()
        self.guru_type = GuruType.objects.create(
            slug="test-guru", name="Test Guru", custom=True, active=True
        )
        self.q_with_og = Question.objects.create(
            guru_type=self.guru_type,
            question="With OG",
            slug="with-og",
            content="# With OG",
            og_image_url="http://example.com/og.png"
        )
        self.q_without_og = Question.objects.create(
            guru_type=self.guru_type,
            question="Without OG",
            slug="without-og",
            content="# Without OG",
            og_image_url="" # Empty OG image URL
        )

    @patch('core.tasks.generate_og_image')
    @override_settings(FILL_OG_IMAGES_FETCH_BATCH_SIZE=10)
    def test_fill_empty_og_images(self, mock_generate_og_image):
        """Test that generate_og_image is called only for questions with empty OG URLs."""
        # Call the task
        fill_empty_og_images()

        # Assertions
        # generate_og_image should only be called for q_without_og
        mock_generate_og_image.assert_called_once_with(self.q_without_og)

        # Verify the call count is exactly 1
        self.assertEqual(mock_generate_og_image.call_count, 1)

    @patch('core.tasks.generate_og_image')
    def test_fill_empty_og_images_no_empty(self, mock_generate_og_image):
        """Test that generate_og_image is not called if no questions have empty OG URLs."""
        # Ensure q_without_og also has an OG image now
        self.q_without_og.og_image_url = "http://example.com/another-og.png"
        self.q_without_og.save()

        # Call the task
        fill_empty_og_images()

        # Assertions
        mock_generate_og_image.assert_not_called()
