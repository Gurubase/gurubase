from django.test import TestCase
from unittest.mock import patch, MagicMock, call
from django.conf import settings

from core.utils import get_default_settings
from core.tasks import generate_questions_from_summaries, generate_questions_from_summaries_for_guru_type
from core.models import GuruType, Summarization, SummaryQuestionGeneration


class GenerateQuestionsFromSummariesTaskTests(TestCase):
    def setUp(self):
        """Set up test fixtures for all tests."""
        # Create GuruType test objects
        get_default_settings()
        self.guru_type1 = GuruType.objects.create(
            slug="python",
            name="Python",
            custom=True,
            active=True
        )
        
        self.guru_type2 = GuruType.objects.create(
            slug="javascript",
            name="JavaScript",
            custom=True,
            active=True
        )
    
    @patch('core.tasks.generate_questions_from_summaries_for_guru_type')
    def test_generate_questions_from_summaries_with_specific_slugs(self, mock_generate):
        """Test generate_questions_from_summaries with specific guru type slugs."""
        # Call the function with specific slugs
        generate_questions_from_summaries(guru_type_slugs=['python', 'javascript'])
        
        # Assert that generate_questions_from_summaries_for_guru_type was called for each slug
        mock_generate.assert_has_calls([
            call(guru_type_slug='python', guru_type=self.guru_type1),
            call(guru_type_slug='javascript', guru_type=self.guru_type2)
        ])
    
    @patch('core.tasks.generate_questions_from_summaries_for_guru_type')
    def test_generate_questions_from_summaries_with_wildcard(self, mock_generate):
        """Test generate_questions_from_summaries with wildcard to process all guru types."""
        # Call the function with wildcard
        generate_questions_from_summaries(guru_type_slugs=['*'])
        
        # Assert that generate_questions_from_summaries_for_guru_type was called for all guru types
        # The order of calls depends on the order of GuruType.objects.all()
        mock_generate.assert_has_calls([
            call(guru_type_slug='python', guru_type=self.guru_type1),
            call(guru_type_slug='javascript', guru_type=self.guru_type2)
        ])
    
    @patch('core.tasks.logger')
    @patch('core.tasks.generate_questions_from_summaries_for_guru_type')
    def test_generate_questions_from_summaries_with_nonexistent_slug(self, mock_generate, mock_logger):
        """Test handling of nonexistent guru type slugs."""
        # Call the function with nonexistent slug
        generate_questions_from_summaries(guru_type_slugs=['nonexistent'])
        
        # Assert that generate_questions_from_summaries_for_guru_type was not called
        mock_generate.assert_not_called()
        
        # Assert that error was logged
        mock_logger.error.assert_called_once()


