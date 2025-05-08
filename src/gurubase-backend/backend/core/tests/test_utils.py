from django.conf import settings
from django.test import TestCase, override_settings
from core.models import Binge, Favicon, Question, GuruType
from accounts.models import User
from django.db.models import Q
from core.utils import APIAskResponse, APIType, adjust_color, ask_question_with_stream, create_custom_guru_type_slug, decode_guru_slug, decode_jwt, encode_guru_slug, format_references, generate_jwt, get_contexts, get_links, get_llm_usage, get_question_history, get_question_summary, get_summary, get_tokens_from_openai_response, get_website_icon, has_sufficient_contrast, lighten_color, prepare_contexts, prepare_contexts_for_context_relevance, rgb_to_hex, search_question, split_text, stream_and_save, stream_question_answer, string_to_boolean, validate_image, validate_slug
from core.utils import get_default_settings
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock

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

class ValidateSlugTests(TestCase):
    """Tests for the validate_slug utility function."""
    
    def test_basic_slug_conversion(self):
        """Test basic slug conversion with a simple string."""
        result = validate_slug("Hello World")
        self.assertEqual(result, "hello-world")
    
    def test_slug_with_special_characters(self):
        """Test slug conversion with special characters."""
        result = validate_slug("Hello, World! How are you?")
        self.assertEqual(result, "hello-world-how-are-you")
    
    def test_slug_with_multiple_spaces(self):
        """Test slug conversion with multiple spaces."""
        result = validate_slug("Hello   World")
        self.assertEqual(result, "hello-world")
    
    def test_slug_with_leading_trailing_hyphens(self):
        """Test that leading and trailing hyphens are removed."""
        result = validate_slug("-Hello World-")
        self.assertEqual(result, "hello-world")
    
    def test_slug_with_multiple_hyphens(self):
        """Test that multiple hyphens are collapsed into a single hyphen."""
        result = validate_slug("Hello---World")
        self.assertEqual(result, "hello-world")
    
    def test_slug_with_uppercase_characters(self):
        """Test that uppercase characters are converted to lowercase."""
        result = validate_slug("HELLO WORLD")
        self.assertEqual(result, "hello-world")
    
    def test_slug_with_numbers(self):
        """Test slug conversion with numbers."""
        result = validate_slug("Hello World 123")
        self.assertEqual(result, "hello-world-123")
    
    def test_slug_with_non_alphanumeric(self):
        """Test slug conversion with various non-alphanumeric characters."""
        result = validate_slug("Hello@World#123$%^&*()")
        self.assertEqual(result, "hello-world-123")


class CreateCustomGuruTypeSlugTests(TestCase):
    """Tests for the create_custom_guru_type_slug utility function."""
    
    def test_basic_guru_type_slug(self):
        """Test basic guru type slug creation."""
        result = create_custom_guru_type_slug("Test Guru")
        self.assertEqual(result, "test-guru")
    
    def test_guru_type_slug_with_special_chars(self):
        """Test guru type slug with special characters."""
        result = create_custom_guru_type_slug("C++")
        self.assertEqual(result, "cplusplus")
        
        result = create_custom_guru_type_slug("C#")
        self.assertEqual(result, "csharp")
        
        result = create_custom_guru_type_slug("A&B")
        self.assertEqual(result, "aandb")
        
        result = create_custom_guru_type_slug("Test@Email")
        self.assertEqual(result, "testatemail")
        
        result = create_custom_guru_type_slug("A|B")
        self.assertEqual(result, "aorb")
        
        result = create_custom_guru_type_slug("50%")
        self.assertEqual(result, "50percent")
        
        result = create_custom_guru_type_slug("Star*")
        self.assertEqual(result, "starstar")
    
    def test_guru_type_slug_with_multiple_replacements(self):
        """Test guru type slug with multiple special character replacements."""
        result = create_custom_guru_type_slug("C++ & Python @ 2023")
        self.assertEqual(result, "cplusplus-and-python-at-2023")


class FormatReferencesTests(TestCase):
    """Tests for the format_references utility function."""
    
    def test_format_references_html_unescaping(self):
        """Test that HTML entities in references are unescaped."""
        references = [
            {"question": "What is &quot;Python&quot;?", "link": "https://example.com/python"},
            {"question": "React &amp; JavaScript", "link": "https://example.com/react"},
            {"question": "HTML &lt;div&gt; element", "link": "https://example.com/html"}
        ]
        
        result = format_references(references)
        
        self.assertEqual(result[0]["question"], 'What is "Python"?')
        self.assertEqual(result[1]["question"], "React & JavaScript")
        self.assertEqual(result[2]["question"], "HTML <div> element")
        
        # Check that links are preserved
        self.assertEqual(result[0]["link"], "https://example.com/python")
        self.assertEqual(result[1]["link"], "https://example.com/react")
        self.assertEqual(result[2]["link"], "https://example.com/html")
    
    def test_format_references_empty_list(self):
        """Test format_references with an empty list."""
        result = format_references([])
        self.assertEqual(result, [])


class RgbToHexTests(TestCase):
    """Tests for the rgb_to_hex utility function."""
    
    def test_rgb_to_hex_conversion(self):
        """Test basic RGB to HEX conversion."""
        # Black
        self.assertEqual(rgb_to_hex((0, 0, 0)), "#000000")
        
        # White
        self.assertEqual(rgb_to_hex((255, 255, 255)), "#ffffff")
        
        # Red
        self.assertEqual(rgb_to_hex((255, 0, 0)), "#ff0000")
        
        # Green
        self.assertEqual(rgb_to_hex((0, 255, 0)), "#00ff00")
        
        # Blue
        self.assertEqual(rgb_to_hex((0, 0, 255)), "#0000ff")
        
        # Custom color
        self.assertEqual(rgb_to_hex((123, 45, 67)), "#7b2d43")


class LightenColorTests(TestCase):
    """Tests for the lighten_color utility function."""
    
    def test_lighten_color_basic(self):
        """Test basic color lightening."""
        # Black should become very light gray
        self.assertEqual(lighten_color("#000000"), "#e5e5e5")
        
        # A dark color should become lighter
        self.assertEqual(lighten_color("#7b2d43"), "#f1eaec")
        
        # White should stay almost white
        self.assertEqual(lighten_color("#ffffff"), "#ffffff")
    
    def test_lighten_color_preserves_format(self):
        """Test that the function preserves the 6-digit hex format."""
        result = lighten_color("#123456")
        
        # Check that it's a valid 6-digit hex color
        self.assertTrue(result.startswith("#"))
        self.assertEqual(len(result), 7)  # Including the # sign
        self.assertTrue(all(c in "0123456789abcdef" for c in result[1:]))


class StringToBooleanTests(TestCase):
    """Tests for the string_to_boolean utility function."""
    
    def test_string_to_boolean_true_values(self):
        """Test string_to_boolean with true values."""
        self.assertTrue(string_to_boolean("true"))
        self.assertTrue(string_to_boolean("True"))
        self.assertTrue(string_to_boolean("TRUE"))
        
    def test_string_to_boolean_false_values(self):
        """Test string_to_boolean with false values."""
        self.assertFalse(string_to_boolean("false"))
        self.assertFalse(string_to_boolean("False"))
        self.assertFalse(string_to_boolean("FALSE"))
        self.assertFalse(string_to_boolean("no"))
        self.assertFalse(string_to_boolean("No"))
        self.assertFalse(string_to_boolean("NO"))
        self.assertFalse(string_to_boolean("0"))
        self.assertFalse(string_to_boolean("f"))
        self.assertFalse(string_to_boolean("n"))
        
    def test_string_to_boolean_invalid_values(self):
        """Test string_to_boolean with invalid values."""
        # Invalid values should return False
        self.assertFalse(string_to_boolean(""))
        self.assertFalse(string_to_boolean("maybe"))
        self.assertFalse(string_to_boolean("123"))
        self.assertFalse(string_to_boolean("None"))


