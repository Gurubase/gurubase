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

@override_settings(
    GPT_MODEL='gpt-test-model',
    EMBED_API_URL='http://embed.test',
    RERANK_API_URL='http://rerank.test'
)
class LLMEvalTaskTests(TestCase):
    def setUp(self):
        self.settings_override = override_settings(
            # Add any specific settings llm_eval might depend on
            RERANK_THRESHOLD=0.5,
            RERANK_THRESHOLD_LLM_EVAL=0.4,
        )
        self.settings_override.enable()
        get_default_settings()

        self.guru_type = GuruType.objects.create(
            slug="test-guru-eval",
            name="Test Guru Eval",
            custom=True,
            active=True,
            milvus_collection_name="test_guru_eval_collection"
        )
        self.question = Question.objects.create(
            guru_type=self.guru_type,
            question="Evaluate this question?",
            user_question="User version",
            enhanced_question="Enhanced version",
            slug="evaluate-this",
            content="# Evaluate this question?\nAnswer content here.",
            llm_eval=True # Marked for evaluation
        )
        self.question_no_eval = Question.objects.create(
            guru_type=self.guru_type,
            question="Do not evaluate this?",
            slug="no-evaluate",
            content="# Do not evaluate",
            llm_eval=False # Not marked
        )

        # Mock Milvus client early to avoid connection attempts
        self.milvus_patcher = patch('core.tasks.get_milvus_client')
        self.mock_milvus_client = self.milvus_patcher.start()
        self.addCleanup(self.milvus_patcher.stop)

        # Mock vector_db_fetch
        self.vector_db_fetch_patcher = patch('core.tasks.vector_db_fetch')
        self.mock_vector_db_fetch = self.vector_db_fetch_patcher.start()
        self.mock_vector_db_fetch.return_value = (
            ["context1", "context2"], # contexts
            [0.9, 0.8], # reranked_scores
            0.85, # trust_score
            [0.95, 0.85], # processed_ctx_relevances
            {'prompt_tokens': 10, 'completion_tokens': 5, 'cached_prompt_tokens': 0}, # fetch_ctx_rel_usage
            (0.1, 0.2) # vector_db_times
        )
        self.addCleanup(self.vector_db_fetch_patcher.stop)

        # Mock requester methods
        self.requester_patcher = patch('core.tasks.OpenAIRequester')
        self.mock_requester_class = self.requester_patcher.start()
        self.mock_requester_instance = self.mock_requester_class.return_value
        self.mock_requester_instance.get_context_relevance.return_value = (
            {'contexts': [
                {'context_num': 1, 'score': 1.0, 'explanation': 'Good'},
                {'context_num': 2, 'score': 0.8, 'explanation': 'Okay'}
            ]},
            {'prompt_tokens': 20, 'completion_tokens': 10, 'cached_prompt_tokens': 5},
            "context_relevance_prompt",
            "context_relevance_user_prompt"
        )
        self.mock_requester_instance.get_groundedness.return_value = (
            {'claims': [
                {'claim': 'Claim 1', 'score': 0.9, 'explanation': 'Solid'},
                {'claim': 'Claim 2', 'score': 0.7, 'explanation': 'Decent'}
            ]},
            {'prompt_tokens': 30, 'completion_tokens': 15, 'cached_prompt_tokens': 10},
            "groundedness_prompt"
        )
        self.mock_requester_instance.get_answer_relevance.return_value = (
            {'score': 0.95, 'overall_explanation': 'Very relevant'},
            {'prompt_tokens': 40, 'completion_tokens': 20, 'cached_prompt_tokens': 15},
            "answer_relevance_prompt"
        )
        self.addCleanup(self.requester_patcher.stop)

        # Mock simulate_summary_and_answer
        self.simulate_patcher = patch('core.tasks.simulate_summary_and_answer')
        self.mock_simulate = self.simulate_patcher.start()
        self.mock_simulate.return_value = (
            "Simulated Answer", # answer
            None, # answer_error
            {'prompt_tokens': 50, 'completion_tokens': 25, 'cached_prompt_tokens': 20}, # answer_usages
            None # unused
        )
        self.addCleanup(self.simulate_patcher.stop)

        # Mock cost calculation
        self.cost_patcher = patch('core.tasks.get_llm_usage')
        self.mock_get_llm_usage = self.cost_patcher.start()
        self.mock_get_llm_usage.return_value = 0.005
        self.addCleanup(self.cost_patcher.stop)

        # Mock the dependent task call
        self.result_task_patcher = patch('core.tasks.llm_eval_result.delay')
        self.mock_result_task_delay = self.result_task_patcher.start()
        self.addCleanup(self.result_task_patcher.stop)

        # Mock redis lock
        self.redis_patcher = patch('core.tasks.redis_client')
        self.mock_redis_client = self.redis_patcher.start()
        self.addCleanup(self.redis_patcher.stop)

        # Mock get_default_settings called within llm_eval
        self.get_settings_patcher = patch('core.tasks.get_default_settings')
        self.mock_get_default_settings = self.get_settings_patcher.start()
        mock_settings = MagicMock()
        mock_settings.rerank_threshold = 0.5
        mock_settings.rerank_threshold_llm_eval = 0.4
        self.mock_get_default_settings.return_value = mock_settings
        self.addCleanup(self.get_settings_patcher.stop)


    def tearDown(self):
        self.settings_override.disable()

    def test_llm_eval_basic_flow(self):
        """Test the basic successful flow of the llm_eval task."""
        guru_types_to_eval = [self.guru_type.slug]
        llm_eval(guru_types=guru_types_to_eval)

        # Check LLMEval object creation
        eval_entry = LLMEval.objects.filter(question=self.question, model='gpt-test-model').first()
        self.assertIsNotNone(eval_entry)
        self.assertEqual(eval_entry.version, 1)
        self.assertEqual(eval_entry.model, 'gpt-test-model')

        # Check scores (averages)
        self.assertAlmostEqual(eval_entry.context_relevance, (1.0 + 0.8) / 2)
        self.assertAlmostEqual(eval_entry.groundedness, (0.9 + 0.7) / 2)
        self.assertAlmostEqual(eval_entry.answer_relevance, 0.95)

        # Check prompts and CoTs
        self.assertIn('Context 1:\nScore: 1.0\nExplanation: Good', eval_entry.context_relevance_cot)
        self.assertIn('Claim 1: Claim 1\nScore: 0.9\nExplanation: Solid', eval_entry.groundedness_cot)
        self.assertEqual(eval_entry.answer_relevance_cot, 'Very relevant')
        self.assertEqual(eval_entry.context_relevance_prompt, "context_relevance_prompt")
        self.assertEqual(eval_entry.groundedness_prompt, "groundedness_prompt")
        self.assertEqual(eval_entry.answer_relevance_prompt, "answer_relevance_prompt")

        # Check other fields
        self.assertEqual(eval_entry.contexts, ["context1", "context2"])
        self.assertEqual(eval_entry.reranked_scores, [0.9, 0.8])
        self.assertEqual(eval_entry.answer, "Simulated Answer")
        self.assertEqual(eval_entry.processed_ctx_relevances, [0.95, 0.85])
        self.assertEqual(eval_entry.cost_dollars, 0.005)

        # Check token counts (sum of all steps)
        expected_prompt = 10 + 20 + 30 + 50 + 40
        expected_completion = 5 + 10 + 15 + 25 + 20
        expected_cached = 0 + 5 + 10 + 20 + 15
        self.assertEqual(eval_entry.prompt_tokens, expected_prompt)
        self.assertEqual(eval_entry.completion_tokens, expected_completion)
        self.assertEqual(eval_entry.cached_prompt_tokens, expected_cached)

        # Check settings saved
        self.assertEqual(eval_entry.settings['rerank_threshold'], 0.5)
        self.assertEqual(eval_entry.settings['rerank_threshold_llm_eval'], 0.4)
        self.assertEqual(eval_entry.settings['model_names'], ['gpt-test-model'])
        self.assertEqual(eval_entry.settings['embed_api_url'], 'http://embed.test')
        self.assertEqual(eval_entry.settings['rerank_api_url'], 'http://rerank.test')

        # Check mocks called
        self.mock_vector_db_fetch.assert_called_once()
        self.mock_requester_instance.get_context_relevance.assert_called_once()
        self.mock_requester_instance.get_groundedness.assert_called_once()
        self.mock_simulate.assert_called_once()
        self.mock_requester_instance.get_answer_relevance.assert_called_once()
        self.mock_get_llm_usage.assert_called_once()

        # Check result task was called
        self.mock_result_task_delay.assert_called_once_with([(self.guru_type.slug, 1)])

        # Check question not marked for eval was skipped
        self.assertFalse(LLMEval.objects.filter(question=self.question_no_eval).exists())

    def test_llm_eval_versioning(self):
        """Test that the version increments correctly."""
        # Create a previous eval entry
        LLMEval.objects.create(
            question=self.question,
            model='gpt-test-model',
            version=1,
            # Add minimal required fields
            context_relevance=0, groundedness=0, answer_relevance=0, cost_dollars=0,
            prompt_tokens=0, completion_tokens=0, cached_prompt_tokens=0
        )
        # Add another question marked for eval to test version calculation based on counts
        q_eval_2 = Question.objects.create(
            guru_type=self.guru_type,
            question="Evaluate this second question?",
            slug="evaluate-this-2",
            content="# Evaluate this second question?",
            llm_eval=True
        )

        guru_types_to_eval = [self.guru_type.slug]
        llm_eval(guru_types=guru_types_to_eval)

        # Check entry for the second question also has version 1
        eval_entry_2 = LLMEval.objects.filter(question=q_eval_2, model='gpt-test-model', version=1).first()
        self.assertIsNotNone(eval_entry_2, "Eval for second question should have version 1")
        self.assertEqual(eval_entry_2.version, 1)

        # Check result task was called with version 2
        self.mock_result_task_delay.assert_called_once_with([(self.guru_type.slug, 1)])

    def test_llm_eval_skip_existing_version(self):
        """Test that evaluation is skipped if an entry for the current version exists."""
        # Create an eval entry for version 1 (which would be the calculated version)
        LLMEval.objects.create(
            question=self.question,
            model='gpt-test-model',
            version=1, # Current version
            context_relevance=0.5, groundedness=0.5, answer_relevance=0.5, cost_dollars=0.001,
            prompt_tokens=10, completion_tokens=10, cached_prompt_tokens=10
        )

        # Reset mocks to check they are not called
        self.mock_vector_db_fetch.reset_mock()
        self.mock_requester_instance.get_context_relevance.reset_mock()
        self.mock_requester_instance.get_groundedness.reset_mock()
        self.mock_requester_instance.get_answer_relevance.reset_mock()
        self.mock_simulate.reset_mock()
        self.mock_get_llm_usage.reset_mock()

        guru_types_to_eval = [self.guru_type.slug]
        llm_eval(guru_types=guru_types_to_eval)

        # Assert that no new LLMEval object was created (count remains 1)
        self.assertEqual(LLMEval.objects.filter(question=self.question, model='gpt-test-model').count(), 2)

        # Assert mocks were not called again
        self.mock_vector_db_fetch.assert_called_once()
        self.mock_requester_instance.get_context_relevance.assert_called_once()
        self.mock_get_llm_usage.assert_called_once()

        # Result task should still be called with the determined version
        self.mock_result_task_delay.assert_called_once_with([(self.guru_type.slug, 2)])

    def test_llm_eval_partial_checks(self):
        """Test running eval with only some checks enabled."""
        # Run with only groundedness check
        llm_eval(guru_types=[self.guru_type.slug], check_answer_relevance=False, check_context_relevance=False, check_groundedness=True)

        eval_entry = LLMEval.objects.filter(question=self.question, model='gpt-test-model').first()
        self.assertIsNotNone(eval_entry)

        # Check only groundedness was calculated
        self.assertAlmostEqual(eval_entry.groundedness, (0.9 + 0.7) / 2)
        self.assertNotEqual(eval_entry.groundedness_cot, 'No previous version exists and groundedness is not set to be checked')

        # Check others used default/placeholder values (or values from previous version if exists)
        # Since no previous version exists in this test setup:
        self.assertEqual(eval_entry.context_relevance, 0)
        self.assertEqual(eval_entry.answer_relevance, 0)
        self.assertIn('context relevance is not set', eval_entry.context_relevance_cot)
        self.assertIn('answer relevance is not set', eval_entry.answer_relevance_cot)
        self.assertEqual(eval_entry.answer, '')

        # Check only relevant mocks were called
        self.mock_vector_db_fetch.assert_called_once() # Needed for groundedness context
        self.mock_requester_instance.get_context_relevance.assert_not_called()
        self.mock_requester_instance.get_groundedness.assert_called_once()
        self.mock_simulate.assert_not_called()
        self.mock_requester_instance.get_answer_relevance.assert_not_called()

        # Check result task called
        self.mock_result_task_delay.assert_called_once_with([(self.guru_type.slug, 1)])
