from django.conf import settings
from django.test import TestCase
from core.models import Question, GuruType
from accounts.models import User
from django.db.models import Q
from core.utils import search_question
from core.utils import get_default_settings
from datetime import datetime, timezone

class SearchQuestionTests(TestCase):
    def setUp(self):
        # Create test guru type
        get_default_settings()
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

        # Create Slack and Discord questions
        self.slack_question = Question.objects.create(
            question="Slack question",
            slug="slack-question",
            guru_type=self.guru_type,
            source=Question.Source.SLACK.value
        )

        self.discord_question = Question.objects.create(
            question="Discord question",
            slug="discord-question",
            guru_type=self.guru_type,
            source=Question.Source.DISCORD.value
        )

        # Create bot questions (using SLACK and DISCORD sources)
        self.bot_question_slack = Question.objects.create(
            question="Bot question via Slack",
            slug="bot-question-slack",
            guru_type=self.guru_type,
            source=Question.Source.SLACK.value,
            user=self.user1
        )

        self.bot_question_discord = Question.objects.create(
            question="Bot question via Discord",
            slug="bot-question-discord",
            guru_type=self.guru_type,
            source=Question.Source.DISCORD.value,
            user=self.user2
        )

        # Create Github questions
        self.github_question = Question.objects.create(
            question="Github question",
            slug="github-question",
            guru_type=self.guru_type,
            source=Question.Source.GITHUB.value
        )

        self.bot_question_github = Question.objects.create(
            question="Bot question via Github",
            slug="bot-question-github",
            guru_type=self.guru_type,
            source=Question.Source.GITHUB.value,
            user=self.user1
        )

    def test_anonymous_user_regular_search(self):
        """Test anonymous user can find regular questions, Slack questions, Discord questions, and Github questions but not API/widget questions"""
        # Should find regular question
        result = search_question(
            user=None,
            guru_type_object=self.guru_type,
            binge=None,
            slug="regular-question"
        )
        self.assertEqual(result, self.regular_question)
        
        # Should find Slack question
        result = search_question(
            user=None,
            guru_type_object=self.guru_type,
            binge=None,
            slug="slack-question"
        )
        self.assertEqual(result, self.slack_question)

        # Should find Discord question
        result = search_question(
            user=None,
            guru_type_object=self.guru_type,
            binge=None,
            slug="discord-question"
        )
        self.assertEqual(result, self.discord_question)

        # Should find Github question
        result = search_question(
            user=None,
            guru_type_object=self.guru_type,
            binge=None,
            slug="github-question"
        )
        self.assertEqual(result, self.github_question)
        
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
        """Test authenticated user can find their own API questions and integration questions when include_api=True"""
        # User1 should find their own API question
        result = search_question(
            user=self.user1,
            guru_type_object=self.guru_type,
            binge=None,
            slug="api-question-user1",
            include_api=True
        )
        self.assertEqual(result, self.api_question_user1)
        
        # User1 should not find user2's API question (for non selfhosted)
        result = search_question(
            user=self.user1,
            guru_type_object=self.guru_type,
            binge=None,
            slug="api-question-user2",
            include_api=True
        )
        if settings.ENV != 'selfhosted':
            self.assertIsNone(result)
        else:
            self.assertEqual(result, self.api_question_user2)

        # User1 should find Slack question with include_api=True
        result = search_question(
            user=self.user1,
            guru_type_object=self.guru_type,
            binge=None,
            slug="slack-question",
            include_api=True
        )
        self.assertEqual(result, self.slack_question)

        # User1 should find Discord question with include_api=True
        result = search_question(
            user=self.user1,
            guru_type_object=self.guru_type,
            binge=None,
            slug="discord-question",
            include_api=True
        )
        self.assertEqual(result, self.discord_question)

    def test_authenticated_user_without_api(self):
        """Test authenticated user without include_api flag"""
        # Should not find API questions when include_api=False
        result = search_question(
            user=self.user1,
            guru_type_object=self.guru_type,
            binge=None,
            slug="api-question-user1",
            include_api=False
        )
        self.assertIsNone(result)

        # Should not find widget questions
        result = search_question(
            user=self.user1,
            guru_type_object=self.guru_type,
            binge=None,
            slug="widget-question",
            include_api=False
        )
        self.assertIsNone(result)

        # Should still find regular questions
        result = search_question(
            user=self.user1,
            guru_type_object=self.guru_type,
            binge=None,
            slug="regular-question",
            include_api=False
        )
        self.assertEqual(result, self.regular_question)

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
            slug="widget-question",
            only_widget=True
        )
        self.assertEqual(result, self.widget_question)
        
        # Admin should find any API question
        result = search_question(
            user=self.admin_user,
            guru_type_object=self.guru_type,
            binge=None,
            slug="api-question-user1",
            include_api=True
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
        
        # Different user's API duplicate should be separate (for non selfhosted)
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
        if settings.ENV != 'selfhosted':
            self.assertEqual(result, newer_api)
        else:
            self.assertEqual(result, other_user_api)
        
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

    def test_bot_questions_accessibility(self):
        """Test that bot questions (SLACK, DISCORD, and GITHUB sources) are accessible by anyone"""
        
        # Anonymous user should find bot questions from all sources
        result = search_question(
            user=None,
            guru_type_object=self.guru_type,
            binge=None,
            slug="bot-question-slack"
        )
        self.assertEqual(result, self.bot_question_slack)

        result = search_question(
            user=None,
            guru_type_object=self.guru_type,
            binge=None,
            slug="bot-question-discord"
        )
        self.assertEqual(result, self.bot_question_discord)

        result = search_question(
            user=None,
            guru_type_object=self.guru_type,
            binge=None,
            slug="bot-question-github"
        )
        self.assertEqual(result, self.bot_question_github)

        # Owner user should find their bot question
        result = search_question(
            user=self.user1,
            guru_type_object=self.guru_type,
            binge=None,
            slug="bot-question-slack"
        )
        self.assertEqual(result, self.bot_question_slack)

        # Non-owner user should find other's bot question
        result = search_question(
            user=self.user2,
            guru_type_object=self.guru_type,
            binge=None,
            slug="bot-question-slack"  # user2 accessing user1's slack bot question
        )
        self.assertEqual(result, self.bot_question_slack)

        # Admin should find bot questions
        result = search_question(
            user=self.admin_user,
            guru_type_object=self.guru_type,
            binge=None,
            slug="bot-question-discord"
        )
        self.assertEqual(result, self.bot_question_discord)

        # Test with include_api=False (should still find bot questions)
        result = search_question(
            user=self.user1,
            guru_type_object=self.guru_type,
            binge=None,
            slug="bot-question-discord",
            include_api=False
        )
        self.assertEqual(result, self.bot_question_discord)

        # Test with only_widget=True (should not find bot questions)
        result = search_question(
            user=None,
            guru_type_object=self.guru_type,
            binge=None,
            slug="bot-question-slack",
            only_widget=True
        )
        self.assertIsNone(result)

        # Test that SLACK, DISCORD, and GITHUB sources are treated the same way
        for question in [self.bot_question_slack, self.bot_question_discord, self.bot_question_github]:
            # Should be accessible by any user
            result = search_question(
                user=self.user2,  # different user
                guru_type_object=self.guru_type,
                binge=None,
                slug=question.slug
            )
            self.assertEqual(result, question)

            # Should be accessible without API flag
            result = search_question(
                user=self.user1,
                guru_type_object=self.guru_type,
                binge=None,
                slug=question.slug,
                include_api=False
            )
            self.assertEqual(result, question)

    def test_maintainer_access(self):
        """Test that maintainers can access all questions when allow_maintainer_access is True"""
        # Add user1 as a maintainer
        self.guru_type.maintainers.add(self.user1)

        # Maintainer should find regular question
        result = search_question(
            user=self.user1,
            guru_type_object=self.guru_type,
            binge=None,
            slug="regular-question",
            allow_maintainer_access=True
        )
        self.assertEqual(result, self.regular_question)

        # Maintainer should find widget question
        result = search_question(
            user=self.user1,
            guru_type_object=self.guru_type,
            binge=None,
            slug="widget-question",
            allow_maintainer_access=True,
            only_widget=True
        )
        self.assertEqual(result, self.widget_question)

        # Maintainer should find any API question
        result = search_question(
            user=self.user1,
            guru_type_object=self.guru_type,
            binge=None,
            slug="api-question-user1",
            allow_maintainer_access=True,
            include_api=True
        )
        self.assertEqual(result, self.api_question_user1)

        # Maintainer should find Slack question
        result = search_question(
            user=self.user1,
            guru_type_object=self.guru_type,
            binge=None,
            slug="slack-question",
            allow_maintainer_access=True
        )
        self.assertEqual(result, self.slack_question)

        # Maintainer should find Discord question
        result = search_question(
            user=self.user1,
            guru_type_object=self.guru_type,
            binge=None,
            slug="discord-question",
            allow_maintainer_access=True
        )
        self.assertEqual(result, self.discord_question)

        # Maintainer should find Github question
        result = search_question(
            user=self.user1,
            guru_type_object=self.guru_type,
            binge=None,
            slug="github-question",
            allow_maintainer_access=True
        )
        self.assertEqual(result, self.github_question)

        # Maintainer should find bot question via Slack
        result = search_question(
            user=self.user1,
            guru_type_object=self.guru_type,
            binge=None,
            slug="bot-question-slack",
            allow_maintainer_access=True
        )
        self.assertEqual(result, self.bot_question_slack)

        # Maintainer should find bot question via Discord
        result = search_question(
            user=self.user1,
            guru_type_object=self.guru_type,
            binge=None,
            slug="bot-question-discord",
            allow_maintainer_access=True
        )
        self.assertEqual(result, self.bot_question_discord)

        # Maintainer should find bot question via Github
        result = search_question(
            user=self.user1,
            guru_type_object=self.guru_type,
            binge=None,
            slug="bot-question-github",
            allow_maintainer_access=True
        )
        self.assertEqual(result, self.bot_question_github)

        # Maintainer should find binge question
        from core.models import Binge
        binge = Binge.objects.create(
            guru_type=self.guru_type,
            owner=self.user1
        )
        binge_question = Question.objects.create(
            question="Binge question",
            slug="binge-question",
            guru_type=self.guru_type,
            source=Question.Source.USER.value,
            binge=binge
        )
        result = search_question(
            user=self.user1,
            guru_type_object=self.guru_type,
            binge=binge,
            slug="binge-question",
            allow_maintainer_access=True
        )
        self.assertEqual(result, binge_question) 