class GuruSlugEncodingDecodingTests(TestCase):
    """Tests for the encode_guru_slug and decode_guru_slug utility functions."""
    
    def test_encode_decode_guru_slug(self):
        """Test encoding and decoding of guru slugs."""
        # Test regular slug
        original_slug = "test-guru"
        encoded = encode_guru_slug(original_slug)
        decoded = decode_guru_slug(encoded)
        self.assertEqual(decoded, original_slug)
        
        # Test slug with special characters
        original_slug = "test/guru+with&special-chars"
        encoded = encode_guru_slug(original_slug)
        decoded = decode_guru_slug(encoded)
        self.assertEqual(decoded, original_slug)
        
    def test_encode_guru_slug(self):
        """Test that encode_guru_slug properly encodes slugs."""
        # The encoding should be URL-safe base64
        encoded = encode_guru_slug("test-guru")
        self.assertTrue(all(c in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_=:" for c in encoded))
        
    def test_decode_guru_slug_invalid(self):
        """Test that decode_guru_slug handles invalid encoded strings."""
        result = decode_guru_slug("not-a-valid-encoded-string:")
        self.assertEqual(result, None)


class GetTokensFromOpenAIResponseTests(TestCase):
    """Tests for the get_tokens_from_openai_response utility function."""
    
    def test_get_tokens_with_usage(self):
        """Test getting tokens from a response with usage information."""
        # Create mock with the correct nested structure
        mock_response = MagicMock()
        mock_response.usage.prompt_tokens = 100
        mock_response.usage.completion_tokens = 50
        mock_response.usage.prompt_tokens_details = None  # No cached tokens
        
        prompt_tokens, completion_tokens, cached_prompt_tokens = get_tokens_from_openai_response(mock_response)
        
        self.assertEqual(prompt_tokens, 100)
        self.assertEqual(completion_tokens, 50)
        self.assertEqual(cached_prompt_tokens, 0)  # Should be 0 when prompt_tokens_details is None
    
    def test_get_tokens_without_usage(self):
        """Test getting tokens from a response without usage information."""
        mock_response = MagicMock()
        mock_response.usage = None
        
        prompt_tokens, completion_tokens, cached_prompt_tokens = get_tokens_from_openai_response(mock_response)
        
        self.assertEqual(prompt_tokens, 0)
        self.assertEqual(completion_tokens, 0)
        self.assertEqual(cached_prompt_tokens, 0)
    
    def test_get_tokens_with_cached(self):
        """Test getting tokens from a response with cached tokens information."""
        mock_response = MagicMock()
        mock_response.usage.prompt_tokens = 100
        mock_response.usage.completion_tokens = 50
        # Create the nested prompt_tokens_details with cached_tokens
        mock_response.usage.prompt_tokens_details = MagicMock()
        mock_response.usage.prompt_tokens_details.cached_tokens = 30
        
        prompt_tokens, completion_tokens, cached_prompt_tokens = get_tokens_from_openai_response(mock_response)
        
        self.assertEqual(prompt_tokens, 100)
        self.assertEqual(completion_tokens, 50)
        self.assertEqual(cached_prompt_tokens, 30)


class GetLLMUsageTests(TestCase):
    """Tests for the get_llm_usage utility function."""

    def setUp(self):
        def_settings = get_default_settings()
        def_settings.pricings = {
            "gpt-4": {
                "prompt": 0.00003,  # per 1 tokens
                "completion": 0.00006  # per 1 tokens
            }
        }
        self.mock_settings = def_settings
    
    @patch("core.utils.get_default_settings")
    def test_get_llm_usage_without_cached(self, mock_settings):
        """Test getting LLM usage cost calculation without cached tokens."""
        # Configure settings
        mock_settings.return_value = self.mock_settings
        
        # Calculate cost for 1000 prompt tokens and 500 completion tokens using gpt-4
        cost = get_llm_usage("gpt-4", 1000, 500)
        
        # Expected cost: (1000 * 0.03/1000) + (500 * 0.06/1000) = 0.03 + 0.03 = 0.06
        self.assertAlmostEqual(cost, 0.06)
    
    @patch("core.utils.get_default_settings")
    def test_get_llm_usage_with_cached(self, mock_settings):
        """Test getting LLM usage cost calculation with cached tokens."""
        mock_settings.return_value = self.mock_settings
        
        # Calculate cost for 1000 prompt tokens (with 300 cached) and 500 completion tokens using gpt-4
        cost = get_llm_usage("gpt-4", 1000, 500, 300)
        
        # Expected cost: ((1000-300) * 0.03/1000) + (500 * 0.06/1000) = 0.021 + 0.03 = 0.051
        self.assertAlmostEqual(cost, 0.051)
    
    @patch("core.utils.get_default_settings")
    def test_get_llm_usage_unknown_model(self, mock_settings):
        """Test getting LLM usage cost for an unknown model."""
        # Configure settings with known models
        mock_settings.return_value = self.mock_settings
        
        # Calculate cost for an unknown model
        cost = get_llm_usage("unknown-model", 1000, 500)
        
        # Should return 0 for unknown models
        self.assertEqual(cost, 0)
    
    @patch("core.utils.get_default_settings")
    def test_get_llm_usage_zero_tokens(self, mock_settings):
        """Test getting LLM usage cost with zero tokens."""
        # Configure settings
        mock_settings.return_value = self.mock_settings
        
        # Calculate cost with zero tokens
        cost = get_llm_usage("gpt-4", 0, 0)
        
        # Expected cost: 0
        self.assertEqual(cost, 0)


class JWTTests(TestCase):
    """Tests for JWT utility functions."""
    
    @patch('core.utils.settings.SECRET_KEY', 'test-secret-key')
    @patch('core.utils.settings.JWT_EXPIRATION_SECONDS', 60)
    def test_generate_jwt(self):
        """Test generating a JWT token."""
        token = generate_jwt()
        
        # Token should be a string
        self.assertIsInstance(token, str)
        
        # Token should have three parts separated by dots
        parts = token.split('.')
        self.assertEqual(len(parts), 3)
    
    @patch('core.utils.settings.SECRET_KEY', 'test-secret-key')
    @patch('core.utils.jwt.decode')
    def test_decode_jwt_valid(self, mock_decode):
        """Test decoding a valid JWT token."""
        mock_decode.return_value = {"sub": "test"}
        
        result = decode_jwt("valid.jwt.token")
        
        self.assertTrue(result)
        mock_decode.assert_called_once()
    
    @patch('core.utils.settings.SECRET_KEY', 'test-secret-key')
    @patch('core.utils.jwt.decode')
    def test_decode_jwt_invalid(self, mock_decode):
        """Test decoding an invalid JWT token."""
        mock_decode.side_effect = Exception("Invalid token")
        
        result = decode_jwt("invalid.jwt.token")
        
        self.assertFalse(result)
        mock_decode.assert_called_once()


class GetWebsiteIconTests(TestCase):
    """Tests for the get_website_icon utility function."""
    
    def setUp(self):
        """Set up test data for favicon tests."""
        self.domain = "example.com"
        self.favicon_url = "https://example.com/favicon.ico"
    
    @patch('core.utils.requests.head')
    def test_get_website_icon_existing_in_db(self, mock_head):
        """Test getting a website icon that already exists in the database."""
        # Create a favicon in the database
        Favicon.objects.create(domain=self.domain, favicon_url=self.favicon_url, valid=True)
        
        result = get_website_icon(self.domain)
        
        # Should return the favicon URL without making any requests
        self.assertEqual(result, self.favicon_url)
        mock_head.assert_not_called()
    
    @patch('core.utils.requests.head')
    def test_get_website_icon_root_favicon(self, mock_head):
        """Test getting a website icon from the root favicon.ico."""
        # Mock a successful HEAD request
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_head.return_value = mock_response
        
        result = get_website_icon(self.domain)
        
        # Should return the favicon URL and create a database entry
        self.assertEqual(result, self.favicon_url)
        mock_head.assert_called_once_with(self.favicon_url, timeout=5)
        
        # Check that a favicon entry was created
        favicon = Favicon.objects.get(domain=self.domain)
        self.assertEqual(favicon.favicon_url, self.favicon_url)
        self.assertTrue(favicon.valid)
    
    @patch('core.utils.requests.head')
    @patch('core.utils.requests.get')
    @patch('core.utils.BeautifulSoup')
    def test_get_website_icon_from_html(self, mock_bs, mock_get, mock_head):
        """Test getting a website icon from HTML link tags."""
        # Mock a failed HEAD request for favicon.ico
        mock_head_response = MagicMock()
        mock_head_response.status_code = 404
        mock_head.return_value = mock_head_response
        
        # Mock a successful GET request for the main page
        mock_get_response = MagicMock()
        mock_get_response.text = "<html><head><link rel='icon' href='/custom-icon.png'></head></html>"
        mock_get.return_value = mock_get_response
        
        # Mock BeautifulSoup to return a link tag
        mock_soup = MagicMock()
        mock_link = MagicMock()
        mock_link.__getitem__.return_value = "/custom-icon.png"
        mock_soup.find.return_value = mock_link
        mock_bs.return_value = mock_soup
        
        result = get_website_icon(self.domain)
        
        # Should return the full URL to the custom icon
        expected_url = "https://example.com/custom-icon.png"
        self.assertEqual(result, expected_url)
        
        # Check that a favicon entry was created
        favicon = Favicon.objects.get(domain=self.domain)
        self.assertEqual(favicon.favicon_url, expected_url)
        self.assertTrue(favicon.valid)
    
    @patch('core.utils.requests.head')
    @patch('core.utils.requests.get')
    def test_get_website_icon_exception(self, mock_get, mock_head):
        """Test handling exceptions when fetching a website icon."""
        # Mock an exception during requests
        mock_head.side_effect = Exception("Connection error")
        
        result = get_website_icon(self.domain)
        
        # Should create an invalid favicon entry
        favicon = Favicon.objects.get(domain=self.domain)
        self.assertFalse(favicon.valid)
        self.assertEqual(result, favicon.url)


class ValidateImageTests(TestCase):
    """Tests for the validate_image utility function."""
    
    def test_validate_image_valid_extensions(self):
        """Test validating images with valid extensions."""
        # Create mock files with valid extensions
        for ext in ['jpg', 'png', 'jpeg', 'svg']:
            mock_file = MagicMock()
            mock_file.name = f"test.{ext}"
            
            error, split = validate_image(mock_file)
            
            self.assertIsNone(error)
            self.assertEqual(split, ['test', ext])
    
    def test_validate_image_invalid_extension(self):
        """Test validating images with invalid extensions."""
        mock_file = MagicMock()
        mock_file.name = "test.txt"
        
        error, split = validate_image(mock_file)
        
        self.assertEqual(error, 'Invalid image extension')
        self.assertIsNone(split)
    
    def test_validate_image_no_extension(self):
        """Test validating images with no extension."""
        mock_file = MagicMock()
        mock_file.name = "test"
        
        error, split = validate_image(mock_file)
        
        self.assertEqual(error, 'Invalid image extension')
        self.assertIsNone(split)
    
    def test_validate_image_none(self):
        """Test validating None as an image."""
        error, split = validate_image(None)
        
        self.assertEqual(error, 'No image provided')
        self.assertIsNone(split)


class GetLinksTests(TestCase):
    """Tests for the get_links utility function."""
    
    def test_get_links_basic(self):
        """Test getting links from basic markdown-style links."""
        content = "Check out this [example link](https://example.com) and [another one](https://test.com)"
        result = get_links(content)
        
        self.assertEqual(len(result), 2)
        self.assertIn("[example link](https://example.com)", result)
        self.assertIn("[another one](https://test.com)", result)
    
    def test_get_links_with_no_links(self):
        """Test getting links from content with no links."""
        content = "This is a text with no links."
        result = get_links(content)
        
        self.assertEqual(result, [])
    
    def test_get_links_with_complex_content(self):
        """Test getting links from complex content with code blocks and other formatting."""
        content = """
        # Title
        
        This is a paragraph with a [link](https://example.com).
        
        ```python
        # This is code, not a [fake link](https://fake.com)
        ```
        
        And here's [another link](https://test.com) with some text.
        """
        
        result = get_links(content)
        
        self.assertEqual(len(result), 3)
        self.assertIn("[link](https://example.com)", result)
        self.assertIn("[another link](https://test.com)", result)
        self.assertIn("[fake link](https://fake.com)", result)
    
    def test_get_links_with_special_characters(self):
        """Test getting links with special characters in label or URL."""
        content = """
        [Link with spaces](https://example.com/path with spaces)
        [Link with (parentheses)](https://example.com/path(with)parentheses)
        """
        
        result = get_links(content)
        
        self.assertEqual(len(result), 2)
        self.assertIn("[Link with spaces](https://example.com/path with spaces)", result)
        self.assertIn("[Link with (parentheses)](https://example.com/path(with)parentheses)", result)


class HasSufficientContrastTests(TestCase):
    """Tests for the has_sufficient_contrast utility function."""
    
    def test_has_sufficient_contrast_dark_colors(self):
        """Test that dark colors have sufficient contrast with white."""
        # Dark black (should have sufficient contrast)
        self.assertTrue(has_sufficient_contrast((0, 0, 0)))
        
        # Dark blue (should have sufficient contrast)
        self.assertTrue(has_sufficient_contrast((0, 0, 128)))
        
        # Dark red (should have sufficient contrast)
        self.assertTrue(has_sufficient_contrast((128, 0, 0)))
    
    def test_has_sufficient_contrast_light_colors(self):
        """Test that light colors don't have sufficient contrast with white."""
        # Light yellow (should not have sufficient contrast)
        self.assertFalse(has_sufficient_contrast((255, 255, 200)))
        
        # Light gray (should not have sufficient contrast)
        self.assertFalse(has_sufficient_contrast((200, 200, 200)))
        
        # White (should not have sufficient contrast with white)
        self.assertFalse(has_sufficient_contrast((255, 255, 255)))
    
    def test_has_sufficient_contrast_threshold(self):
        """Test colors near the contrast threshold."""
        # Test colors that are just above/below the threshold
        # Note: The actual threshold in the function is a contrast ratio <= 1/2
        
        # Should have sufficient contrast (just below the threshold)
        self.assertTrue(has_sufficient_contrast((100, 100, 100)))
        
        # Should have sufficient contrast (just above the threshold)
        self.assertTrue(has_sufficient_contrast((180, 180, 180)))


class AdjustColorTests(TestCase):
    """Tests for the adjust_color utility function."""
    
    def test_adjust_color_below_threshold(self):
        """Test adjusting a color below the threshold (0.03928)."""
        # For a color below threshold (0.03928), the formula is color / 12.92
        color = 0.03  # Below threshold
        result = adjust_color(color)
        expected = color / 12.92
        self.assertAlmostEqual(result, expected)
    
    def test_adjust_color_above_threshold(self):
        """Test adjusting a color above the threshold (0.03928)."""
        # For a color above threshold, the formula is ((color + 0.055) / 1.055) ** 2.4
        color = 0.5  # Above threshold
        result = adjust_color(color)
        expected = ((color + 0.055) / 1.055) ** 2.4
        self.assertAlmostEqual(result, expected)
    
    def test_adjust_color_at_threshold(self):
        """Test adjusting a color exactly at the threshold (0.03928)."""
        color = 0.03928  # At threshold
        result = adjust_color(color)
        expected = color / 12.92
        self.assertAlmostEqual(result, expected)


class PrepareContextsForContextRelevanceTests(TestCase):
    """Tests for the prepare_contexts_for_context_relevance utility function."""
    
    def test_prepare_contexts_empty(self):
        """Test preparing an empty context list."""
        contexts = []
        result = prepare_contexts_for_context_relevance(contexts)
        self.assertEqual(result, [])
    
    def test_prepare_contexts_single_context(self):
        """Test preparing a single context."""
        # Create a mock context with the expected structure
        context = {
            'entity': {
                'text': 'Sample context text',
                'metadata': {
                    'title': 'Sample Title',
                    'link': 'https://example.com',
                    'type': 'WEBSITE'
                }
            },
            'prefix': 'Text'
        }
        
        result = prepare_contexts_for_context_relevance([context])
        
        self.assertEqual(len(result), 1)
        self.assertIn('Sample context text', result[0])
        self.assertIn('Sample Title', result[0])
        self.assertIn('https://example.com', result[0])
    
    def test_prepare_contexts_multiple_contexts(self):
        """Test preparing multiple contexts."""
        # Create mock contexts with the expected structure
        contexts = [
            {
                'entity': {
                    'text': 'First context text',
                    'metadata': {
                        'title': 'First Title',
                        'link': 'https://example.com/1',
                        'type': 'WEBSITE'
                    }
                },
                'prefix': 'Text'
            },
            {
                'entity': {
                    'text': 'Second context text',
                    'metadata': {
                        'title': 'Second Title',
                        'link': 'https://example.com/2',
                        'type': 'WEBSITE'
                    }
                },
                'prefix': 'Text'
            }
        ]
        
        result = prepare_contexts_for_context_relevance(contexts)
        
        self.assertEqual(len(result), 2)
        self.assertIn('First context text', result[0])
        self.assertIn('First Title', result[0])
        self.assertIn('https://example.com/1', result[0])
        
        self.assertIn('Second context text', result[1])
        self.assertIn('Second Title', result[1])
        self.assertIn('https://example.com/2', result[1])


class SplitTextTests(TestCase):
    """Tests for the split_text utility function."""
    
    def test_split_text_basic(self):
        """Test basic text splitting."""
        text = "This is a sample text that needs to be split into chunks."
        
        result = split_text(text, max_length=20, min_length=5, overlap=5)
        
        # Should split into smaller chunks
        self.assertTrue(len(result) > 1)
        
        # Each chunk should respect max_length
        for chunk in result:
            self.assertLessEqual(len(chunk), 20)
        
        # Test that content is preserved
        combined = ''.join(result)
        # Due to overlaps, combined might be longer than original
        for item in result:
            self.assertTrue(item in text)
    
    def test_split_text_with_separators(self):
        """Test text splitting with custom separators."""
        text = "Paragraph 1. Paragraph 1. Paragraph 1. Paragraph 1.\n\nParagraph 2. Paragraph 2. Paragraph 2. Paragraph 2.\n\nParagraph 3. Paragraph 3. Paragraph 3. Paragraph 3."
        separators = ["\n\n"]
        
        result = split_text(text, max_length=50, min_length=5, overlap=5, separators=separators)
        
        # Should split at paragraph boundaries
        self.assertEqual(len(result), 3)
        self.assertIn("Paragraph 1.", result[0])
        self.assertIn("Paragraph 2.", result[1])
        self.assertIn("Paragraph 3.", result[2])
    
    def test_split_text_small_text(self):
        """Test splitting text smaller than max_length."""
        text = "Small text"
        
        result = split_text(text, max_length=50, min_length=5, overlap=5)
        
        # Should return a single chunk
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0], text)
    
    def test_split_text_with_long_words(self):
        """Test splitting text with words longer than max_length."""
        text = "This contains a supercalifragilisticexpialidocious word."
        
        result = split_text(text, max_length=10, min_length=5, overlap=2)
        
        # Should still split, possibly breaking words
        self.assertTrue(len(result) > 1)
        
        # Combined result should contain the original text
        combined = ''.join(result)
        for item in result:
            self.assertTrue(item in ''.join(text.split(' ')))


