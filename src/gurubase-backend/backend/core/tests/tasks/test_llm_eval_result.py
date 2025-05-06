from django.test import TestCase
from django.conf import settings
from statistics import median, mean, stdev
from core.models import GuruType, Question, LLMEval, LLMEvalResult
from core.tasks import llm_eval_result
from core.utils import get_default_settings


class TestLLMEvalResult(TestCase):
    def setUp(self):
        """
        Set up the test environment with necessary objects:
        1. Default settings
        2. A GuruType
        3. Questions for that GuruType
        4. LLMEval entries with sample metrics
        """
        # Initialize default settings
        get_default_settings()
        
        # Create a test GuruType
        self.guru_type = GuruType.objects.create(
            slug="test-guru", 
            name="Test Guru", 
            custom=True, 
            active=True
        )
        
        # Create test questions
        self.questions = []
        for i in range(5):
            question = Question.objects.create(
                question=f"Test Question {i}",
                slug=f"test-question-{i}",
                guru_type=self.guru_type,
                llm_eval=True,
                content=f"# Test Question {i}\n\nThis is a test question content."
            )
            self.questions.append(question)
        
        # Sample test data for metrics
        self.version = 1
        self.model = settings.GPT_MODEL
        
        # LLMEval test data with varying scores
        self.create_test_llm_eval_data()
        
        # Expected metrics to verify
        self.context_relevance_values = [0.8, 0.7, 0.9, 0.0, 0.75]
        self.groundedness_values = [0.9, 0.85, 0.0, 0.95, 0.8]
        self.answer_relevance_values = [0.75, 0.0, 0.8, 0.9, 0.85]
        
        # Sample settings to verify in results
        self.test_settings = {
            "rerank_threshold": 0.5,
            "rerank_threshold_llm_eval": 0.4,
            "model_names": ["gpt-4"],
            "embed_api_url": "https://test-api.com/embed",
            "rerank_api_url": "https://test-api.com/rerank"
        }

    def create_test_llm_eval_data(self):
        """Create test LLMEval objects with various metrics"""
        # Create LLMEval entries with varying scores including some zeros
        test_data = [
            {"context_relevance": 0.8, "groundedness": 0.9, "answer_relevance": 0.75},
            {"context_relevance": 0.7, "groundedness": 0.85, "answer_relevance": 0.0},
            {"context_relevance": 0.9, "groundedness": 0.0, "answer_relevance": 0.8},
            {"context_relevance": 0.0, "groundedness": 0.95, "answer_relevance": 0.9},
            {"context_relevance": 0.75, "groundedness": 0.8, "answer_relevance": 0.85},
        ]
        
        for i, data in enumerate(test_data):
            LLMEval.objects.create(
                question=self.questions[i],
                version=self.version,
                model=self.model,
                context_relevance=data["context_relevance"],
                groundedness=data["groundedness"],
                answer_relevance=data["answer_relevance"],
                context_relevance_cot="Test explanation",
                groundedness_cot="Test explanation",
                answer_relevance_cot="Test explanation",
                cost_dollars=0.05,
                prompt_tokens=100,
                completion_tokens=50,
                cached_prompt_tokens=0,
            )

    def test_llm_eval_result_creates_result_object(self):
        """Test that llm_eval_result creates a LLMEvalResult object with correct data"""
        # Call the function being tested
        llm_eval_result([(self.guru_type.slug, self.version)])
        
        # Check that the result was created
        result = LLMEvalResult.objects.filter(
            guru_type=self.guru_type,
            version=self.version,
            model=self.model
        ).first()
        
        self.assertIsNotNone(result, "LLMEvalResult object should be created")
        
        # Calculate expected values manually to verify against result
        non_zero_context = [v for v in self.context_relevance_values if v != 0]
        non_zero_groundedness = [v for v in self.groundedness_values if v != 0]
        non_zero_answer = [v for v in self.answer_relevance_values if v != 0]
        
        # Verify metrics including zeros
        self.assertAlmostEqual(result.context_relevance_avg, sum(self.context_relevance_values) / 5, places=2)
        self.assertAlmostEqual(result.groundedness_avg, sum(self.groundedness_values) / 5, places=2)
        self.assertAlmostEqual(result.answer_relevance_avg, sum(self.answer_relevance_values) / 5, places=2)
        self.assertAlmostEqual(result.context_relevance_median, median(self.context_relevance_values), places=2)
        self.assertAlmostEqual(result.groundedness_median, median(self.groundedness_values), places=2)
        self.assertAlmostEqual(result.answer_relevance_median, median(self.answer_relevance_values), places=2)
        
        # Verify non-zero metrics
        self.assertAlmostEqual(result.context_relevance_non_zero_avg, mean(non_zero_context), places=2)
        self.assertAlmostEqual(result.groundedness_non_zero_avg, mean(non_zero_groundedness), places=2)
        self.assertAlmostEqual(result.answer_relevance_non_zero_avg, mean(non_zero_answer), places=2)
        self.assertAlmostEqual(result.context_relevance_non_zero_median, median(non_zero_context), places=2)
        self.assertAlmostEqual(result.groundedness_non_zero_median, median(non_zero_groundedness), places=2)
        self.assertAlmostEqual(result.answer_relevance_non_zero_median, median(non_zero_answer), places=2)
        
        # Verify counts
        self.assertEqual(result.total_questions, 5)
        self.assertEqual(result.context_relevance_non_zero_count, 4)
        self.assertEqual(result.groundedness_non_zero_count, 4)
        self.assertEqual(result.answer_relevance_non_zero_count, 4)
        
    def test_llm_eval_result_updates_existing_result(self):
        """Test that llm_eval_result updates an existing LLMEvalResult object"""
        # Create an existing result with different metrics
        initial_result = LLMEvalResult.objects.create(
            guru_type=self.guru_type,
            version=self.version,
            model=self.model,
            context_relevance_avg=0.5,
            groundedness_avg=0.5,
            answer_relevance_avg=0.5,
            settings={"old_setting": "value"},
            context_relevance_median=0.5,
            groundedness_median=0.5,
            answer_relevance_median=0.5,
            context_relevance_non_zero_avg=0.5,
            groundedness_non_zero_avg=0.5,
            answer_relevance_non_zero_avg=0.5,
            context_relevance_non_zero_median=0.5,
            groundedness_non_zero_median=0.5,
            context_relevance_std=0.5,
            groundedness_std=0.5,
            answer_relevance_std=0.5,
            total_questions=5,
            total_cost=0.25,
        )
        
        # Call the function being tested
        llm_eval_result([(self.guru_type.slug, self.version)])
        
        # Check that the result was updated
        updated_result = LLMEvalResult.objects.get(id=initial_result.id)
        
        # Verify the metrics were updated
        self.assertNotEqual(updated_result.context_relevance_avg, 0.5)
        
    def test_llm_eval_result_handles_multiple_pairs(self):
        """Test that llm_eval_result handles multiple pairs correctly"""
        # Create another GuruType and related data
        second_guru_type = GuruType.objects.create(
            slug="second-guru", 
            name="Second Guru", 
            custom=True, 
            active=True
        )
        
        # Create a question for the second GuruType
        second_question = Question.objects.create(
            question="Second Question",
            guru_type=second_guru_type,
            llm_eval=True,
            content="# Second Question\n\nThis is a test."
        )
        
        # Create LLMEval for the second GuruType
        LLMEval.objects.create(
            question=second_question,
            version=2,
            model=self.model,
            context_relevance=0.95,
            groundedness=0.9,
            answer_relevance=0.85,
            context_relevance_cot="Test explanation",
            groundedness_cot="Test explanation",
            answer_relevance_cot="Test explanation",
            cost_dollars=0.05,
            prompt_tokens=100,
            completion_tokens=50,
            cached_prompt_tokens=0,
            settings={"different": "settings"}
        )
        
        # Call the function with multiple pairs
        llm_eval_result([
            (self.guru_type.slug, self.version),
            (second_guru_type.slug, 2)
        ])
        
        # Check that both results were created
        first_result = LLMEvalResult.objects.filter(
            guru_type=self.guru_type,
            version=self.version
        ).first()
        
        second_result = LLMEvalResult.objects.filter(
            guru_type=second_guru_type,
            version=2
        ).first()
        
        self.assertIsNotNone(first_result)
        self.assertIsNotNone(second_result)
        self.assertEqual(second_result.total_questions, 1)
        self.assertEqual(second_result.context_relevance_avg, 0.95)
        
    def test_llm_eval_result_handles_missing_evals(self):
        """Test that llm_eval_result handles the case where no LLMEval objects exist"""
        # Create a GuruType with no LLMEval objects
        empty_guru_type = GuruType.objects.create(
            slug="empty-guru", 
            name="Empty Guru", 
            custom=True, 
            active=True
        )
        
        # Call the function
        llm_eval_result([(empty_guru_type.slug, 1)])
        
        # Verify no LLMEvalResult was created
        result = LLMEvalResult.objects.filter(
            guru_type=empty_guru_type,
            version=1
        ).first()
        
        self.assertIsNone(result)