class GenerateQuestionsFromSummariesForGuruTypeTaskTests(TestCase):
    def setUp(self):
        """Set up test fixtures for all tests."""
        # Create test guru type
        get_default_settings()
        self.guru_type = GuruType.objects.create(
            slug="python",
            name="Python",
            custom=True,
            active=True
        )
        
        # Create test summarizations
        self.summarization1 = Summarization.objects.create(
            is_data_source_summarization=True,
            initial=True,
            question_generation_ref=None,
            guru_type=self.guru_type,
            summary_suitable=True,
            result_content="Python is a programming language."
        )
        
        self.summarization2 = Summarization.objects.create(
            is_data_source_summarization=True,
            initial=True,
            question_generation_ref=None,
            guru_type=self.guru_type,
            summary_suitable=True,
            result_content="Python has many libraries."
        )
        
        # Summarization with no guru type
        self.summarization_no_guru_type = Summarization.objects.create(
            is_data_source_summarization=True,
            initial=True,
            question_generation_ref=None,
            guru_type=None,
            summary_suitable=True,
            result_content="This has no guru type."
        )
        
        # Configuration settings
        settings.GENERATED_QUESTION_PER_GURU_LIMIT = 10
        settings.QUESTION_GENERATION_COUNT = 2  # Each summary should generate 2 questions
    
    @patch('core.tasks.guru_type_has_enough_generated_questions')
    @patch('core.tasks.generate_questions_from_summary')
    @patch('core.tasks.SummaryQuestionGeneration.objects.create')
    def test_generate_questions_for_guru_type_basic_flow(self, mock_create, mock_generate, mock_has_enough):
        """Test the basic flow of generate_questions_from_summaries_for_guru_type."""
        # Setup mocks
        mock_has_enough.return_value = (False, 0)  # Not enough questions, 0 generated so far
        
        mock_generate.return_value = (
            {
                'summary_sufficient': True,
                'questions': ['What is Python?', 'What are Python libraries?']
            },
            'gpt-4',
            {'prompt_tokens': 100, 'completion_tokens': 50}
        )
        
        object = SummaryQuestionGeneration(
            summarization=self.summarization1,
        )
        object.save()
        mock_create.return_value = object
        
        # Call the function
        generate_questions_from_summaries_for_guru_type(guru_type_slug='python', guru_type=self.guru_type)
        
        # Assert mocks were called correctly
        mock_has_enough.assert_called_once_with(self.guru_type)
        
        # Should be called twice, once for each summarization
        self.assertEqual(mock_generate.call_count, 2)
        
        # Check SummaryQuestionGeneration.objects.create was called
        self.assertEqual(mock_create.call_count, 2)
    
    @patch('core.tasks.guru_type_has_enough_generated_questions')
    @patch('core.tasks.generate_questions_from_summary')
    def test_generate_questions_for_guru_type_already_enough(self, mock_generate, mock_has_enough):
        """Test when guru type already has enough generated questions."""
        # Setup mock to indicate enough questions already
        mock_has_enough.return_value = (True, 10)  # Enough questions, 10 generated
        
        # Call the function
        generate_questions_from_summaries_for_guru_type(guru_type_slug='python', guru_type=self.guru_type)
        
        # Assert that generate_questions_from_summary was not called
        mock_generate.assert_not_called()
    
    @patch('core.tasks.guru_type_has_enough_generated_questions')
    @patch('core.tasks.logger')
    @patch('core.tasks.generate_questions_from_summary')
    @patch('core.tasks.SummaryQuestionGeneration.objects.create')
    def test_generate_questions_for_guru_type_no_guru_type(self, mock_create, mock_generate, 
                                                       mock_logger, mock_has_enough):
        """Test handling of summarizations with no guru type."""
        # Setup mocks
        mock_has_enough.return_value = (False, 0)
        
        # Make all summarizations except the one without guru type unavailable
        Summarization.objects.filter(guru_type__isnull=False).delete()
        
        # Create a new summarization with no guru type to ensure it's included in the query
        Summarization.objects.create(
            is_data_source_summarization=True,
            initial=True,
            question_generation_ref=None,
            guru_type=None,
            summary_suitable=True,
            result_content="Another with no guru type."
        )
        
        # Call the function
        generate_questions_from_summaries_for_guru_type(guru_type_slug='python', guru_type=self.guru_type)
        
        # No questions should be generated
        mock_generate.assert_not_called()
    
    @patch('core.tasks.guru_type_has_enough_generated_questions')
    @patch('core.tasks.logger')
    @patch('core.tasks.generate_questions_from_summary')
    @patch('core.tasks.SummaryQuestionGeneration.objects.create')
    def test_generate_questions_for_guru_type_error_handling(self, mock_create, mock_generate, 
                                                        mock_logger, mock_has_enough):
        """Test error handling during question generation."""
        # Setup mocks
        mock_has_enough.return_value = (False, 0)
        mock_generate.side_effect = Exception("Test error")
        
        # Call the function - should raise exception
        with self.assertRaises(Exception):
            generate_questions_from_summaries_for_guru_type(guru_type_slug='python', guru_type=self.guru_type)
    
    @patch('core.tasks.guru_type_has_enough_generated_questions')
    @patch('core.tasks.generate_questions_from_summary')
    @patch('core.tasks.SummaryQuestionGeneration.objects.create')
    def test_generate_questions_stops_at_limit(self, mock_create, mock_generate, mock_has_enough):
        """Test that generation stops when question limit is reached."""
        # Setup mocks
        mock_has_enough.return_value = (False, 8)  # 8 questions already generated, limit is 10
        
        mock_generate.return_value = (
            {
                'summary_sufficient': True,
                'questions': ['What is Python?', 'What are Python libraries?']  # This will add 2 more, reaching the limit
            },
            'gpt-4',
            {'prompt_tokens': 100, 'completion_tokens': 50}
        )
        
        # Create a mock for the created SummaryQuestionGeneration
        mock_question_gen = SummaryQuestionGeneration(
            summarization=self.summarization1,
        )
        mock_question_gen.save()
        mock_create.return_value = mock_question_gen
        
        # Call the function
        generate_questions_from_summaries_for_guru_type(guru_type_slug='python', guru_type=self.guru_type)
        
        # Should only process one summarization before reaching limit
        self.assertEqual(mock_generate.call_count, 1)
        self.assertEqual(mock_create.call_count, 1)