class PrepareContextsTests(TestCase):
    """Tests for the prepare_contexts utility function."""
    
    def test_stackoverflow_contexts(self):
        """Test preparing StackOverflow contexts."""
        # Create a mock StackOverflow context
        context = {
            'question': {
                'entity': {
                    'text': 'How do I use Django?',
                    'metadata': {
                        'question': 'How do I use Django?',
                        'link': 'https://stackoverflow.com/q/12345',
                        'score': 10,
                        'owner_badges': ["Gold"],
                        'owner_reputation': 5000
                    }
                },
                'prefix': 'Text'
            },
            'accepted_answer': {
                'entity': {
                    'text': 'Here is how to use Django...',
                    'metadata': {}
                }
            },
            'other_answers': [
                {
                    'entity': {
                        'text': 'Another way to use Django...',
                        'metadata': {'score': 5}
                    }
                }
            ],
            'prefix': 'Text'
        }
        
        formatted_contexts, references = prepare_contexts([context], [])
        
        # Check the formatted contexts
        self.assertTrue('Context 1:' in formatted_contexts['contexts'])
        self.assertTrue('Question: \'\'\'How do I use Django?\'\'\'' in formatted_contexts['contexts'])
        self.assertTrue('Accepted answer: \'\'\'Here is how to use Django...\'\'\'' in formatted_contexts['contexts'])
        self.assertTrue('Answer 1 with higher score: \'\'\'Another way to use Django...\'\'\'' in formatted_contexts['contexts'])
        
        # Check the references
        self.assertEqual(len(references), 1)
        self.assertEqual(references[0]['question'], 'How do I use Django?')
        self.assertEqual(references[0]['link'], 'https://stackoverflow.com/q/12345')
    
    def test_data_source_contexts(self):
        """Test preparing data source contexts (WEBSITE, PDF, etc.)."""
        # Create a mock data source context
        context = {
            'entity': {
                'text': 'Website content about Python',
                'metadata': {
                    'type': 'WEBSITE',
                    'title': 'Python Tutorial',
                    'link': 'https://example.com/python'
                }
            },
            'prefix': 'Text'
        }
        
        formatted_contexts, references = prepare_contexts([context], [])
        
        # Check the formatted contexts
        self.assertTrue('Context 1:' in formatted_contexts['contexts'])
        self.assertTrue("Metadata: '''{'type': 'WEBSITE', 'title': 'Python Tutorial', 'link': 'https://example.com/python'}'''" in formatted_contexts['contexts'])
        self.assertTrue("Text: '''Website content about Python'''" in formatted_contexts['contexts'])
        
        # Check the references
        self.assertEqual(len(references), 1)
        self.assertEqual(references[0]['question'], 'Python Tutorial')
        self.assertEqual(references[0]['link'], 'https://example.com/python')
    
    def test_github_repo_contexts(self):
        """Test preparing GitHub repository contexts."""
        # Create a mock GitHub repo context
        context = {
            'entity': {
                'text': 'def hello_world(): print("Hello, World!")',
                'metadata': {
                    'type': 'GITHUB_REPO',
                    'title': 'example/hello.py',
                    'link': 'https://github.com/example/repo/blob/main/hello.py'
                }
            },
            'prefix': 'Code'
        }
        
        formatted_contexts, references = prepare_contexts([context], [])
        
        # Check the formatted contexts
        self.assertTrue('Context 1:' in formatted_contexts['contexts'])
        self.assertTrue("Metadata: '''{'type': 'GITHUB_REPO', 'title': 'example/hello.py', 'link': 'https://github.com/example/repo/blob/main/hello.py'}'''" in formatted_contexts['contexts'])
        self.assertTrue('Text: \'\'\'def hello_world(): print("Hello, World!")\'\'\'' in formatted_contexts['contexts'])
        
        # Check the references
        self.assertEqual(len(references), 1)
        self.assertEqual(references[0]['question'], 'example/hello.py')
        self.assertEqual(references[0]['link'], 'https://github.com/example/repo/blob/main/hello.py')
    
    def test_private_pdf_contexts(self):
        """Test preparing private PDF contexts where the link should be masked."""
        # Create a mock private PDF context
        context = {
            'entity': {
                'text': 'Private PDF content',
                'metadata': {
                    'type': 'PDF',
                    'title': 'Private Document',
                    'link': 'https://example.com/private.pdf'
                }
            },
            'prefix': 'Text'
        }
        
        # Set up the mock to return this PDF as private
        with patch('core.models.DataSource.objects.filter') as mock_filter:
            mock_queryset = MagicMock()
            mock_queryset.values_list.return_value = ['https://example.com/private.pdf']
            mock_filter.return_value = mock_queryset
            
            formatted_contexts, references = prepare_contexts([context], [])
            
            # The link should be None in the metadata
            self.assertTrue("'link': None" in formatted_contexts['contexts'])
            
            # The reference should still have the link (it's masked only in the prompt)
            self.assertEqual(references[0]['link'], 'https://example.com/private.pdf')


