from django.conf import settings
from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework.test import APIClient
from core.models import Question, GuruType
from django.contrib.auth import get_user_model
from core.utils import get_default_settings
from unittest.mock import patch

class FollowUpExamplesTests(TestCase):
    def setUp(self):
        get_default_settings()
        self.client = APIClient()
        get_user_model().objects.create_superuser(email=settings.ROOT_EMAIL, password=settings.ROOT_PASSWORD, name='Admin')
        self.user = get_user_model().objects.create_user(
            email='testuser@test.com',
            name='Test User',
            password='testpass123'
        )
        if settings.ENV != 'selfhosted':
            self.client.force_authenticate(user=self.user)
        
        # Create test data
        self.guru_type = GuruType.objects.create(
            active=True,
            name='Test Guru',
            slug='test-guru'
        )
        
        # Create a question with processed contexts
        self.question = Question.objects.create(
            slug='test-question',
            question="What is Test Guru?",
            guru_type=self.guru_type,
            content="Test Guru is a testing framework.",
            processed_ctx_relevances={
                'kept': [
                    {
                        'context': "Test Guru is a comprehensive testing framework that helps developers write better tests.",
                        'score': 0.9,
                        'explanation': "Directly relevant to the question"
                    },
                    {
                        'context': "Test Guru provides features like mocking, assertions, and test organization.",
                        'score': 0.8,
                        'explanation': "Describes key features"
                    }
                ]
            }
        )

    @override_settings(ENV='dev')
    @patch('core.requester.GeminiRequester.generate_follow_up_questions')
    def test_follow_up_examples_generation_cloud(self, mock_generate):
        # Mock the Gemini response
        mock_generate.return_value = ["What are the key features of Test Guru?", "How does Test Guru help with testing?"]
        
        response = self.client.post(
            reverse('follow_up_examples', kwargs={'guru_type': self.guru_type.slug}),
            {'question_slug': self.question.slug}
        )
        
        self.assertEqual(response.status_code, 200)
        self.assertTrue(isinstance(response.data, list))
        self.assertEqual(len(response.data), 2)
        self.assertEqual(response.data, ["What are the key features of Test Guru?", "How does Test Guru help with testing?"])
        
        # Verify the mock was called with correct arguments
        mock_generate.assert_called_once()
        call_args = mock_generate.call_args[1]
        self.assertEqual(len(call_args['questions']), 1)  # Only one question in history
        self.assertEqual(call_args['last_content'], "Test Guru is a testing framework.")
        self.assertEqual(call_args['guru_type'], self.guru_type)
        self.assertEqual(len(call_args['contexts']), 2)  # Two contexts from processed_ctx_relevances

    @override_settings(ENV='selfhosted')
    @patch('core.requester.OpenAIRequester.generate_follow_up_questions')
    def test_follow_up_examples_generation_selfhosted(self, mock_generate):
        # Mock the OpenAI response
        mock_generate.return_value = ["Can you explain more about Test Guru's testing capabilities?", "What makes Test Guru different from other testing frameworks?"]
        
        response = self.client.post(
            reverse('follow_up_examples', kwargs={'guru_type': self.guru_type.slug}),
            {'question_slug': self.question.slug}
        )
        
        self.assertEqual(response.status_code, 200)
        self.assertTrue(isinstance(response.data, list))
        self.assertEqual(len(response.data), 2)
        self.assertEqual(response.data, ["Can you explain more about Test Guru's testing capabilities?", "What makes Test Guru different from other testing frameworks?"])
        
        # Verify the mock was called with correct arguments
        mock_generate.assert_called_once()
        call_args = mock_generate.call_args[1]
        self.assertEqual(len(call_args['questions']), 1)  # Only one question in history
        self.assertEqual(call_args['last_content'], "Test Guru is a testing framework.")
        self.assertEqual(call_args['guru_type'], self.guru_type)
        self.assertEqual(len(call_args['contexts']), 2)  # Two contexts from processed_ctx_relevances

    def test_follow_up_examples_no_contexts(self):
        # Create a question without contexts
        question = Question.objects.create(
            slug='test-question-2',
            question="Another test question",
            guru_type=self.guru_type,
            processed_ctx_relevances={'kept': []}
        )
        
        response = self.client.post(
            reverse('follow_up_examples', kwargs={'guru_type': self.guru_type.slug}),
            {'question_slug': question.slug}
        )
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, [])
        
    def test_follow_up_examples_cached(self):
        # Test that cached follow-up questions are returned
        self.question.follow_up_questions = ["Cached question 1?", "Cached question 2?"]
        self.question.save()
        
        response = self.client.post(
            reverse('follow_up_examples', kwargs={'guru_type': self.guru_type.slug}),
            {'question_slug': self.question.slug}
        )
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, ["Cached question 1?", "Cached question 2?"])
        
    def test_follow_up_examples_invalid_question(self):
        response = self.client.post(
            reverse('follow_up_examples', kwargs={'guru_type': self.guru_type.slug}),
            {'question_slug': 'invalid-slug'}
        )
        
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data, {'msg': 'Question does not exist'})
