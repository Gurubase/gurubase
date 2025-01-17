from django.test import TestCase
from core.models import Question, GuruType
from accounts.models import User
from django.db.models import Q
from core.utils import search_question
from datetime import datetime, timezone

class SearchQuestionTests(TestCase):
    def setUp(self):
        # Create test guru type
        self.guru_type = GuruType.objects.create(
            name="Test Guru",
            slug="test-guru"
        )
        
        # Create test users
        self.user1 = User.objects.create(email="user1@test.com")
        self.user2 = User.objects.create(email="user2@test.com")
        self.admin_user = User.objects.create(email="admin@test.com", is_admin=True)
        
        # Create regular questions
        self.regular_question = Question.objects.create(
            question="Regular question",
            slug="regular-question",
            guru_type=self.guru_type,
            source=Question.Source.USER.value
        )
        
        # Create widget questions
        self.widget_question = Question.objects.create(
            question="Widget question",
            slug="widget-question",
            guru_type=self.guru_type,
            source=Question.Source.WIDGET_QUESTION.value
        )
        
        # Create API questions for different users
        self.api_question_user1 = Question.objects.create(
            question="API question user1",
            slug="api-question-user1",
            guru_type=self.guru_type,
            source=Question.Source.API.value,
            user=self.user1
        )
        
        self.api_question_user2 = Question.objects.create(
            question="API question user2",
            slug="api-question-user2",
            guru_type=self.guru_type,
            source=Question.Source.API.value,
            user=self.user2
        )

    def test_anonymous_user_regular_search(self):
        """Test anonymous user can find regular questions but not API/widget questions"""
        # Should find regular question
        result = search_question(
            user=None,
            guru_type_object=self.guru_type,
            binge=None,
            slug="regular-question"
        )
        self.assertEqual(result, self.regular_question)
        
        # Should not find widget question
        result = search_question(
            user=None,
            guru_type_object=self.guru_type,
            binge=None,
            slug="widget-question"
        )
        self.assertIsNone(result)
        
        # Should not find API question
        result = search_question(
            user=None,
            guru_type_object=self.guru_type,
            binge=None,
            slug="api-question-user1"
        )
        self.assertIsNone(result)

    def test_anonymous_user_widget_search(self):
        """Test anonymous user can find widget questions when include_widget=True"""
        # Should find widget question
        result = search_question(
            user=None,
            guru_type_object=self.guru_type,
            binge=None,
            slug="widget-question",
            only_widget=True
        )
        self.assertEqual(result, self.widget_question)
        
        # Should not find regular question when only including widget
        result = search_question(
            user=None,
            guru_type_object=self.guru_type,
            binge=None,
            slug="regular-question",
            only_widget=True
        )
        self.assertIsNone(result)

    def test_authenticated_user_api_search(self):
        """Test authenticated user can find their own API questions when include_api=True"""
        # User1 should find their own API question
        result = search_question(
            user=self.user1,
            guru_type_object=self.guru_type,
            binge=None,
            slug="api-question-user1",
            include_api=True
        )
        self.assertEqual(result, self.api_question_user1)
        
        # User1 should not find user2's API question
        result = search_question(
            user=self.user1,
            guru_type_object=self.guru_type,
            binge=None,
            slug="api-question-user2",
            include_api=True
        )
        self.assertIsNone(result)

    def test_admin_user_search(self):
        """Test admin user can find all questions"""
        # Admin should find regular question
        result = search_question(
            user=self.admin_user,
            guru_type_object=self.guru_type,
            binge=None,
            slug="regular-question"
        )
        self.assertEqual(result, self.regular_question)
        
        # Admin should find widget question
        result = search_question(
            user=self.admin_user,
            guru_type_object=self.guru_type,
            binge=None,
            slug="widget-question"
        )
        self.assertEqual(result, self.widget_question)
        
        # Admin should find any API question
        result = search_question(
            user=self.admin_user,
            guru_type_object=self.guru_type,
            binge=None,
            slug="api-question-user1"
        )
        self.assertEqual(result, self.api_question_user1)

    def test_search_by_question_text(self):
        """Test searching by question text instead of slug"""
        # Regular user should find regular question
        result = search_question(
            user=self.user1,
            guru_type_object=self.guru_type,
            binge=None,
            question="Regular question"
        )
        self.assertEqual(result, self.regular_question)
        
        # Should find case-insensitive
        result = search_question(
            user=self.user1,
            guru_type_object=self.guru_type,
            binge=None,
            question="REGULAR QUESTION"
        )
        self.assertEqual(result, self.regular_question)

    def test_search_with_user_question(self):
        """Test searching by user_question field"""
        # Create question with different user_question
        question = Question.objects.create(
            question="DB Question",
            user_question="How to use PostgreSQL?",
            slug="db-question",
            guru_type=self.guru_type,
            source=Question.Source.USER.value
        )
        
        # Should find by user_question
        result = search_question(
            user=None,
            guru_type_object=self.guru_type,
            binge=None,
            question="How to use PostgreSQL?"
        )
        self.assertEqual(result, question)
        
        # Should find case-insensitive
        result = search_question(
            user=None,
            guru_type_object=self.guru_type,
            binge=None,
            question="HOW TO USE POSTGRESQL?"
        )
        self.assertEqual(result, question)

    def test_invalid_search_parameters(self):
        """Test error handling for invalid search parameters"""
        # Should raise assertion error when neither slug nor question provided
        with self.assertRaises(AssertionError):
            search_question(
                user=None,
                guru_type_object=self.guru_type,
                binge=None
            )

    def test_search_with_binge(self):
        """Test searching questions within a specific binge"""
        from core.models import Binge
        
        # Create a binge
        binge = Binge.objects.create(
            guru_type=self.guru_type,
            owner=self.user1
        )
        
        # Create a question in the binge
        binge_question = Question.objects.create(
            question="Binge question",
            slug="binge-question",
            guru_type=self.guru_type,
            source=Question.Source.USER.value,
            binge=binge
        )
        
        # Create same question outside binge
        non_binge_question = Question.objects.create(
            question="Binge question",
            slug="binge-question-2",
            guru_type=self.guru_type,
            source=Question.Source.USER.value
        )
        
        # Should find question in binge
        result = search_question(
            user=self.user1,
            guru_type_object=self.guru_type,
            binge=binge,
            slug="binge-question"
        )
        self.assertEqual(result, binge_question)
        
        # Should not find non-binge question when searching in binge
        result = search_question(
            user=self.user1,
            guru_type_object=self.guru_type,
            binge=binge,
            slug="binge-question-2"
        )
        self.assertIsNone(result) 

    def test_duplicate_questions(self):
        """Test duplicate question handling for different source types"""
        
        # API questions should return most recent for same user
        older_api = Question.objects.create(
            question="API duplicate",
            slug="api-duplicate-1",
            guru_type=self.guru_type,
            source=Question.Source.API.value,
            user=self.user1,
            date_updated=datetime(2023, 1, 1, tzinfo=timezone.utc)
        )
        
        newer_api = Question.objects.create(
            question="API duplicate",
            slug="api-duplicate-2", 
            guru_type=self.guru_type,
            source=Question.Source.API.value,
            user=self.user1,
            date_updated=datetime(2023, 1, 2, tzinfo=timezone.utc)
        )
        
        # Should return newer API question for same user
        result = search_question(
            user=self.user1,
            guru_type_object=self.guru_type,
            binge=None,
            question="API duplicate",
            include_api=True
        )
        self.assertEqual(result, newer_api)
        
        # Different user's API duplicate should be separate
        other_user_api = Question.objects.create(
            question="API duplicate",
            slug="api-duplicate-3",
            guru_type=self.guru_type,
            source=Question.Source.API.value,
            user=self.user2,
            date_updated=datetime(2023, 1, 3, tzinfo=timezone.utc)
        )
        
        # Should still return user1's newest API question
        result = search_question(
            user=self.user1,
            guru_type_object=self.guru_type,
            binge=None,
            question="API duplicate",
            include_api=True
        )
        self.assertEqual(result, newer_api)
        
        # Test binge duplicates
        from core.models import Binge
        
        binge1 = Binge.objects.create(
            guru_type=self.guru_type,
            owner=self.user1
        )
        
        binge2 = Binge.objects.create(
            guru_type=self.guru_type,
            owner=self.user1
        )
        
        # Create duplicate questions in different binges
        binge1_question = Question.objects.create(
            question="Binge duplicate",
            slug="binge-duplicate-1",
            guru_type=self.guru_type,
            source=Question.Source.USER.value,
            binge=binge1,
            date_updated=datetime(2023, 1, 1, tzinfo=timezone.utc)
        )
        
        binge2_question = Question.objects.create(
            question="Binge duplicate",
            slug="binge-duplicate-2",
            guru_type=self.guru_type,
            source=Question.Source.USER.value,
            binge=binge2,
            date_updated=datetime(2023, 1, 2, tzinfo=timezone.utc)
        )
        
        # Should find correct question in each binge regardless of date
        result = search_question(
            user=self.user1,
            guru_type_object=self.guru_type,
            binge=binge1,
            question="Binge duplicate"
        )
        self.assertEqual(result, binge1_question)
        
        result = search_question(
            user=self.user1,
            guru_type_object=self.guru_type,
            binge=binge2,
            question="Binge duplicate"
        )
        self.assertEqual(result, binge2_question) 