class GetQuestionHistoryTests(TestCase):
    """Tests for the get_question_history utility function."""
    
    def setUp(self):
        """Set up test data for question history tests."""
        get_default_settings()
        self.guru_type = GuruType.objects.create(
            name="Test Guru",
            slug="test-guru"
        )
        
        # Create a chain of questions for testing history
        self.root_question = Question.objects.create(
            question="Root question",
            slug="root-question",
            guru_type=self.guru_type,
            source=Question.Source.USER.value,
            content="Answer to root question",
            user_question="User's root question"
        )
        
        self.follow_up_1 = Question.objects.create(
            question="Follow-up 1",
            slug="follow-up-1",
            guru_type=self.guru_type,
            source=Question.Source.USER.value,
            content="Answer to follow-up 1",
            user_question="User's follow-up 1",
            parent=self.root_question
        )
        
        self.follow_up_2 = Question.objects.create(
            question="Follow-up 2",
            slug="follow-up-2",
            guru_type=self.guru_type,
            source=Question.Source.USER.value,
            content="Answer to follow-up 2",
            user_question="User's follow-up 2",
            parent=self.follow_up_1
        )
    
    def test_get_question_history_no_parent(self):
        """Test getting question history for a root question with no parent."""
        history = get_question_history(self.root_question)
        
        # Should have one item (the root question)
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]['question'], "Root question")
        self.assertEqual(history[0]['user_question'], "User's root question")
        self.assertEqual(history[0]['answer'], "Answer to root question")
    
    def test_get_question_history_single_parent(self):
        """Test getting question history for a question with a single parent."""
        history = get_question_history(self.follow_up_1)
        
        # Should have two items (the root question and the follow-up 1)
        self.assertEqual(len(history), 2)
        self.assertEqual(history[0]['question'], "Root question")
        self.assertEqual(history[0]['user_question'], "User's root question")
        self.assertEqual(history[0]['answer'], "Answer to root question")

        # Check second item (follow-up 1)
        self.assertEqual(history[1]['question'], "Follow-up 1")
        self.assertEqual(history[1]['user_question'], "User's follow-up 1")
        self.assertEqual(history[1]['answer'], "Answer to follow-up 1")
    
    def test_get_question_history_multiple_levels(self):
        """Test getting question history for a question with multiple parent levels."""
        history = get_question_history(self.follow_up_2)
        
        # Should have three items (root, follow-up 1, and follow-up 2)
        self.assertEqual(len(history), 3)
        
        # Check first item (root question)
        self.assertEqual(history[0]['question'], "Root question")
        self.assertEqual(history[0]['user_question'], "User's root question")
        self.assertEqual(history[0]['answer'], "Answer to root question")
        
        # Check second item (follow-up 1)
        self.assertEqual(history[1]['question'], "Follow-up 1")
        self.assertEqual(history[1]['user_question'], "User's follow-up 1")
        self.assertEqual(history[1]['answer'], "Answer to follow-up 1")

        # Check third item (follow-up 2)
        self.assertEqual(history[2]['question'], "Follow-up 2")
        self.assertEqual(history[2]['user_question'], "User's follow-up 2")
        self.assertEqual(history[2]['answer'], "Answer to follow-up 2")
    
    def test_get_question_history_with_none(self):
        """Test getting question history with None as input."""
        history = get_question_history(None)
        
        # Should return an empty list
        self.assertEqual(history, [])

