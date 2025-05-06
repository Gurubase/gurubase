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

# class SetSimilaritiesTaskTests(TestCase):
#     def setUp(self):
#         # Setup initial data
#         get_default_settings()
#         self.guru_type = GuruType.objects.create(
#             slug="test-guru",
#             name="Test Guru",
#             domain_knowledge="Test domain knowledge",
#             custom=True,
#             active=True
#         )
#         self.q1 = Question.objects.create(
#             guru_type=self.guru_type,
#             question="Question 1",
#             slug="question-1",
#             content="# Question 1"
#         )
#         self.q2 = Question.objects.create(
#             guru_type=self.guru_type,
#             question="Question 2",
#             slug="question-2",
#             content="# Question 2"
#         )

#     @patch('core.tasks.get_most_similar_questions')
#     @patch('core.tasks.redis_client')
#     def test_set_similarities_basic(self, mock_redis_client, mock_get_most_similar):
#         """Test the basic functionality of set_similarities task."""
#         # Mock Redis client behavior
#         mock_redis_client.get.return_value = None # Start from the beginning
#         mock_redis_client.set = MagicMock()
#         mock_redis_client.delete = MagicMock()

#         # Mock get_most_similar_questions to return predictable results
#         mock_get_most_similar.side_effect = [
#             [{'slug': 'similar-1', 'score': 0.9}], # For q1
#             [{'slug': 'similar-2', 'score': 0.8}]  # For q2
#         ]

#         # Call the task
#         set_similarities()

#         # Refresh objects from DB
#         self.q1.refresh_from_db()
#         self.q2.refresh_from_db()

#         # Assertions
#         self.assertEqual(self.q1.similar_questions, [{'slug': 'similar-1', 'score': 0.9}])
#         self.assertEqual(self.q2.similar_questions, [{'slug': 'similar-2', 'score': 0.8}])

#         # Check if get_most_similar_questions was called correctly
#         self.assertEqual(mock_get_most_similar.call_count, 2)
#         mock_get_most_similar.assert_any_call(
#             self.q1.slug, self.q1.question, self.q1.guru_type.slug, column='title', sitemap_constraint=True
#         )
#         mock_get_most_similar.assert_any_call(
#             self.q2.slug, self.q2.question, self.q2.guru_type.slug, column='title', sitemap_constraint=True
#         )

#         # Check Redis interactions
#         mock_redis_client.get.assert_called_once_with('set_similar_questions_last_processed_id')
#         # Should set the last processed ID twice (once for each question)
#         self.assertEqual(mock_redis_client.set.call_count, 2)
#         mock_redis_client.set.assert_any_call('set_similar_questions_last_processed_id', self.q1.id)
#         mock_redis_client.set.assert_any_call('set_similar_questions_last_processed_id', self.q2.id)
#         # Since we processed all questions, it should reset by deleting the key after the next run (not tested here directly)

#     @patch('core.tasks.get_most_similar_questions')
#     @patch('core.tasks.redis_client')
#     @override_settings(SIMILARITY_FETCH_BATCH_SIZE=1, SIMILARITY_SAVE_BATCH_SIZE=1)
#     def test_set_similarities_batching_and_resume(self, mock_redis_client, mock_get_most_similar):
#         """Test batching and resuming from last processed ID."""
#         # Mock Redis client to simulate resuming
#         mock_redis_client.get.return_value = str(self.q1.id) # Resume after q1
#         mock_redis_client.set = MagicMock()
#         mock_redis_client.delete = MagicMock()

#         # Mock get_most_similar_questions
#         mock_get_most_similar.return_value = [{'slug': 'similar-2-resume', 'score': 0.85}]

#         # Call the task
#         set_similarities()

#         # Refresh objects from DB
#         self.q1.refresh_from_db()
#         self.q2.refresh_from_db()

#         # Assertions
#         self.assertEqual(self.q1.similar_questions, {}) # q1 should not be processed
#         self.assertEqual(self.q2.similar_questions, [{'slug': 'similar-2-resume', 'score': 0.85}]) # Only q2 processed

#         # Check if get_most_similar_questions was called only for q2
#         self.assertEqual(mock_get_most_similar.call_count, 1)
#         mock_get_most_similar.assert_called_once_with(
#             self.q2.slug, self.q2.question, self.q2.guru_type.slug, column='title', sitemap_constraint=True
#         )

#         # Check Redis interactions
#         mock_redis_client.get.assert_called_once_with('set_similar_questions_last_processed_id')
#         mock_redis_client.set.assert_called_once_with('set_similar_questions_last_processed_id', self.q2.id)
#         mock_redis_client.delete.assert_not_called() # Not called yet as it hasn't wrapped around

#     @patch('core.tasks.get_most_similar_questions')
#     @patch('core.tasks.redis_client')
#     @override_settings(SIMILARITY_FETCH_BATCH_SIZE=10)
#     def test_set_similarities_no_questions(self, mock_redis_client, mock_get_most_similar):
#         """Test the task when there are no questions."""
#         Question.objects.all().delete() # Remove existing questions

#         # Mock Redis client
#         mock_redis_client.get.return_value = None
#         mock_redis_client.set = MagicMock()
#         mock_redis_client.delete = MagicMock()

#         # Call the task
#         set_similarities()

#         # Assertions
#         mock_get_most_similar.assert_not_called()
#         mock_redis_client.get.assert_called_once_with('set_similar_questions_last_processed_id')
#         mock_redis_client.delete.assert_called_once_with('set_similar_questions_last_processed_id') # Tries to reset
#         mock_redis_client.set.assert_not_called()

#     @patch('core.tasks.Question.objects.bulk_update')
#     @patch('core.tasks.get_most_similar_questions')
#     @patch('core.tasks.redis_client')
#     @override_settings(SIMILARITY_FETCH_BATCH_SIZE=5, SIMILARITY_SAVE_BATCH_SIZE=1)
#     def test_set_similarities_save_batching(self, mock_redis_client, mock_get_most_similar, mock_bulk_update):
#         """Test that bulk_update is called according to SIMILARITY_SAVE_BATCH_SIZE."""
#         # Mock Redis client
#         mock_redis_client.get.return_value = None
#         mock_redis_client.set = MagicMock()

#         # Mock get_most_similar_questions
#         mock_get_most_similar.side_effect = [
#             [{'slug': 'similar-1', 'score': 0.9}],
#             [{'slug': 'similar-2', 'score': 0.8}],
#             [{'slug': 'similar-2', 'score': 0.8}],
#             [{'slug': 'similar-1', 'score': 0.9}],
#         ]

#         # Call the task
#         set_similarities()

#         # Assertions
#         # bulk_update should be called twice (once per question due to save_batch_size=1)
#         self.assertEqual(mock_bulk_update.call_count, 2)
#         mock_bulk_update.assert_any_call([self.q1], ['similar_questions'])
#         mock_bulk_update.assert_any_call([self.q2], ['similar_questions'])

#         # Now test with save_batch_size=2
#         mock_bulk_update.reset_mock()
#         with override_settings(SIMILARITY_SAVE_BATCH_SIZE=2):
#             set_similarities()
#             # bulk_update should be called once with both questions
#             self.assertEqual(mock_bulk_update.call_count, 1)
#             # Check the list of objects passed to bulk_update
#             call_args, _ = mock_bulk_update.call_args
#             updated_objects = call_args[0]
#             # The order might not be guaranteed, so check the IDs
#             updated_ids = {obj.id for obj in updated_objects}
#             self.assertEqual(updated_ids, {self.q1.id, self.q2.id})
#             self.assertEqual(call_args[1], ['similar_questions'])
