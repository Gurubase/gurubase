from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from core.models import Question, GuruType
from django.contrib.auth import get_user_model

class FollowUpExamplesTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email='testuser@test.com',
            name='Test User',
            password='testpass123'
        )
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
        
    def test_follow_up_examples_generation(self):
        response = self.client.post(
            reverse('follow_up_examples', kwargs={'guru_type': self.guru_type.slug}),
            {'question_slug': self.question.slug}
        )
        
        self.assertEqual(response.status_code, 200)
        self.assertTrue(isinstance(response.data, list))
        self.assertGreater(len(response.data), 0)

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