class APIAskResponseTests(TestCase):
    """Tests for the APIAskResponse class methods."""
    
    def setUp(self):
        """Set up test data for APIAskResponse tests."""
        get_default_settings()
        self.guru_type = GuruType.objects.create(
            name="Test Guru",
            slug="test-guru"
        )
        
        self.question_obj = Question.objects.create(
            question="Test question",
            slug="test-question",
            guru_type=self.guru_type,
            source=Question.Source.USER.value,
            content="Answer to test question"
        )
    
    def test_from_existing(self):
        """Test creating an APIAskResponse from an existing question."""
        response = APIAskResponse.from_existing(self.question_obj)
        
        self.assertEqual(response.content, "Answer to test question")
        self.assertIsNone(response.error)
        self.assertEqual(response.question_obj, self.question_obj)
        self.assertTrue(response.is_existing)
        self.assertEqual(response.question, "Test question")
    
    def test_from_stream(self):
        """Test creating an APIAskResponse from a stream generator."""
        # Mock a generator
        def mock_generator():
            yield "Part 1"
            yield "Part 2"
            yield "Part 3"
        
        response = APIAskResponse.from_stream(mock_generator(), "Stream question")
        
        self.assertEqual(response.content.__name__, "mock_generator")  # It's the generator function
        self.assertIsNone(response.error)
        self.assertIsNone(response.question_obj)
        self.assertFalse(response.is_existing)
        self.assertEqual(response.question, "Stream question")
    
    def test_from_error(self):
        """Test creating an APIAskResponse from an error."""
        response = APIAskResponse.from_error("Test error message")
        
        self.assertIsNone(response.content)
        self.assertEqual(response.error, "Test error message")
        self.assertIsNone(response.question_obj)
        self.assertFalse(response.is_existing)
        self.assertIsNone(response.question)

class APITypeTests(TestCase):
    """Tests for the APIType class methods."""
    
    def test_is_api_type(self):
        """Test the is_api_type classmethod."""
        # Valid API types
        self.assertTrue(APIType.is_api_type(APIType.API))
        self.assertTrue(APIType.is_api_type(APIType.WIDGET))
        self.assertTrue(APIType.is_api_type(APIType.DISCORD))
        self.assertTrue(APIType.is_api_type(APIType.SLACK))
        self.assertTrue(APIType.is_api_type(APIType.GITHUB))
        
        # Invalid API types
        self.assertFalse(APIType.is_api_type("INVALID"))
        self.assertFalse(APIType.is_api_type(""))
        self.assertFalse(APIType.is_api_type(None))
    
    def test_get_question_source(self):
        """Test the get_question_source classmethod."""
        # Check mapping to Question.Source values
        self.assertEqual(APIType.get_question_source(APIType.API), Question.Source.API.value)
        self.assertEqual(APIType.get_question_source(APIType.WIDGET), Question.Source.WIDGET_QUESTION.value)
        self.assertEqual(APIType.get_question_source(APIType.DISCORD), Question.Source.DISCORD.value)
        self.assertEqual(APIType.get_question_source(APIType.SLACK), Question.Source.SLACK.value)
        self.assertEqual(APIType.get_question_source(APIType.GITHUB), Question.Source.GITHUB.value)
        
        # Invalid API type should raise ValueError
        with self.assertRaises(KeyError):
            APIType.get_question_source("INVALID") 

class StreamQuestionAnswerTests(TestCase):
    """Tests for stream_question_answer and ask_question_with_stream utility functions."""
    
    def setUp(self):
        """Set up test data for all tests."""
        # Create a test guru type
        self.guru_type = GuruType.objects.create(
            name="Test Guru",
            slug="test-guru",
            domain_knowledge="Test domain knowledge",
            milvus_collection_name="test_guru_collection"
        )
        
        # Create a test user
        self.user = User.objects.create_user(
            name="testuser",
            email="test@example.com",
            password="testpassword"
        )
        
        # Create mock Milvus client
        self.milvus_client_mock = MagicMock()
        
        # Mock question and parameters
        self.question = "What is the meaning of life?"
        self.user_question = "Tell me about life's meaning"
        self.enhanced_question = "Explain the philosophical meaning of life"
        self.source = Question.Source.USER.value
        
    @patch('core.utils.get_milvus_client')
    @patch('core.utils.ask_question_with_stream')
    def test_stream_question_answer_success(self, mock_ask_question_with_stream, mock_get_milvus_client):
        """Test successful streaming of question answer."""
        # Configure mocks
        mock_get_milvus_client.return_value = self.milvus_client_mock
        mock_response = MagicMock()
        mock_prompt = "Test prompt"
        mock_links = {"example.com": "Example Link"}
        mock_context_vals = ["Test context"]
        mock_context_distances = [{"context_id": "1", "distance": 0.1}]
        mock_reranked_scores = [{"index": 0, "score": 0.9}]
        mock_trust_score = 0.85
        mock_processed_ctx_relevances = {"context1": 0.9}
        mock_ctx_rel_usage = {"prompt_tokens": 100}
        mock_times = {"total": 1.0}
        
        mock_ask_question_with_stream.return_value = (
            mock_response, mock_prompt, mock_links, mock_context_vals, 
            mock_context_distances, mock_reranked_scores, mock_trust_score, 
            mock_processed_ctx_relevances, mock_ctx_rel_usage, mock_times
        )
        
        # Call the function under test
        result = stream_question_answer(
            self.question, self.guru_type, "answer", "medium",
            self.user_question, self.source, self.enhanced_question,
            user=self.user
        )
        
        # Verify expected results
        response, prompt, links, context_vals, context_distances, reranked_scores, trust_score, processed_ctx_relevances, ctx_rel_usage, times = result
        
        self.assertEqual(response, mock_response)
        self.assertEqual(prompt, mock_prompt)
        self.assertEqual(links, mock_links)
        self.assertEqual(context_vals, mock_context_vals)
        self.assertEqual(context_distances, mock_context_distances)
        self.assertEqual(reranked_scores, mock_reranked_scores)
        self.assertEqual(trust_score, mock_trust_score)
        self.assertEqual(processed_ctx_relevances, mock_processed_ctx_relevances)
        self.assertEqual(ctx_rel_usage, mock_ctx_rel_usage)
        self.assertEqual(times, mock_times)
        
        # Verify correct parameters were passed
        mock_ask_question_with_stream.assert_called_once_with(
            self.milvus_client_mock, "test_guru_collection", self.question, self.guru_type,
            "answer", "medium", self.user_question, None, self.source, 
            self.enhanced_question, self.user, None
        )
    
    @patch('core.utils.get_milvus_client')
    @patch('core.utils.ask_question_with_stream')
    def test_stream_question_answer_no_response(self, mock_ask_question_with_stream, mock_get_milvus_client):
        """Test streaming with no response returned."""
        # Configure mocks
        mock_get_milvus_client.return_value = self.milvus_client_mock
        mock_times = {"total": 0.5}
        
        # Return None for response and other values
        mock_ask_question_with_stream.return_value = (
            None, None, None, None, None, None, None, None, None, mock_times
        )
        
        # Call the function under test
        result = stream_question_answer(
            self.question, self.guru_type, "answer", "medium",
            self.user_question, self.source, self.enhanced_question
        )
        
        # Verify expected results - should just return the times
        self.assertEqual(result, (None, None, None, None, None, None, None, None, None, mock_times))
    
    @patch('core.utils.get_milvus_client')
    @patch('core.utils.get_contexts')
    @patch('core.utils.get_github_details_if_applicable')
    @patch('core.utils.get_question_history')
    @patch('core.utils.prepare_chat_messages')
    @patch('core.utils.get_openai_requester')
    @patch('core.utils.OutOfContextQuestion')
    def test_ask_question_with_stream_success(self, mock_out_of_context, mock_get_openai_requester, 
                                              mock_prepare_chat_messages, mock_get_question_history,
                                              mock_get_github_details, mock_get_contexts, mock_get_milvus_client):
        """Test successful ask_question_with_stream flow."""
        # Configure mocks
        mock_get_milvus_client.return_value = self.milvus_client_mock
        
        mock_context_vals = ["Test context"]
        mock_links = {"example.com": "Example Link"}
        mock_context_distances = [{"context_id": "1", "distance": 0.1}]
        mock_reranked_scores = [{"index": 0, "score": 0.9}]
        mock_trust_score = 0.85
        mock_processed_ctx_relevances = {"context1": 0.9}
        mock_ctx_rel_usage = {"prompt_tokens": 100}
        mock_get_contexts_times = {"total": 0.5}
        
        mock_get_contexts.return_value = (
            mock_context_vals, mock_links, mock_context_distances, mock_reranked_scores,
            mock_trust_score, mock_processed_ctx_relevances, mock_ctx_rel_usage, mock_get_contexts_times
        )
        
        mock_get_github_details.return_value = "GitHub details"
        mock_get_question_history.return_value = []
        
        mock_messages = [{"role": "system", "content": "You are a helpful assistant"}]
        mock_prepare_chat_messages.return_value = mock_messages
        
        mock_openai_requester = MagicMock()
        mock_response = MagicMock()
        mock_openai_requester.ask_question_with_stream.return_value = mock_response
        mock_get_openai_requester.return_value = mock_openai_requester
        
        # Call the function under test
        result = ask_question_with_stream(
            self.milvus_client_mock, "test_collection", self.question, self.guru_type,
            "answer", "medium", self.user_question, None, self.source, 
            self.enhanced_question, self.user
        )
        
        # Unpack the result
        response, prompt, links, context_vals, context_distances, reranked_scores, trust_score, processed_ctx_relevances, ctx_rel_usage, times = result
        
        # Verify expected results
        self.assertEqual(response, mock_response)
        self.assertEqual(prompt, mock_messages[0]['content'])
        self.assertEqual(links, mock_links)
        self.assertEqual(context_vals, mock_context_vals)
        self.assertEqual(context_distances, mock_context_distances)
        self.assertEqual(reranked_scores, mock_reranked_scores)
        self.assertEqual(trust_score, mock_trust_score)
        self.assertEqual(processed_ctx_relevances, mock_processed_ctx_relevances)
        self.assertEqual(ctx_rel_usage, mock_ctx_rel_usage)
        self.assertTrue('total' in times)
        
        # Verify OutOfContextQuestion was not created
        mock_out_of_context.objects.create.assert_not_called()
    
    @patch('core.utils.get_milvus_client')
    @patch('core.utils.get_contexts')
    @patch('core.utils.get_default_settings')
    @patch('core.utils.OutOfContextQuestion')
    def test_ask_question_with_stream_no_contexts(self, mock_out_of_context, mock_get_default_settings,
                                                mock_get_contexts, mock_get_milvus_client):
        """Test ask_question_with_stream when no contexts are found."""
        # Configure mocks
        mock_get_milvus_client.return_value = self.milvus_client_mock
        
        mock_context_vals = []
        mock_links = {}
        mock_context_distances = []
        mock_reranked_scores = []  # Empty reranked_scores triggers the early return
        mock_trust_score = 0.0
        mock_processed_ctx_relevances = {}
        mock_ctx_rel_usage = {}
        mock_get_contexts_times = {"total": 0.1}
        
        mock_get_contexts.return_value = (
            mock_context_vals, mock_links, mock_context_distances, mock_reranked_scores,
            mock_trust_score, mock_processed_ctx_relevances, mock_ctx_rel_usage, mock_get_contexts_times
        )
        
        # Mock default settings
        mock_settings = MagicMock()
        mock_settings.rerank_threshold = 0.01
        mock_settings.trust_score_threshold = 0.0
        mock_get_default_settings.return_value = mock_settings
        
        # Call the function under test
        result = ask_question_with_stream(
            self.milvus_client_mock, "test_collection", self.question, self.guru_type,
            "answer", "medium", self.user_question, None, self.source, 
            self.enhanced_question
        )
        
        # Verify OutOfContextQuestion was created
        mock_out_of_context.objects.create.assert_called_once()
        
        # Verify function returns expected values when no contexts found
        response, prompt, links, context_vals, context_distances, reranked_scores, trust_score, processed_ctx_relevances, ctx_rel_usage, times = result
        
        self.assertIsNone(response)
        self.assertIsNone(prompt)
        self.assertIsNone(links)
        self.assertIsNone(context_vals)
        self.assertIsNone(context_distances)
        self.assertIsNone(reranked_scores)
        self.assertIsNone(trust_score)
        self.assertIsNone(processed_ctx_relevances)
        self.assertIsNone(ctx_rel_usage)
        self.assertIsNotNone(times)


class GetContextsTests(TestCase):
    """Tests for get_contexts and vector_db_fetch utility functions."""
    
    def setUp(self):
        """Set up test data for all tests."""
        # Create a test guru type
        self.guru_type = GuruType.objects.create(
            name="Test Guru",
            slug="test-guru",
            domain_knowledge="Test domain knowledge",
            milvus_collection_name="test_guru_collection"
        )
        
        # Create mock Milvus client
        self.milvus_client_mock = MagicMock()
        
        # Mock question parameters
        self.question = "What is the meaning of life?"
        self.user_question = "Tell me about life's meaning"
        self.enhanced_question = "Explain the philosophical meaning of life"
    
    @patch('core.utils.vector_db_fetch')
    @patch('core.utils.prepare_contexts')
    def test_get_contexts_success(self, mock_prepare_contexts, mock_vector_db_fetch):
        """Test successful retrieval of contexts."""
        # Configure mocks
        mock_contexts = [{"id": "1", "text": "Context 1", "distance": 0.1}]
        mock_reranked_scores = [{"index": 0, "score": 0.9}]
        mock_trust_score = 0.85
        mock_processed_ctx_relevances = {"context1": 0.9}
        mock_ctx_rel_usage = {"prompt_tokens": 100}
        mock_vector_db_times = {"total": 0.5}
        
        mock_vector_db_fetch.return_value = (
            mock_contexts, mock_reranked_scores, mock_trust_score, 
            mock_processed_ctx_relevances, mock_ctx_rel_usage, mock_vector_db_times
        )
        
        mock_context_vals = ["Formatted context"]
        mock_links = {"example.com": "Example Link"}
        mock_prepare_contexts.return_value = (mock_context_vals, mock_links)
        
        # Call the function under test
        result = get_contexts(
            self.milvus_client_mock, self.guru_type.milvus_collection_name,
            self.question, self.guru_type.slug, self.user_question, self.enhanced_question
        )
        
        # Unpack the result
        context_vals, links, context_distances, reranked_scores, trust_score, processed_ctx_relevances, ctx_rel_usage, times = result
        
        # Verify expected results
        self.assertEqual(context_vals, mock_context_vals)
        self.assertEqual(links, mock_links)
        self.assertEqual(reranked_scores, mock_reranked_scores)
        self.assertEqual(trust_score, mock_trust_score)
        self.assertEqual(processed_ctx_relevances, mock_processed_ctx_relevances)
        self.assertEqual(ctx_rel_usage, mock_ctx_rel_usage)
        self.assertTrue('vector_db_fetch' in times)
        
        # Verify the correct calls were made
        mock_vector_db_fetch.assert_called_once_with(
            self.milvus_client_mock, self.guru_type.milvus_collection_name,
            self.question, self.guru_type.slug, self.user_question, self.enhanced_question
        )
        mock_prepare_contexts.assert_called_once_with(mock_contexts, mock_reranked_scores)
    
    @patch('core.utils.vector_db_fetch')
    @patch('core.utils.prepare_contexts')
    def test_get_contexts_stackoverflow(self, mock_prepare_contexts, mock_vector_db_fetch):
        """Test get_contexts with StackOverflow contexts."""
        # Configure mocks with StackOverflow context structure
        mock_contexts = [{
            "question": {
                "id": "1",
                "distance": 0.1,
                "entity": {
                    "text": "How to center a div?",
                    "metadata": {
                        "question": "Center div",
                        "link": "https://stackoverflow.com/q/1"
                    }
                }
            },
            "accepted_answer": {
                "id": "2",
                "distance": 0.2,
                "entity": {"text": "Use flexbox"}
            },
            "other_answers": [
                {
                    "id": "3",
                    "distance": 0.3,
                    "entity": {"text": "Use grid"}
                }
            ],
            "prefix": "stackoverflow"
        }]
        mock_reranked_scores = [{"index": 0, "score": 0.9}]
        mock_trust_score = 0.85
        mock_processed_ctx_relevances = {"context1": 0.9}
        mock_ctx_rel_usage = {"prompt_tokens": 100}
        mock_vector_db_times = {"total": 0.5}
        
        mock_vector_db_fetch.return_value = (
            mock_contexts, mock_reranked_scores, mock_trust_score, 
            mock_processed_ctx_relevances, mock_ctx_rel_usage, mock_vector_db_times
        )
        
        mock_context_vals = ["Formatted context"]
        mock_links = {"stackoverflow.com/q/1": "Center div"}
        mock_prepare_contexts.return_value = (mock_context_vals, mock_links)
        
        # Call the function under test
        result = get_contexts(
            self.milvus_client_mock, self.guru_type.milvus_collection_name,
            self.question, self.guru_type.slug, self.user_question, self.enhanced_question
        )
        
        # Unpack the result
        context_vals, links, context_distances, reranked_scores, trust_score, processed_ctx_relevances, ctx_rel_usage, times = result
        
        # Verify expected results - especially context_distances handling for StackOverflow
        self.assertEqual(len(context_distances), 3)  # Question + accepted answer + other answer
        self.assertEqual(context_distances[0], {'context_id': '1', 'distance': 0.1})
        self.assertEqual(context_distances[1], {'context_id': '2', 'distance': 0.2})
        self.assertEqual(context_distances[2], {'context_id': '3', 'distance': 0.3})
    
    @patch('core.utils.vector_db_fetch')
    def test_get_contexts_error(self, mock_vector_db_fetch):
        """Test get_contexts when vector_db_fetch raises an exception."""
        # Configure mock to raise exception
        mock_vector_db_fetch.side_effect = Exception("Database error")
        
        # Call the function under test
        result = get_contexts(
            self.milvus_client_mock, self.guru_type.milvus_collection_name,
            self.question, self.guru_type.slug, self.user_question, self.enhanced_question
        )
        
        # Unpack the result
        context_vals, links, context_distances, reranked_scores, trust_score, processed_ctx_relevances, ctx_rel_usage, times = result
        
        # Verify default empty values when error occurs
        self.assertEqual(context_vals, {'contexts': ''})
        self.assertEqual(links, [])
        self.assertEqual(context_distances, [])
        self.assertEqual(reranked_scores, [])
        self.assertEqual(trust_score, 0.0)
        self.assertEqual(processed_ctx_relevances, {'removed': [], 'kept': []})
        self.assertEqual(ctx_rel_usage, {})


class StreamAndSaveTests(TestCase):
    """Tests for stream_and_save utility function."""
    
    def setUp(self):
        """Set up test data for all tests."""
        # Create test guru type
        self.guru_type = GuruType.objects.create(
            name="Test Guru",
            slug="test-guru",
            domain_knowledge="Test domain knowledge"
        )
        
        # Create test user
        self.user = User.objects.create_user(
            name="testuser",
            email="test@example.com",
            password="testpassword"
        )
        
        # Mock question parameters
        self.question = "What is the meaning of life?"
        self.user_question = "Tell me about life's meaning"
        self.question_slug = "what-is-the-meaning-of-life"
        self.description = "A question about life's meaning"
        self.enhanced_question = "Explain the philosophical meaning of life"
        self.source = Question.Source.USER.value
        
        # Mock response data
        self.links = {"example.com": "Example link"}
        self.context_vals = ["Example context"]
        self.context_distances = [{"context_id": "1", "distance": 0.1}]
        self.reranked_scores = [{"index": 0, "score": 0.9}]
        self.trust_score = 0.85
        self.processed_ctx_relevances = {"context1": 0.9}
        self.ctx_rel_usage = {"prompt_tokens": 50, "completion_tokens": 30, "cost_dollars": 0.001}
        
        # Mock summary tokens
        self.summary_prompt_tokens = 100
        self.summary_completion_tokens = 50
        self.summary_cached_tokens = 20
        
        # Mock times
        self.times = {
            "summary": {"total": 0.2},
            "before_stream": {"total": 0.1}
        }
        
        # Create mock stream response
        self.mock_response = MagicMock()
        self.mock_chunk = MagicMock()
        self.mock_response.__iter__ = MagicMock(return_value=iter([self.mock_chunk]))
        self.mock_chunk.choices = [MagicMock()]
        self.mock_chunk.choices[0].delta.content = "Test response"
        
        # Mock for tokens
        self.prompt_tokens = 150
        self.completion_tokens = 75
        self.cached_prompt_tokens = 30
    
    @patch('core.utils.get_tokens_from_openai_response')
    @patch('core.utils.get_llm_usage')
    @patch('core.utils.get_cloudflare_requester')
    def test_stream_and_save_new_question(self, mock_get_cloudflare_requester, mock_get_llm_usage, mock_get_tokens):
        """Test stream_and_save creating a new Question."""
        # Configure mocks
        mock_get_tokens.return_value = (self.prompt_tokens, self.completion_tokens, self.cached_prompt_tokens)
        mock_get_llm_usage.return_value = 0.05  # Cost in dollars
        
        # Make the response iterable and set up content
        response_chunks = [
            self.mock_chunk,
            self.mock_chunk  # Multiple chunks to test aggregation
        ]
        response_iter = MagicMock()
        response_iter.__iter__.return_value = iter(response_chunks)
        
        # Set up the test prompt
        test_prompt = "Test system prompt"
        
        # Execute the generator function and collect yielded values
        generator = stream_and_save(
            self.user_question, self.question, self.guru_type, self.question_slug,
            self.description, response_iter, test_prompt, self.links,
            self.summary_completion_tokens, self.summary_prompt_tokens, self.summary_cached_tokens,
            self.context_vals, self.context_distances, self.times, self.reranked_scores,
            self.trust_score, self.processed_ctx_relevances, self.ctx_rel_usage,
            self.enhanced_question, self.user, source=self.source
        )
        
        # Collect all yielded values
        yielded_values = list(generator)
        
        # Check that the yielded values match the expected content
        self.assertEqual(yielded_values, ["Test response", "Test response"])
        
        # Verify a new Question was created
        saved_question = Question.objects.get(slug=self.question_slug)
        self.assertEqual(saved_question.question, self.question)
        self.assertEqual(saved_question.user_question, self.user_question)
        self.assertEqual(saved_question.enhanced_question, self.enhanced_question)
        self.assertEqual(saved_question.content, "Test responseTest response")  # Combined chunks
        self.assertEqual(saved_question.guru_type, self.guru_type)
        self.assertEqual(saved_question.prompt, test_prompt)
        self.assertEqual(saved_question.references, self.links)
        self.assertEqual(saved_question.context_distances, self.context_distances)
        self.assertEqual(saved_question.reranked_scores, self.reranked_scores)
        self.assertEqual(saved_question.trust_score, self.trust_score)
        self.assertEqual(saved_question.user, self.user)
        self.assertEqual(saved_question.processed_ctx_relevances, self.processed_ctx_relevances)
    
    @patch('core.utils.get_tokens_from_openai_response')
    @patch('core.utils.get_llm_usage')
    @patch('core.utils.get_cloudflare_requester')
    def test_stream_and_save_existing_question(self, mock_get_cloudflare_requester, mock_get_llm_usage, mock_get_tokens):
        """Test stream_and_save updating an existing Question."""
        # Create an existing question
        existing_question = Question.objects.create(
            slug=self.question_slug,
            question="Old question",
            user_question="Old user question",
            content="Old content",
            description="Old description",
            guru_type=self.guru_type,
            change_count=0
        )
        
        # Configure mocks
        mock_get_tokens.return_value = (self.prompt_tokens, self.completion_tokens, self.cached_prompt_tokens)
        mock_get_llm_usage.return_value = 0.05  # Cost in dollars
        
        # Mock Cloudflare requester
        mock_cloudflare = MagicMock()
        mock_get_cloudflare_requester.return_value = mock_cloudflare
        
        # Make the response iterable and set up content
        response_chunks = [self.mock_chunk]
        response_iter = MagicMock()
        response_iter.__iter__.return_value = iter(response_chunks)
        
        # Set up the test prompt
        test_prompt = "Test system prompt"
        
        # Execute the generator function
        generator = stream_and_save(
            self.user_question, self.question, self.guru_type, self.question_slug,
            self.description, response_iter, test_prompt, self.links,
            self.summary_completion_tokens, self.summary_prompt_tokens, self.summary_cached_tokens,
            self.context_vals, self.context_distances, self.times, self.reranked_scores,
            self.trust_score, self.processed_ctx_relevances, self.ctx_rel_usage,
            self.enhanced_question, self.user, source=self.source
        )
        
        # Consume the generator
        list(generator)
        
        # Refresh the question from the database
        updated_question = Question.objects.get(id=existing_question.id)
        
        # Verify the question was updated
        self.assertEqual(updated_question.question, self.question)
        self.assertEqual(updated_question.user_question, self.user_question)
        self.assertEqual(updated_question.content, "Test response")
        self.assertEqual(updated_question.change_count, 1)  # Incremented
        self.assertEqual(updated_question.enhanced_question, self.enhanced_question)
        
        # Verify Cloudflare cache was purged
        mock_cloudflare.purge_cache.assert_called_once_with(self.guru_type.slug, self.question_slug)
    
    @patch('core.utils.get_tokens_from_openai_response')
    @patch('core.utils.get_llm_usage')
    def test_stream_and_save_with_binge(self, mock_get_llm_usage, mock_get_tokens):
        """Test stream_and_save with a Binge instance."""
        # Create a binge
        binge = Binge.objects.create(
            guru_type=self.guru_type
        )
        
        # Configure mocks
        mock_get_tokens.return_value = (self.prompt_tokens, self.completion_tokens, self.cached_prompt_tokens)
        mock_get_llm_usage.return_value = 0.05  # Cost in dollars
        
        # Make the response iterable
        response_chunks = [self.mock_chunk]
        response_iter = MagicMock()
        response_iter.__iter__.return_value = iter(response_chunks)
        
        # Set up the test prompt
        test_prompt = "Test system prompt"
        
        # Execute the generator function
        generator = stream_and_save(
            self.user_question, self.question, self.guru_type, self.question_slug,
            self.description, response_iter, test_prompt, self.links,
            self.summary_completion_tokens, self.summary_prompt_tokens, self.summary_cached_tokens,
            self.context_vals, self.context_distances, self.times, self.reranked_scores,
            self.trust_score, self.processed_ctx_relevances, self.ctx_rel_usage,
            self.enhanced_question, self.user, binge=binge, source=self.source
        )
        
        # Consume the generator
        list(generator)
        
        # Verify a Question was created with the binge
        saved_question = Question.objects.get(slug=self.question_slug)
        self.assertEqual(saved_question.binge, binge)
        
        # Refresh binge to verify last_used is updated
        binge.refresh_from_db()
        self.assertIsNotNone(binge.last_used)


class GetQuestionSummaryTests(TestCase):
    """Tests for get_question_summary and get_summary utility functions."""
    
    def setUp(self):
        """Set up test data for all tests."""
        # Create a test guru type
        self.guru_type = GuruType.objects.create(
            name="Test Guru",
            slug="test-guru",
            domain_knowledge="Test domain knowledge",
            language=GuruType.Language.ENGLISH
        )
        
        # Create a binge
        self.binge = Binge.objects.create(
            guru_type=self.guru_type
        )
        
        # Mock question parameters
        self.question = "What is the meaning of life?"
    
    @patch('core.utils.get_summary')
    @patch('core.utils.parse_summary_response')
    def test_get_question_summary_success(self, mock_parse_summary_response, mock_get_summary):
        """Test successful question summary generation."""
        # Configure mocks
        mock_response = MagicMock()
        mock_get_summary_times = {"total": 0.5}
        mock_get_summary.return_value = (mock_response, mock_get_summary_times)
        
        mock_parsed_response = {
            'question': 'Meaning of life?',
            'user_question': self.question,
            'question_slug': 'meaning-of-life',
            'description': 'A philosophical question',
            'valid_question': True,
            'completion_tokens': 50,
            'prompt_tokens': 100,
            'cached_prompt_tokens': 20,
            'user_intent': 'answer',
            'answer_length': 'medium',
            'enhanced_question': 'What is the philosophical meaning of life?',
            'jwt': 'test-jwt'
        }
        mock_parse_summary_response.return_value = mock_parsed_response
        
        # Call the function under test
        result, times = get_question_summary(
            self.question, self.guru_type.slug, self.binge
        )
        
        # Verify expected results
        self.assertEqual(result['question'], 'Meaning of life?')
        self.assertEqual(result['user_question'], self.question)
        self.assertIn('meaning-of-life-', result['question_slug'])  # Check UUID was appended
        self.assertEqual(result['description'], 'A philosophical question')
        self.assertEqual(result['valid_question'], True)
        self.assertEqual(result['jwt'], 'test-jwt')
        
        # Verify times were correctly tracked
        self.assertTrue('total' in times)
        self.assertTrue('get_summary' in times)
        self.assertTrue('parse_summary_response' in times)
    
    @patch('core.utils.get_summary')
    @patch('core.utils.parse_summary_response')
    def test_get_question_summary_with_parent(self, mock_parse_summary_response, mock_get_summary):
        """Test question summary generation with a parent question."""
        # Create a parent question
        parent_question = Question.objects.create(
            slug="parent-question",
            question="Parent question",
            content="Parent answer",
            guru_type=self.guru_type
        )
        
        # Configure mocks
        mock_response = MagicMock()
        mock_get_summary_times = {"total": 0.5}
        mock_get_summary.return_value = (mock_response, mock_get_summary_times)
        
        mock_parsed_response = {
            'question': 'Follow-up question',
            'user_question': self.question,
            'question_slug': 'follow-up-question',
            'description': 'A follow-up',
            'valid_question': True,
            'completion_tokens': 50,
            'prompt_tokens': 100,
            'cached_prompt_tokens': 20,
            'enhanced_question': 'What is the follow-up?',
            'jwt': 'test-jwt'
        }
        mock_parse_summary_response.return_value = mock_parsed_response
        
        # Call the function under test with parent_question
        result, times = get_question_summary(
            self.question, self.guru_type.slug, self.binge, 
            parent_question=parent_question
        )
        
        # Verify parent question was passed to get_summary
        mock_get_summary.assert_called_once_with(
            self.question, self.guru_type.slug, False, None, parent_question
        )
    
    @patch('core.utils.get_openai_requester')
    @patch('core.utils.get_guru_type_prompt_map')
    def test_get_summary_success(self, mock_get_guru_type_prompt_map, mock_get_openai_requester):
        """Test successful summary generation."""
        # Configure mocks
        prompt_map = {
            'guru_type': 'Test Guru',
            'domain_knowledge': 'Test knowledge',
            'language': 'English'
        }
        mock_get_guru_type_prompt_map.return_value = prompt_map
        
        mock_openai_requester = MagicMock()
        mock_response = MagicMock()
        mock_openai_requester.get_summary.return_value = mock_response
        mock_get_openai_requester.return_value = mock_openai_requester
        
        # Call the function under test
        response, times = get_summary(self.question, self.guru_type.slug)
        
        # Verify expected results
        self.assertEqual(response, mock_response)
        self.assertTrue('total' in times)
        self.assertTrue('prompt_prep' in times)
        self.assertTrue('response_await' in times)
        
        # Verify the right prompt was built and passed
        mock_openai_requester.get_summary.assert_called_once()
    
    @patch('core.utils.get_openai_requester')
    @patch('core.utils.get_guru_type_prompt_map')
    def test_get_summary_with_short_answer(self, mock_get_guru_type_prompt_map, mock_get_openai_requester):
        """Test summary generation with short answer flag."""
        # Configure mocks
        prompt_map = {
            'guru_type': 'Test Guru',
            'domain_knowledge': 'Test knowledge',
            'language': 'English'
        }
        mock_get_guru_type_prompt_map.return_value = prompt_map
        
        mock_openai_requester = MagicMock()
        mock_response = MagicMock()
        mock_openai_requester.get_summary.return_value = mock_response
        mock_get_openai_requester.return_value = mock_openai_requester
        
        # Call the function under test with short_answer=True
        response, times = get_summary(self.question, self.guru_type.slug, short_answer=True)
        
        # Verify expected results
        self.assertEqual(response, mock_response)
        
        # The short answer flag should affect the prompt template used
        # Since we're mocking the implementation, we just verify the right parameters were passed
        mock_openai_requester.get_summary.assert_called_once()
    
    @patch('core.utils.get_openai_requester')
    @patch('core.utils.get_guru_type_prompt_map')
    def test_get_summary_error(self, mock_get_guru_type_prompt_map, mock_get_openai_requester):
        """Test summary generation when an error occurs."""
        # Configure mocks
        prompt_map = {
            'guru_type': 'Test Guru',
            'domain_knowledge': 'Test knowledge',
            'language': 'English'
        }
        mock_get_guru_type_prompt_map.return_value = prompt_map
        
        mock_openai_requester = MagicMock()
        mock_openai_requester.get_summary.side_effect = Exception("API error")
        mock_get_openai_requester.return_value = mock_openai_requester
        
        # Call the function under test
        response, times = get_summary(self.question, self.guru_type.slug)
        
        # Verify expected results
        self.assertIsNone(response)  # Should return None on error
        self.assertTrue('total' in times)
