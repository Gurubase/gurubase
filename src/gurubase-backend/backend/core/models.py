import secrets
from django.db import transaction
import traceback
import logging
import os
import uuid
from django.conf import settings
from django.db import models
from django.db.models import Index
from datetime import datetime
from django.core.exceptions import ValidationError
from urllib.parse import urlparse
from django.core.validators import URLValidator, MaxValueValidator

from accounts.models import User

logger = logging.getLogger(__name__)


def get_datasource_upload_path(instance, filename):
    """
    Generate dynamic upload path for DataSource files.
    Path format: data_sources/<guru_type_slug>/<filename>
    """
    guru_type_slug = instance.guru_type.slug.lower()
    return f'data_sources/{guru_type_slug}/{filename}'


class Question(models.Model):
    class Source(models.TextChoices):
        USER = "USER"
        RAW_QUESTION = "RAW_QUESTION"
        REDDIT = "REDDIT"
        SUMMARY_QUESTION = "SUMMARY QUESTION"
        WIDGET_QUESTION = "WIDGET QUESTION"
        API = "API"
        DISCORD = "DISCORD"
        SLACK = "SLACK"
        GITHUB = "GITHUB"

    slug = models.SlugField(max_length=1500)
    question = models.TextField()
    old_question = models.TextField(default='', blank=True, null=True)  # For tracking changes
    user_question = models.TextField(default='', blank=True, null=True)
    og_image_url = models.URLField(max_length=2000, default='', blank=True, null=True)
    content = models.TextField()
    is_helpful = models.BooleanField(null=True, blank=True)
    description = models.TextField()
    change_count = models.IntegerField(default=0)
    date_created = models.DateTimeField(auto_now_add=True)
    date_updated = models.DateTimeField(auto_now=True)
    add_to_sitemap = models.BooleanField(default=False)
    sitemap_reason = models.TextField(default='', blank=True, null=True)
    sitemap_date = models.DateTimeField(null=True, blank=True)

    similar_questions = models.JSONField(default=dict, blank=True, null=False)
    context_distances = models.JSONField(default=list, blank=True, null=False)
    reranked_scores = models.JSONField(default=list, blank=True, null=False)

    default_question = models.BooleanField(default=False)

    guru_type = models.ForeignKey(
        "GuruType", on_delete=models.SET_NULL, null=True, blank=True
    )

    cost_dollars = models.FloatField(default=0, blank=True, null=True)
    completion_tokens = models.PositiveIntegerField(default=0, blank=True, null=True)
    prompt_tokens = models.PositiveIntegerField(default=0, blank=True, null=True)
    cached_prompt_tokens = models.PositiveIntegerField(
        default=0, blank=True, null=True)  # Already included in prompt_tokens
    latency_sec = models.FloatField(default=0, blank=True, null=True)
    source = models.CharField(
        max_length=50,
        choices=[(tag.value, tag.value) for tag in Source],
        default=Source.USER.value,
    )
    references = models.JSONField(default=dict, blank=True, null=True)
    prompt = models.TextField(default="", blank=True, null=True)

    english = models.BooleanField(default=True)
    title_processed = models.BooleanField(default=False)
    llm_eval = models.BooleanField(default=False)
    similarity_written_to_milvus = models.BooleanField(default=False)
    parent = models.ForeignKey("self", on_delete=models.SET_NULL, null=True, blank=True, related_name="parent_question")
    follow_up_questions = models.JSONField(default=list, blank=True, null=False)
    binge = models.ForeignKey("Binge", on_delete=models.SET_NULL, null=True, blank=True, default=None)
    cache_request_count = models.IntegerField(default=0)
    # Avg context relevance of the contexts passing the minimum threshold. Between 0 and 1.
    trust_score = models.FloatField(default=0, blank=True, null=True)
    processed_ctx_relevances = models.JSONField(default=dict, blank=True, null=False)
    llm_usages = models.JSONField(default=dict, blank=True, null=False)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    times = models.JSONField(default=dict, blank=True, null=False)
    enhanced_question = models.TextField(default='', blank=True, null=True)

    @property
    def frontend_url(self):
        """Returns the frontend URL for this question."""
        from django.conf import settings
        if not self.guru_type:
            return ""
            
        if self.binge:
            root_slug = self.binge.root_question.slug if self.binge.root_question else self.slug
            return f"{settings.BASE_URL}/g/{self.guru_type.slug}/{root_slug}/binge/{self.binge.id}?question_slug={self.slug}"
        
        return f"{settings.BASE_URL}/g/{self.guru_type.slug}/{self.slug}"

    def __str__(self):
        return f"{self.id} - {self.slug}"

    def save(self, *args, **kwargs):
        if not self.binge:
            # Check uniqueness for non-binge questions
            existing_by_slug = Question.objects.filter(
                slug=self.slug,
                guru_type=self.guru_type,
                binge__isnull=True
            ).exclude(pk=self.pk).exists()

            if existing_by_slug:
                raise ValidationError("A question with this slug and guru type already exists")

            # This does not include Slack and Discord as all of the questions there belong to binges.
            if self.source not in [Question.Source.API.value, Question.Source.WIDGET_QUESTION.value]:
                existing_by_question = Question.objects.exclude(source__in=[Question.Source.API.value, Question.Source.WIDGET_QUESTION.value]).filter(
                    question=self.question,
                    guru_type=self.guru_type,
                    binge__isnull=True,
                ).exclude(pk=self.pk).exists()

                if existing_by_question:
                    raise ValidationError("A question with this text and guru type already exists")
        else:
            # Check uniqueness for binge questions
            existing_binge = Question.objects.filter(
                binge=self.binge,
                slug=self.slug,
                guru_type=self.guru_type
            ).exclude(pk=self.pk).exists()

            if existing_binge:
                raise ValidationError("A question with this slug and guru type already exists in this binge")

        total_cost_dollars = 0
        for prices in self.llm_usages.values():
            total_cost_dollars += prices['cost_dollars']
        self.cost_dollars = total_cost_dollars

        if not self.user_question:
            self.user_question = self.question

        super().save(*args, **kwargs)

    class Meta:
        indexes = [
            Index(fields=["add_to_sitemap"]),
            Index(fields=["guru_type"]),
            Index(fields=["date_created"]),
            Index(fields=["source"]),
            Index(fields=["guru_type", "date_created"]),
            Index(fields=["guru_type", "source"]),
        ]

    @property
    def total_tokens(self):
        return self.prompt_tokens + self.completion_tokens

    def is_on_sitemap(self):
        from core.utils import get_default_settings, get_most_similar_questions
        add_to_sitemap = True
        sitemap_reason = None

        if self.parent:
            add_to_sitemap = False
            sitemap_reason = "Is a follow up question"
            return add_to_sitemap, sitemap_reason

        # If not belonging to a custom guru, return False
        # if not self.guru_type.custom:
        #     add_to_sitemap = False
        #     sitemap_reason = "Not belonging to a custom guru"
        #     return add_to_sitemap, sitemap_reason

        if self.source not in [Question.Source.SUMMARY_QUESTION.value, Question.Source.RAW_QUESTION.value]:
            add_to_sitemap = False
            sitemap_reason = "Not a summary or raw question"
            return add_to_sitemap, sitemap_reason

        if not self.english:
            add_to_sitemap = False
            sitemap_reason = "Not English"
            return add_to_sitemap, sitemap_reason

        default_settings = get_default_settings()
        reranked_scores = self.reranked_scores
        avg_score = sum(map(lambda x: x['score'], reranked_scores)) / len(reranked_scores) if reranked_scores else 0

        if avg_score < default_settings.rerank_threshold:
            add_to_sitemap = False
            sitemap_reason = f"Rerank avg score too low: {avg_score} < {default_settings.rerank_threshold}"
            return add_to_sitemap, sitemap_reason

        # If there is another question with the same title, do not add to sitemap
        questions_with_same_title = Question.objects.filter(
            question=self.question, add_to_sitemap=True).exclude(id=self.id)
        if questions_with_same_title.exists():
            add_to_sitemap = False
            sitemap_reason = f"Same title with ID: {questions_with_same_title.first().id}"
            logger.info(
                f"Question {self.id} has another question with the same title. Not adding to sitemap.", exc_info=True)
            return add_to_sitemap, sitemap_reason

        # Get the closest first question
        similar_questions = get_most_similar_questions(
            self.slug, self.content, self.guru_type.slug, column='content', top_k=1, sitemap_constraint=True)
        if len(similar_questions) == 0:
            add_to_sitemap = True
        else:
            distance = similar_questions[0]['distance']
            if distance > settings.VECTOR_DISTANCE_THRESHOLD:
                add_to_sitemap = True
            else:
                add_to_sitemap = False
                # DO NOT CHANGE THE REASON TEXT. It's used in the signal: delete_question_similarities
                sitemap_reason = f"Similar to question ID: ({similar_questions[0]['id']}) - ({similar_questions[0]['title']}) with content distance: {distance}"

        # Check also Context Relevance score to check if the threshold is greater than 0.5
        if self.trust_score < settings.SITEMAP_ADD_CONTEXT_RELEVANCE_THRESHOLD:
            add_to_sitemap = False
            sitemap_reason = f"Trust score is low: {self.trust_score} < {settings.SITEMAP_ADD_CONTEXT_RELEVANCE_THRESHOLD}"

        return add_to_sitemap, sitemap_reason


class RawQuestion(models.Model):
    question = models.TextField()
    category = models.TextField(default='')
    guru_type = models.ForeignKey("GuruType", on_delete=models.SET_NULL, null=True, blank=True)
    raw_question_generation = models.ForeignKey(
        "RawQuestionGeneration", on_delete=models.SET_NULL, null=True, blank=True)
    date_created = models.DateTimeField(auto_now_add=True)
    date_updated = models.DateTimeField(auto_now=True)
    processed = models.BooleanField(default=False)

    def __str__(self):
        return str(self.id)


class RawQuestionGeneration(models.Model):

    guru_type = models.ForeignKey(
        "GuruType", on_delete=models.SET_NULL, null=True, blank=True
    )
    sort = models.TextField(null=False, blank=False)
    page_num = models.IntegerField(null=False, blank=False)
    page_size = models.IntegerField(null=False, blank=False)
    generate_count = models.IntegerField(null=False, blank=False)
    model = models.TextField(null=False, blank=False)
    cost_dollars = models.FloatField(default=0, blank=True, null=True)
    prompts = models.JSONField(default=list, blank=True, null=False)

    date_created = models.DateTimeField(auto_now_add=True)
    date_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return str(self.id)


class ContentPageStatistics(models.Model):
    question = models.OneToOneField(
        Question, on_delete=models.CASCADE, related_name="statistics"
    )
    view_count = models.PositiveIntegerField(default=0)
    upvotes = models.PositiveIntegerField(default=0)
    downvotes = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"Statistics for {self.question.slug}"


class QuestionValidityCheckPricing(models.Model):
    slug = models.SlugField(max_length=1500)
    cost_dollars = models.FloatField(default=0, blank=True, null=True)
    completion_tokens = models.PositiveIntegerField(default=0, blank=True, null=True)
    prompt_tokens = models.PositiveIntegerField(default=0, blank=True, null=True)
    cached_prompt_tokens = models.PositiveIntegerField(
        default=0, blank=True, null=True)  # Already included in prompt_tokens

    def __str__(self):
        return str(self.id)

    @property
    def total_tokens(self):
        return self.prompt_tokens + self.completion_tokens


class GuruType(models.Model):
    class EmbeddingModel(models.TextChoices):
        IN_HOUSE = "IN_HOUSE", "In-house embedding model"
        GEMINI_EMBEDDING_001 = "GEMINI_EMBEDDING_001", "Gemini - embedding-001"
        GEMINI_TEXT_EMBEDDING_004 = "GEMINI_TEXT_EMBEDDING_004", "Gemini - text-embedding-004"
        OPENAI_TEXT_EMBEDDING_3_SMALL = "OPENAI_TEXT_EMBEDDING_3_SMALL", "OpenAI - text-embedding-3-small"
        OPENAI_TEXT_EMBEDDING_3_LARGE = "OPENAI_TEXT_EMBEDDING_3_LARGE", "OpenAI - text-embedding-3-large"
        OPENAI_TEXT_EMBEDDING_ADA_002 = "OPENAI_TEXT_EMBEDDING_ADA_002", "OpenAI - text-embedding-ada-002"

    slug = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=50, blank=True, null=True)
    maintainers = models.ManyToManyField(User, blank=True, related_name='maintained_guru_types')
    stackoverflow_tag = models.CharField(max_length=100, blank=True, null=True)
    github_repos = models.JSONField(default=list, blank=True)
    github_details = models.JSONField(default=dict, blank=True, null=False)
    github_details_updated_date = models.DateTimeField(null=True, blank=True)
    colors = models.JSONField(default=dict, blank=True, null=False)
    icon_url = models.CharField(max_length=2000, default="", blank=True, null=True)
    ogimage_url = models.URLField(max_length=2000, default="", blank=True, null=True)  # question
    ogimage_base_url = models.URLField(max_length=2000, default="", blank=True, null=True)
    stackoverflow_source = models.BooleanField(default=True)  # Set this to false for custom guru types
    active = models.BooleanField(default=False)
    intro_text = models.TextField(default='', blank=True, null=True)
    custom = models.BooleanField(default=True)
    milvus_collection_name = models.CharField(max_length=100, blank=True, null=True)
    typesense_collection_name = models.CharField(max_length=100, blank=True, null=True)
    domain_knowledge = models.TextField(default='', blank=True, null=True)
    has_sitemap_added_questions = models.BooleanField(default=False)
    index_repo = models.BooleanField(default=True)
    # GitHub repository limits
    github_repo_count_limit = models.IntegerField(default=1)
    github_file_count_limit_per_repo_soft = models.IntegerField(default=1000)  # Warning threshold
    github_file_count_limit_per_repo_hard = models.IntegerField(default=1500)  # Absolute maximum
    github_repo_size_limit_mb = models.IntegerField(default=100)
    # Data source limits
    website_count_limit = models.IntegerField(default=1500)
    youtube_count_limit = models.IntegerField(default=100)
    pdf_size_limit_mb = models.IntegerField(default=100)

    text_embedding_model = models.CharField(
        max_length=100,
        choices=EmbeddingModel.choices,
        default=None,  # Will be set in save()
        null=True,
        blank=True
    )
    code_embedding_model = models.CharField(
        max_length=100,
        choices=EmbeddingModel.choices,
        default=None,  # Will be set in save()
        null=True,
        blank=True
    )
    send_notification = models.BooleanField(default=False)

    date_created = models.DateTimeField(auto_now_add=True)
    date_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.slug

    def save(self, *args, **kwargs):
        from core.utils import validate_slug
        from core.guru_types import generate_milvus_collection_name, generate_typesense_collection_name

        # Set default embedding models if not set
        if not self.text_embedding_model:
            self.text_embedding_model = Settings.get_default_embedding_model()
        if not self.code_embedding_model:
            self.code_embedding_model = Settings.get_default_embedding_model()

        if 'domain_knowledge' not in self.prompt_map:
            raise ValidationError({'msg': 'Domain knowledge field is required'})

        domain_knowledge = self.prompt_map['domain_knowledge']
        if len(domain_knowledge) > 200:
            raise ValidationError({'msg': f'Domain knowledge must be 200 characters or less. Got: {domain_knowledge}'})

        if not self.id:  # If it is a new object
            if not self.slug:
                self.slug = validate_slug(self.name)

            self.milvus_collection_name = generate_milvus_collection_name(self.slug)
            self.typesense_collection_name = generate_typesense_collection_name(self.slug)

        if ' ' in self.slug:
            raise ValidationError({'msg': 'Guru type name must not contain spaces'})

        if self.slug == '':
            raise ValidationError({'msg': 'Guru type name cannot be empty'})

        unique_github_repos = set(self.github_repos)

        if settings.ENV != 'selfhosted' and len(unique_github_repos) > self.github_repo_count_limit:
            raise ValidationError({'msg': f'You have reached the maximum number ({self.github_repo_count_limit}) of GitHub repositories for this guru type.'})

        if settings.ENV == 'selfhosted':
            if self.text_embedding_model == GuruType.EmbeddingModel.IN_HOUSE:
                raise ValidationError({'msg': 'In-house embedding model is not allowed in selfhosted environment.'})
            if self.code_embedding_model == GuruType.EmbeddingModel.IN_HOUSE:
                raise ValidationError({'msg': 'In-house embedding model is not allowed in selfhosted environment.'})

        self.github_repos = list(unique_github_repos)

        super().save(*args, **kwargs)

    def generate_widget_id(self, domain_url):
        """
        Generates a new widget ID for this guru type and domain.
        If an active key exists for the domain, raises ValidationError.
        Validates that the domain URL is properly formatted.
        
        Supports the following domain URL formats:
        - Standard URLs: 'https://example.com', 'http://subdomain.example.com'
        - Wildcard patterns:
          - '*': Match any domain (universal wildcard)
          - 'http://localhost:*': Match localhost with any port
          - 'https://*.example.com': Match any subdomain of example.com
        
        Examples:
        - '*' → Allow from any domain
        - 'http://localhost:*' → Allow from localhost with any port (localhost:3000, localhost:8080, etc.)
        - 'https://*.example.com' → Allow from any subdomain of example.com (app.example.com, api.example.com, etc.)
        - 'https://example.com' → Allow only from exact domain example.com
        """
        if domain_url:
            # Normalize domain_url
            domain_url = domain_url.rstrip('/')

            # Check if this is a wildcard pattern
            is_wildcard = '*' in domain_url
            
            # For non-wildcard URLs, perform standard validation
            if not is_wildcard:
                # Standard URL validation
                url_validator = URLValidator()
                try:
                    url_validator(domain_url)
                except ValidationError:
                    raise ValidationError({'msg': 'Invalid URL format'})

                # Additional domain validation
                parsed_url = urlparse(domain_url)
                if not parsed_url.netloc:
                    raise ValidationError({'msg': 'Invalid domain URL'})

                # Ensure URL has valid scheme
                if parsed_url.scheme not in ['http', 'https']:
                    raise ValidationError({'msg': 'URL must start with http:// or https://'})

        # Check for existing widget for this domain/guru type combination
        existing_key = WidgetId.objects.filter(
            guru_type=self,
            domain_url=domain_url,
        ).first()

        if existing_key:
            raise ValidationError({'msg': 'This domain url already has a widget ID'})

        # Generate new key
        key = secrets.token_urlsafe(32)
        WidgetId.objects.create(
            guru_type=self,
            key=key,
            domain_url=domain_url,
            is_wildcard=is_wildcard if domain_url else False
        )
        return key

    @property
    def prompt_map(self):
        return {
            "guru_type": self.name,
            "domain_knowledge": self.domain_knowledge
        }

    @property
    def ready(self):
        # Check if all its data sources are processed
        non_processed_count = DataSource.objects.filter(guru_type=self, status=DataSource.Status.NOT_PROCESSED).count()
        non_written_count = DataSource.objects.filter(
            guru_type=self, status=DataSource.Status.SUCCESS, in_milvus=False).count()

        return non_processed_count == 0 and non_written_count == 0

    def check_datasource_limits(self, user, file=None, website_urls_count=0, youtube_urls_count=0, github_urls_count=0):
        """
        Checks if adding a new datasource would exceed the limits for this guru type.
        Returns (bool, str) tuple - (is_allowed, error_message)
        """
        if settings.ENV != 'selfhosted':
            # Check if user is maintainer
            if not self.maintainers.filter(id=user.id).exists():
                if user.is_admin:
                    # If user is admin, only check the limits
                    pass
                else:
                    return False, "You don't have permission to add data sources to this guru type"
        
        if settings.ENV == 'selfhosted':
            # Selfhosted users bypass all limits
            return True, None

        # Get current counts
        website_count = DataSource.objects.filter(
            guru_type=self,
            type=DataSource.Type.WEBSITE
        ).count()

        youtube_count = DataSource.objects.filter(
            guru_type=self,
            type=DataSource.Type.YOUTUBE
        ).count()

        github_count = DataSource.objects.filter(
            guru_type=self,
            type=DataSource.Type.GITHUB_REPO
        ).count()

        # Get total PDF size in MB
        pdf_sources = DataSource.objects.filter(
            guru_type=self,
            type=DataSource.Type.PDF
        )
        total_pdf_mb = 0
        for source in pdf_sources:
            if source.file:
                total_pdf_mb += source.file.size / (1024 * 1024)  # Convert bytes to MB

        # Check website limit
        if (website_count + website_urls_count) > self.website_count_limit:
            return False, f"Website limit ({self.website_count_limit}) reached"

        # Check YouTube limit
        if (youtube_count + youtube_urls_count) > self.youtube_count_limit:
            return False, f"YouTube video limit ({self.youtube_count_limit}) reached"

        # Check GitHub repo limit
        if (github_count + github_urls_count) > self.github_repo_count_limit:
            return False, f"GitHub repository limit ({self.github_repo_count_limit}) reached"

        # Check PDF size limit if file provided
        if file:
            file_size_mb = file.size / (1024 * 1024)
            if total_pdf_mb + file_size_mb > self.pdf_size_limit_mb:
                return False, f"Total PDF size limit ({self.pdf_size_limit_mb}MB) would be exceeded"

        return True, None


class LLMEval(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='llm_evals')
    model = models.TextField()
    version = models.IntegerField(default=1)
    # relevance = models.FloatField(default=0, blank=True, null=True)
    # relevance_cot = models.TextField(default='', blank=True, null=True)

    # sentiment = models.FloatField(default=0, blank=True, null=True)
    # sentiment_cot = models.TextField(default='', blank=True, null=True)

    # conciseness = models.FloatField(default=0, blank=True, null=True)
    # conciseness_cot = models.TextField(default='', blank=True, null=True)

    # correctness = models.FloatField(default=0, blank=True, null=True)
    # correctness_cot = models.TextField(default='', blank=True, null=True)

    # coherence = models.FloatField(default=0, blank=True, null=True)
    # coherence_cot = models.TextField(default='', blank=True, null=True)

    context_relevance = models.FloatField(default=0, blank=True, null=True)
    context_relevance_cot = models.TextField(default='', blank=True, null=True)
    context_relevance_prompt = models.TextField(default='', blank=True, null=True)
    context_relevance_user_prompt = models.TextField(default='', blank=True, null=True)

    groundedness = models.FloatField(default=0, blank=True, null=True)
    groundedness_cot = models.TextField(default='', blank=True, null=True)
    groundedness_prompt = models.TextField(default='', blank=True, null=True)

    answer_relevance = models.FloatField(default=0, blank=True, null=True)
    answer_relevance_cot = models.TextField(default='', blank=True, null=True)
    answer_relevance_prompt = models.TextField(default='', blank=True, null=True)
    answer = models.TextField(default='', blank=True, null=True)

    reranked_scores = models.JSONField(default=list, blank=True, null=False)

    cost_dollars = models.FloatField(default=0, blank=True, null=True)
    prompt_tokens = models.PositiveIntegerField(default=0, blank=True, null=True)
    completion_tokens = models.PositiveIntegerField(default=0, blank=True, null=True)
    cached_prompt_tokens = models.PositiveIntegerField(
        default=0, blank=True, null=True)  # Already included in prompt_tokens
    prompt = models.TextField(default='', blank=True, null=True)
    contexts = models.JSONField(default=list, blank=True, null=False)
    settings = models.JSONField(default=dict, blank=True, null=False)
    date_created = models.DateTimeField(auto_now_add=True)
    date_updated = models.DateTimeField(auto_now=True)

    processed_ctx_relevances = models.JSONField(default=dict, blank=True, null=False)

    def __str__(self):
        return f"{self.id}"

    @property
    def total_tokens(self):
        return self.prompt_tokens + self.completion_tokens


class DataSource(models.Model):
    class Type(models.TextChoices):
        PDF = "PDF"
        WEBSITE = "WEBSITE"
        YOUTUBE = "YOUTUBE"
        GITHUB_REPO = "GITHUB_REPO"

    class Status(models.TextChoices):
        NOT_PROCESSED = "NOT_PROCESSED"
        SUCCESS = "SUCCESS"
        FAIL = "FAIL"

    type = models.CharField(
        max_length=50,
        choices=[(tag.value, tag.value) for tag in Type],
        default=Type.PDF.value,
    )
    url = models.URLField(max_length=2000, null=True, blank=True)  # If website or youtube
    guru_type = models.ForeignKey(
        GuruType, on_delete=models.CASCADE, null=True, blank=True
    )
    title = models.TextField(null=True, blank=True)
    file = models.FileField(
        upload_to=get_datasource_upload_path,
        blank=True,
        null=True
    )
    content = models.TextField(null=True, blank=True)
    in_milvus = models.BooleanField(default=False)
    doc_ids = models.JSONField(
        default=list, blank=True, null=True
    )  # If written to milvus
    status = models.CharField(
        max_length=50,
        choices=[(tag.value, tag.value) for tag in Status],
        default=Status.NOT_PROCESSED.value,
    )
    error = models.TextField(default='', blank=True, null=False)
    user_error = models.TextField(default='', blank=True, null=False)
    content_rewritten = models.BooleanField(default=False)
    original_content = models.TextField(null=True, blank=True)

    date_created = models.DateTimeField(auto_now_add=True)
    date_updated = models.DateTimeField(auto_now=True)
    initial_summarizations_created = models.BooleanField(default=False)
    final_summarization_created = models.BooleanField(default=False)

    default_branch = models.CharField(max_length=100, null=True, blank=True)  # Only used for Github Repos

    private = models.BooleanField(default=False)

    last_reindex_date = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    reindex_count = models.IntegerField(default=0)

    scrape_tool = models.CharField(max_length=100, null=True, blank=True)
    last_successful_index_date = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ["url", "guru_type"]

    def __str__(self):
        return f"{self.id} - {self.title}"

    def get_file_path(self):
        # Only used once while writing, after that, it is written to url
        guru_type = self.guru_type.slug.lower()
        file_name = os.path.basename(self.file.name)
        name, ext = os.path.splitext(file_name)
        random_key = uuid.uuid4().hex[:30]
        if self.guru_type.custom:
            return f'./{settings.ENV}/custom_gurus/{guru_type}/{name}-{random_key}{ext}'
        return f'./{settings.ENV}/default_gurus/{guru_type}/{name}-{random_key}{ext}'

    def get_file_path_local(self):
        return os.path.join(settings.MEDIA_ROOT, 'data_sources', self.guru_type.slug, self.file.name)

    def get_url_prefix(self):
        return f'https://storage.googleapis.com/{settings.GS_DATA_SOURCES_BUCKET_NAME}'

    def get_metadata(self):
        if self.type == DataSource.Type.PDF:
            return {
                'title': self.title,
            }
        return {
            'link': self.url,
            'title': self.title,
        }

    def save(self, *args, **kwargs):
        # If it is already created
        if self.id:
            super().save(*args, **kwargs)
            return

        # Check for existence. Return if it exists
        if self.type == DataSource.Type.PDF:
            self.title = self.file.name.split('/')[-1]
            existing_data_source = DataSource.objects.filter(
                type=self.type,
                guru_type=self.guru_type,
                title=self.title).first()
        else:
            existing_data_source = DataSource.objects.filter(
                type=self.type,
                guru_type=self.guru_type,
                url=self.url).first()

        if existing_data_source:
            raise DataSourceExists({'id': existing_data_source.id, 'title': existing_data_source.title})

        if self.type == DataSource.Type.PDF:
            if self.file:
                if settings.STORAGE_TYPE == 'gcloud':
                    from core.gcp import DATA_SOURCES_GCP
                    expected_path = self.get_file_path()
                    path, success = DATA_SOURCES_GCP.upload_file(self.file, expected_path)
                    if not success:
                        raise Exception("Failed to upload file")
                    self.url = f'{self.get_url_prefix()}/{expected_path.lstrip("./")}'
                else:
                    self.url = self.get_file_path_local()
            else:
                raise Exception("File is required")
        else:
            # Check if url format is valid
            if not self.url.startswith(('http://', 'https://')):
                raise ValidationError({'msg': 'Invalid URL format'})

        if self.type == DataSource.Type.GITHUB_REPO:
            if settings.ENV != 'selfhosted' and DataSource.objects.filter(type=self.type, guru_type=self.guru_type).count() > self.guru_type.github_repo_count_limit:
                raise ValidationError({'msg': f"You have reached the maximum number ({self.guru_type.github_repo_count_limit}) of GitHub repositories for this guru type."})

        super().save(*args, **kwargs)


    def write_to_milvus(self, overridden_model=None):
        # Model override is added to reinsert code context after changing the embedding model
        from core.utils import embed_texts_with_model, split_text, map_extension_to_language, split_code, get_embedding_model_config
        from core.milvus_utils import insert_vectors
        from django.conf import settings

        if self.in_milvus:
            return

        if overridden_model:
            model = overridden_model
        else:
            if self.type == DataSource.Type.GITHUB_REPO:
                model = self.guru_type.code_embedding_model
            else:
                model = self.guru_type.text_embedding_model

        if self.type == DataSource.Type.GITHUB_REPO:
            collection_name, dimension = get_embedding_model_config(model)
        else:
            _, dimension = get_embedding_model_config(model)
            collection_name = self.guru_type.milvus_collection_name

        if self.type == DataSource.Type.GITHUB_REPO:
            github_files = GithubFile.objects.filter(data_source=self, in_milvus=False)
            logger.info(f"Writing {len(github_files)} GitHub files to Milvus. Repository: {self.url}")
            doc_ids = self.doc_ids
            
            # Process files in batches
            batch_size = settings.GITHUB_FILE_BATCH_SIZE
            for i in range(0, len(github_files), batch_size):
                batch = github_files[i:i + batch_size]
                logger.info(f"Processing batch {i//batch_size + 1} of {(len(github_files) + batch_size - 1)//batch_size}. Repository: {self.url}")
                
                # Prepare all texts and metadata for the batch
                all_texts = []
                all_metadata = []
                file_text_counts = []  # Keep track of how many text chunks each file has
                
                for file in batch:
                    # Split the content into chunks
                    extension = file.path.split('/')[-1].split('.')[-1]
                    language = map_extension_to_language(extension)
                    if language:
                        splitted = split_code(
                            file.content,
                            settings.SPLIT_SIZE,
                            settings.SPLIT_MIN_LENGTH,
                            settings.SPLIT_OVERLAP,
                            language
                        )
                    else:
                        splitted = split_text(
                            file.content,
                            settings.SPLIT_SIZE,
                            settings.SPLIT_MIN_LENGTH,
                            settings.SPLIT_OVERLAP,
                            separators=["\n\n", "\n", ".", "?", "!", " ", ""]
                        )
                    
                    metadata = {
                        "type": file.data_source.type,
                        "repo_link": file.repository_link,
                        "link": file.link,  # Now we can safely use file.link as it's been updated
                        "repo_title": file.repo_title,
                        "title": file.title,
                        "file_path": file.path
                    }
                    
                    # Add texts and metadata
                    all_texts.extend(splitted)
                    all_metadata.extend([metadata] * len(splitted))
                    file_text_counts.append(len(splitted))  # Store count of chunks for this file

                # Batch embed all texts using the configured model
                try:
                    embeddings = embed_texts_with_model(all_texts, model)
                except Exception as e:
                    logger.error(f"Error embedding texts in batch: {traceback.format_exc()}")
                    continue

                if embeddings is None:
                    logger.error("Embeddings is None for batch")
                    continue

                # Prepare documents for Milvus
                docs = []
                split_num = 0
                guru_slug = self.guru_type.slug
                
                for i, (text, metadata, embedding) in enumerate(zip(all_texts, all_metadata, embeddings)):
                    split_num += 1
                    docs.append({
                        "metadata": {**metadata, "split_num": split_num},
                        "text": text,
                        "vector": embedding,
                        "guru_slug": guru_slug,
                    })

                # Write batch to Milvus with the correct collection name and dimension
                try:
                    batch_ids = list(insert_vectors(collection_name, docs, code=True, dimension=dimension))
                    if len(batch_ids) != len(docs):
                        logger.error(f"Error writing batch to Milvus: {len(batch_ids)} != {len(docs)}")
                        continue
                    
                    # Distribute IDs back to files based on chunk counts and prepare for bulk update
                    start_idx = 0
                    files_to_update = []
                    for file, chunk_count in zip(batch, file_text_counts):
                        end_idx = start_idx + chunk_count
                        file_ids = batch_ids[start_idx:end_idx]
                        file.doc_ids = file_ids
                        file.in_milvus = True
                        files_to_update.append(file)
                        start_idx = end_idx
                        doc_ids.extend(file_ids)
                    
                    # Bulk update all files in this batch
                    GithubFile.objects.bulk_update(files_to_update, ['doc_ids', 'in_milvus'])
                    
                except Exception as e:
                    logger.error(f"Error writing batch to Milvus: {str(e)}")
                    continue

            self.doc_ids = doc_ids
        else:
            splitted = split_text(
                self.content,
                settings.SPLIT_SIZE,
                settings.SPLIT_MIN_LENGTH,
                settings.SPLIT_OVERLAP,
                separators=["\n\n", "\n", ".", "?", "!", " ", ""]
            )

            type = self.type
            link = self.url
            title = self.title

            # Embed the texts using the configured model
            try:
                embeddings = embed_texts_with_model(splitted, model)
            except Exception as e:
                logger.error(f"Error embedding texts: {traceback.format_exc()}")
                self.status = DataSource.Status.FAIL
                self.save()
                raise e

            if embeddings is None:
                logger.error(f"Embeddings is None. {traceback.format_exc()}")
                raise Exception("Embeddings is None")

            # Prepare the metadata
            docs = []
            split_num = 0
            for i, split in enumerate(splitted):
                split_num += 1
                docs.append(
                    {
                        "metadata": {
                            "type": type,
                            "link": link,
                            "split_num": split_num,
                            "title": title,
                        },
                        "text": split,
                        "vector": embeddings[i],
                    }
                )

            # Write to milvus with the correct collection name and dimension
            ids = insert_vectors(collection_name, docs, dimension=dimension)
            # Update the model
            if self.doc_ids is None:
                self.doc_ids = []
            self.doc_ids += ids

        self.in_milvus = True
        self.save()

    def delete_from_milvus(self, overridden_model=None):
        from core.milvus_utils import delete_vectors
        from core.utils import get_embedding_model_config

        if not self.in_milvus:
            return

        if overridden_model:
            model = overridden_model
        else:
            if self.type == DataSource.Type.GITHUB_REPO:
                model = self.guru_type.code_embedding_model
            else:
                model = self.guru_type.text_embedding_model

        ids = self.doc_ids
        if self.type == DataSource.Type.GITHUB_REPO:
            collection_name, dimension = get_embedding_model_config(model)
        else:
            collection_name = self.guru_type.milvus_collection_name
        delete_vectors(collection_name, ids)

        self.doc_ids = []
        self.in_milvus = False

        if self.type == DataSource.Type.GITHUB_REPO:
            GithubFile.objects.filter(data_source=self).update(in_milvus=False, doc_ids=[])

        self.save()

    def scrape_main_content(self):
        """
        Scrape the main content of the data source using Gemini to extract the main content from HTML.
        Updates Milvus immediately after processing.
        Skips if the content has already been rewritten or is not in a success status.
        """
        from core.requester import GeminiRequester
        gemini_requester = GeminiRequester(model_name=settings.LARGE_GEMINI_MODEL)

        try:
            # Skip if already rewritten or not in success status
            if self.content_rewritten or self.status != DataSource.Status.SUCCESS:
                logger.info(f"Skipping data source {self.id} - already rewritten or not in success status")
                return
                
            if not self.content:
                logger.warning(f"Data source {self.id} has no content to process")
                return
                
            # Store original content if not already stored
            if not self.original_content:
                self.original_content = self.content
            
            # Scrape main content using Gemini
            main_content = gemini_requester.scrape_main_content(self.content)
            
            # Update data source with new content
            self.content = main_content
            self.content_rewritten = True

            with transaction.atomic():
                # Save to database
                self.save()
                
                # Delete from Milvus
                self.delete_from_milvus()
                
                # Write to Milvus
                self.write_to_milvus()

            
        except Exception as e:
            logger.error(f"Error scraping main content for data source {self.id}: {str(e)}", exc_info=True)

    def create_initial_summarizations(self, max_length=settings.SUMMARIZATION_MAX_LENGTH, chunk_overlap=settings.SUMMARIZATION_OVERLAP_LENGTH):
        """
        Summarizes the content of the data source by using RecursiveCharacterTextSplitter and generating summaries.
        Continues from where it left off if there are existing summarizations.

        Args:
            max_length: The maximum length of the summarization chunks.
            chunk_overlap: The overlap length between the summarization chunks.
        """
        from core.requester import OpenAIRequester
        from core.utils import split_text, summarize_text

        if self.initial_summarizations_created:
            return

        content = self.content

        # Get the highest existing split_num
        last_split_num = Summarization.objects.filter(
            is_data_source_summarization=True,
            data_source_ref=self,
            initial=True
        ).order_by('-split_num').values_list('split_num', flat=True).first() or 0

        chunks = split_text(content, max_length, settings.SUMMARIZATION_MIN_LENGTH, chunk_overlap)

        content_metadata = [self.get_metadata()]

        # Summarize each chunk (if multiple) and combine them into a single summarization
        if len(chunks) > 1:
            for i, chunk in enumerate(chunks[last_split_num:], start=last_split_num + 1):
                chunk = f'\n<METADATA>{content_metadata}</METADATA>\n\n{chunk}'
                summarized, model_name, usages, summary_suitable, reasoning = summarize_text(chunk, self.guru_type)
                Summarization.objects.create(
                    is_data_source_summarization=True,
                    guru_type=self.guru_type,
                    content_metadata=content_metadata,
                    initial=True,
                    data_source_ref=self,
                    source_content=chunk,
                    result_content=summarized,
                    is_root=False,
                    processed=False,
                    split_num=i,
                    model=model_name,
                    usages=usages,
                    summary_suitable=summary_suitable,
                    reasoning=reasoning
                )
        elif last_split_num == 0 and len(chunks) == 1:  # Only create if it doesn't exist
            chunk = f'\n<METADATA>{content_metadata}</METADATA>\n\n{chunks[0]}'
            summarized, model_name, usages, summary_suitable, reasoning = summarize_text(chunk, self.guru_type)
            Summarization.objects.create(
                is_data_source_summarization=True,
                guru_type=self.guru_type,
                content_metadata=content_metadata,
                initial=True,
                data_source_ref=self,
                source_content=chunk,
                result_content=summarized,
                is_root=True,
                processed=False,
                split_num=1,
                model=model_name,
                usages=usages,
                summary_suitable=summary_suitable,
                reasoning=reasoning
            )
            self.final_summarization_created = True

        self.initial_summarizations_created = True
        self.save()

    def reindex(self):
        self.status = DataSource.Status.NOT_PROCESSED
        self.last_reindex_date = datetime.now()
        self.reindex_count += 1

        if self.type == DataSource.Type.GITHUB_REPO:
            self.content = ''

        self.save()
        self.delete_from_milvus()


class FeaturedDataSource(models.Model):
    guru_type = models.ForeignKey(GuruType, on_delete=models.CASCADE)
    type = models.CharField(max_length=50, choices=DataSource.Type.choices, default=DataSource.Type.PDF)
    title = models.TextField(null=False, blank=False)
    description = models.TextField(null=False, blank=False)
    icon_url = models.URLField(max_length=2000, null=False, blank=False)
    active = models.BooleanField(default=True)
    url = models.URLField(max_length=2000, null=True, blank=True)  # If website or youtube

    def __str__(self):
        return f"{self.title} - {self.type}"


class Favicon(models.Model):
    domain = models.CharField(max_length=255, unique=True)
    favicon_url = models.URLField(max_length=2000, null=True, blank=True)
    valid = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.domain} - {self.favicon_url} - {self.valid}"

    @property
    def url(self):
        if self.valid:
            return self.favicon_url
        else:
            return settings.FAVICON_PLACEHOLDER_URL


class DataSourceExists(Exception):
    pass


class LinkReference(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    url = models.TextField()
    # url format is (link_name)[url]
    validity = models.ForeignKey('LinkValidity', on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return self.link

    @property
    def link(self):
        import re

        # Match markdown link format: [text](url)
        markdown_match = re.match(r'\[([^\]]+)\]\(([^)]+)\)', self.url)
        if markdown_match:
            return markdown_match.group(2)

        # If not markdown format, return the full URL
        return self.url.strip()


class LinkValidity(models.Model):
    link = models.TextField()
    valid = models.BooleanField(default=False)
    response_code = models.IntegerField(default=0)

    def __str__(self):
        if self.id:
            return f"{self.link} - {self.valid}"
        return f"{self.link}"


class OutOfContextQuestion(models.Model):
    question = models.TextField()
    user_question = models.TextField()
    rerank_threshold = models.FloatField(default=0.0)
    trust_score_threshold = models.FloatField(default=0.0)
    guru_type = models.ForeignKey(GuruType, on_delete=models.CASCADE)
    date_created = models.DateTimeField(auto_now_add=True)
    source = models.CharField(
        max_length=50,
        choices=[(tag.value, tag.value) for tag in Question.Source],
        default=Question.Source.USER.value,
    )
    processed_ctx_relevances = models.JSONField(default=dict, blank=True, null=False)
    enhanced_question = models.TextField(default='', blank=True, null=True)

    def __str__(self):
        return self.question

    class Meta:
        indexes = [
            models.Index(fields=["guru_type", "date_created"]),
            models.Index(fields=["source"]),
        ]


class Settings(models.Model):
    class ScrapeType(models.TextChoices):
        CRAWL4AI = "CRAWL4AI", "Crawl4AI"
        FIRECRAWL = "FIRECRAWL", "Firecrawl"

    class DefaultEmbeddingModel(models.TextChoices):
        CLOUD = "IN_HOUSE", "In-house embedding model"
        SELFHOSTED = "OPENAI_TEXT_EMBEDDING_3_SMALL", "OpenAI - text-embedding-3-small"

    rerank_threshold = models.FloatField(default=0.01)
    rerank_threshold_llm_eval = models.FloatField(default=0.01)
    trust_score_threshold = models.FloatField(default=0.0)
    pricings = models.JSONField(default=dict)
    widget_answer_max_length = models.IntegerField(default=150)
    openai_api_key = models.CharField(max_length=500, null=True, blank=True)
    is_openai_key_valid = models.BooleanField(default=False)
    firecrawl_api_key = models.CharField(max_length=500, null=True, blank=True)
    is_firecrawl_key_valid = models.BooleanField(default=False)
    youtube_api_key = models.CharField(max_length=500, null=True, blank=True)
    is_youtube_key_valid = models.BooleanField(default=False)
    scrape_type = models.CharField(
        max_length=50,
        choices=ScrapeType.choices,
        default=ScrapeType.CRAWL4AI,
    )
    embedding_model_configs = models.JSONField(default=dict, blank=True, null=True)
    default_embedding_model = models.CharField(
        max_length=100,
        choices=DefaultEmbeddingModel.choices,
        default=None,
        null=True,
        blank=True
    )

    code_file_extensions = models.JSONField(default=list, blank=True, null=True)  # Used for github repos
    package_manifest_files = models.JSONField(default=list, blank=True, null=True)  # Used for github repos

    @classmethod
    def get_default_embedding_model(cls):
        """
        Returns the default embedding model based on the environment.
        For cloud environments, returns IN_HOUSE.
        For selfhosted environments, returns OPENAI_TEXT_EMBEDDING_3_SMALL.
        """
        try:
            settings_obj = cls.objects.first()
            if settings_obj:
                return settings_obj.default_embedding_model
        except Exception:
            pass
        
        # Fallback to environment-based default if no settings object exists
        return cls.DefaultEmbeddingModel.CLOUD if settings.ENV != 'selfhosted' else cls.DefaultEmbeddingModel.SELFHOSTED

    def save(self, *args, **kwargs):
        # Set default embedding model based on environment if not set
        if not self.default_embedding_model:
            self.default_embedding_model = self.DefaultEmbeddingModel.CLOUD if settings.ENV != 'selfhosted' else self.DefaultEmbeddingModel.SELFHOSTED

        # Check OpenAI API key validity before saving
        if self.openai_api_key:
            try:
                from openai import OpenAI
                client = OpenAI(api_key=self.openai_api_key, timeout=10)
                client.models.list()
                self.is_openai_key_valid = True
            except Exception:
                self.is_openai_key_valid = False
        else:
            self.is_openai_key_valid = False

        if self.firecrawl_api_key:
            try:
                if self.scrape_type == Settings.ScrapeType.FIRECRAWL:
                    import requests
                    url = "https://api.firecrawl.dev/v1/team/credit-usage"
                    headers = {"Authorization": f"Bearer {self.firecrawl_api_key}"}
                    response = requests.get(url, headers=headers, timeout=10)
                    self.is_firecrawl_key_valid = response.status_code == 200
            except Exception:
                self.is_firecrawl_key_valid = False
        else:
            self.is_firecrawl_key_valid = False

        if self.youtube_api_key:
            try:
                from core.requester import YouTubeRequester
                requester = YouTubeRequester(self.youtube_api_key)
                requester.get_most_popular_video()
                self.is_youtube_key_valid = True
            except Exception as e:
                logger.error(f'Error validating YouTube API key: {e}')
                self.is_youtube_key_valid = False

        super().save(*args, **kwargs)

    def __str__(self):
        return f"Settings ID: {self.id}"


class LLMEvalResult(models.Model):
    guru_type = models.ForeignKey(GuruType, on_delete=models.CASCADE)
    version = models.IntegerField()
    model = models.TextField()

    context_relevance_avg = models.FloatField()
    context_relevance_median = models.FloatField()
    context_relevance_std = models.FloatField()

    groundedness_avg = models.FloatField()
    groundedness_median = models.FloatField()
    groundedness_std = models.FloatField()

    answer_relevance_avg = models.FloatField()
    answer_relevance_median = models.FloatField()
    answer_relevance_std = models.FloatField()

    total_questions = models.IntegerField()
    total_cost = models.FloatField()

    # Non-zero metrics
    context_relevance_non_zero_avg = models.FloatField(null=True, blank=True)
    context_relevance_non_zero_median = models.FloatField(null=True, blank=True)
    context_relevance_non_zero_std = models.FloatField(null=True, blank=True)
    context_relevance_non_zero_count = models.IntegerField(null=True, blank=True)

    groundedness_non_zero_avg = models.FloatField(null=True, blank=True)
    groundedness_non_zero_median = models.FloatField(null=True, blank=True)
    groundedness_non_zero_std = models.FloatField(null=True, blank=True)
    groundedness_non_zero_count = models.IntegerField(null=True, blank=True)

    answer_relevance_non_zero_avg = models.FloatField(null=True, blank=True)
    answer_relevance_non_zero_median = models.FloatField(null=True, blank=True)
    answer_relevance_non_zero_std = models.FloatField(null=True, blank=True)
    answer_relevance_non_zero_count = models.IntegerField(null=True, blank=True)

    plot_url = models.URLField(max_length=2000, null=True, blank=True)

    notes = models.TextField(default='', blank=True, null=True)
    settings = models.JSONField(default=dict, blank=True, null=True)

    date_created = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['guru_type', 'version', 'model']

    def __str__(self):
        return f"{self.guru_type.slug} - v{self.version} - {self.model}"

    def save(self, *args, **kwargs):
        if not self.plot_url:
            self.plot_url = self.generate_scatter_plot()
        super().save(*args, **kwargs)

    def generate_scatter_plot(self):
        import io
        from matplotlib import pyplot as plt
        import numpy as np
        from core.gcp import PLOTS_GCP

        # Fetch all LLMEval objects
        guru_type = self.guru_type
        version = self.version
        model = self.model

        llm_evals = LLMEval.objects.filter(question__guru_type=guru_type, version=version, model=model)

        # Prepare x (context_relevance), y (average reranked score), and question IDs
        x = []
        y = []
        question_ids = []

        for eval in llm_evals:
            # Add context relevance
            x.append(eval.context_relevance)

            # Calculate average reranked score, use 0 if reranked_scores is empty or None
            if eval.reranked_scores:
                avg_reranked_score = sum(map(lambda x: x['score'], eval.reranked_scores)) / len(eval.reranked_scores)
            else:
                avg_reranked_score = 0

            y.append(avg_reranked_score)
            question_ids.append(eval.question.id)

        # Convert to numpy arrays for plotting
        x = np.array(x)
        y = np.array(y)

        # Create scatter plot
        plt.figure(figsize=(12, 9))
        scatter = plt.scatter(x, y, alpha=0.5)
        plt.xlabel('Context Relevance')
        plt.ylabel('Average Reranked Score')
        plt.title('Context Relevance vs Average Reranked Score')

        # Add question IDs as annotations
        for i, txt in enumerate(question_ids):
            plt.annotate(txt, (x[i], y[i]), xytext=(5, 5), textcoords='offset points', fontsize=8)

        # Save the plot to a bytes buffer
        buffer = io.BytesIO()
        plt.savefig(buffer, format='png', dpi=300)
        plt.close()

        # Set the buffer's current position to the beginning
        buffer.seek(0)

        # Upload the image to GCP
        target_path = f'{settings.ENV}/plots/{model}/{guru_type.slug}/scatter_plot-{version}.png'
        _, success = PLOTS_GCP.upload_file(buffer, target_path)

        success_url = f'{PLOTS_GCP.get_url_prefix()}/{target_path.lstrip("./")}'

        if success:
            return success_url
        else:
            logger.error(f'Error uploading scatter plot to GCP: {success_url}')
            return None


class Summarization(models.Model):
    is_data_source_summarization = models.BooleanField(default=True)
    data_source_ref = models.ForeignKey(
        'DataSource', on_delete=models.CASCADE, null=True, blank=True
    )
    guru_type = models.ForeignKey(GuruType, on_delete=models.CASCADE, null=True,
                                  blank=True)  # Used for merging data source summarizations
    summarization_refs = models.ManyToManyField('self', symmetrical=False, blank=True)
    content_metadata = models.JSONField(default=list, blank=True, null=True)
    initial = models.BooleanField(default=False)
    source_content = models.TextField(null=True, blank=True)
    split_num = models.IntegerField(default=1)  # Only used for initial summarizations
    result_content = models.TextField(null=True, blank=True)    # summary
    is_root = models.BooleanField(default=False)
    processed = models.BooleanField(default=False)
    summary_suitable = models.BooleanField(default=False)
    reasoning = models.TextField(default='', blank=True, null=True)
    date_created = models.DateTimeField(auto_now_add=True)
    date_updated = models.DateTimeField(auto_now=True)
    # Used a foreign key instead of an id as this is not a performance critical system and we would prefer to have a more readable model
    question_generation_ref = models.ForeignKey(
        'SummaryQuestionGeneration', on_delete=models.SET_NULL, null=True, blank=True)
    model = models.TextField(default='gpt-4o-2024-08-06')
    usages = models.JSONField(default=dict, blank=True, null=True)

    def __str__(self):
        return f'{self.id}'


class SummaryQuestionGeneration(models.Model):
    summarization_ref = models.ForeignKey(Summarization, on_delete=models.SET_NULL, null=True, blank=True)
    guru_type = models.ForeignKey(GuruType, on_delete=models.CASCADE, null=True, blank=True)
    question = models.ForeignKey(Question, on_delete=models.SET_NULL, null=True, blank=True)
    summary_sufficient = models.BooleanField(default=False)
    questions = models.JSONField(default=list)
    date_created = models.DateTimeField(auto_now_add=True)
    processed = models.BooleanField(default=False)
    model = models.TextField(default='gpt-4o-2024-08-06')
    usages = models.JSONField(default=dict, blank=True, null=True)

    def __str__(self):
        return f'{self.id}'


class Binge(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    guru_type = models.ForeignKey(GuruType, on_delete=models.CASCADE)
    root_question = models.ForeignKey(Question, on_delete=models.CASCADE,
                                      related_name='binge_root_question', null=True, blank=True)
    owner = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    date_created = models.DateTimeField(auto_now_add=True)
    last_used = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.id} - {self.guru_type.slug}"


class Thread(models.Model):
    thread_id = models.CharField(max_length=100)  # Discord thread ID
    binge = models.ForeignKey(Binge, on_delete=models.CASCADE)
    integration = models.ForeignKey('Integration', on_delete=models.CASCADE)
    date_created = models.DateTimeField(auto_now_add=True)
    date_updated = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['thread_id', 'integration']

    def __str__(self):
        return f"{self.thread_id} - {self.integration.guru_type.slug}"


class WidgetId(models.Model):
    guru_type = models.ForeignKey(GuruType, on_delete=models.CASCADE, related_name='widget_ids')
    key = models.CharField(max_length=100, unique=True)
    domain_url = models.URLField(max_length=2000)
    domain = models.URLField(max_length=2000)  # New field to store the base domain
    is_wildcard = models.BooleanField(default=False)  # Flag to indicate if this is a wildcard pattern
    date_created = models.DateTimeField(auto_now_add=True)
    date_updated = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Widget ID'
        verbose_name_plural = 'Widget IDs'
        unique_together = ['guru_type', 'domain_url']

    def __str__(self):
        return f"{self.guru_type.slug} - {self.domain_url}"

    def clean(self):
        if self.domain_url:
            # Remove trailing slashes and normalize domain
            self.domain_url = self.domain_url.rstrip('/')
            
            # Check if this is a wildcard pattern
            self.is_wildcard = '*' in self.domain_url
            
            # For non-wildcard URLs, extract and store the domain
            if not self.is_wildcard:
                parsed_url = urlparse(self.domain_url)
                self.domain = f"{parsed_url.scheme}://{parsed_url.netloc}"
            else:
                # For wildcard patterns, store the pattern as is
                self.domain = self.domain_url

        # Ensure domain is unique per guru type if specified
        if self.domain_url and WidgetId.objects.filter(
            guru_type=self.guru_type,
            domain_url=self.domain_url,
        ).exclude(id=self.id).exists():
            raise ValidationError('This domain is already registered for this guru type')

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    @classmethod
    def validate_key(cls, widget_id):
        """
        Validates if a widget ID exists
        Returns the WidgetId object if valid, None otherwise.
        """
        try:
            return cls.objects.get(key=widget_id)
        except cls.DoesNotExist:
            return None
            
    @classmethod
    def domain_matches_pattern(cls, domain, pattern):
        """
        Check if a domain matches a wildcard pattern.
        
        Supports patterns like:
        * - Match any domain
        http://localhost:* - Match localhost with any port
        https://*.example.com - Match any subdomain of example.com
        *example.com - Match any domain ending with example.com
        example* - Match any domain starting with example
        *example* - Match any domain containing example
        
        Matching is case insensitive.
        """
        import re
        
        # Convert both domain and pattern to lowercase for case-insensitive matching
        if domain:
            domain = domain.lower()
        if pattern:
            pattern = pattern.lower()
        else:
            return False
            
        # Exact match
        if domain == pattern:
            return True
            
        # Universal wildcard
        if pattern == '*':
            return True
            
        # Convert wildcard pattern to regex pattern
        # Replace * with appropriate regex
        regex_pattern = pattern.replace('.', r'\.').replace('*', '.*')
        
        # Add start/end anchors if not already wildcarded
        if not pattern.startswith('*'):
            regex_pattern = '^' + regex_pattern
        if not pattern.endswith('*'):
            regex_pattern = regex_pattern + '$'
            
        # Try to match using regex
        try:
            return bool(re.match(regex_pattern, domain))
        except re.error:
            # If regex fails, fall back to simpler checks
            
            # Port wildcard (e.g., http://localhost:*)
            if pattern.endswith(':*'):
                base_pattern = pattern[:-2]  # Remove :* from the end
                return domain.startswith(base_pattern)
                
            # Subdomain wildcard (e.g., https://*.example.com)
            if '*.' in pattern:
                prefix, suffix = pattern.split('*.', 1)
                return domain.endswith(suffix) and domain.startswith(prefix)
                
            # Contains wildcard
            if '*' in pattern:
                parts = pattern.split('*')
                return all(part in domain for part in parts if part)
                
            return False


class GithubFile(models.Model):
    data_source = models.ForeignKey(
        DataSource,
        on_delete=models.CASCADE,
        related_name='github_files')

    path = models.CharField(max_length=2000)
    link = models.URLField(max_length=2000)
    content = models.TextField()
    size = models.PositiveIntegerField()
    in_milvus = models.BooleanField(default=False)
    doc_ids = models.JSONField(default=list, blank=True, null=True)
    date_created = models.DateTimeField(auto_now_add=True)
    date_updated = models.DateTimeField(auto_now=True)

    @property
    def repository_link(self):
        return self.data_source.url
    
    @property
    def repo_title(self):
        return self.data_source.title
    
    @property
    def title(self):
        return self.path.split('/')[-1]

    class Meta:
        unique_together = ['data_source', 'path']
        indexes = [
            models.Index(fields=['path']),
        ]

    def save(self, *args, **kwargs):
        self.link = f'{self.repository_link}/tree/{self.data_source.default_branch}/{self.path}'
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.path}"

    def write_to_milvus(self):
        from core.utils import embed_texts_with_model, split_text, split_code, map_extension_to_language, get_embedding_model_config
        from core.milvus_utils import insert_vectors

        if self.in_milvus:
            return

        # Split the content into chunks
        extension = self.path.split('/')[-1].split('.')[-1]
        language = map_extension_to_language(extension)
        if language:
            splitted = split_code(
                self.content,
                settings.SPLIT_SIZE,
                settings.SPLIT_MIN_LENGTH,
                settings.SPLIT_OVERLAP,
                language
            )
        else:
            splitted = split_text(
                self.content,
                settings.SPLIT_SIZE,
                settings.SPLIT_MIN_LENGTH,
                settings.SPLIT_OVERLAP,
                separators=["\n\n", "\n", ".", "?", "!", " ", ""]
            )

        # Prepare metadata
        if not self.link:
            self.link = f'{self.repository_link}/tree/{self.data_source.default_branch}/{self.path}'

        metadata = {
            "type": self.data_source.type,
            "repo_link": self.repository_link,
            "link": self.link,
            "repo_title": self.repo_title,
            "title": self.title,
            "file_path": self.path
        }

        # Get embedding model configuration
        collection_name, dimension = get_embedding_model_config(self.data_source.guru_type.code_embedding_model)

        # Embed the texts using the configured model
        try:
            embeddings = embed_texts_with_model(splitted, self.data_source.guru_type.code_embedding_model)
        except Exception as e:
            logger.error(f"Error embedding texts: {traceback.format_exc()}")
            raise e

        if embeddings is None:
            raise Exception("Embeddings is None")

        # Prepare documents for Milvus
        docs = []
        split_num = 0
        guru_slug = self.data_source.guru_type.slug
        for i, split in enumerate(splitted):
            split_num += 1
            docs.append({
                "metadata": {**metadata, "split_num": split_num},
                "text": split,
                "vector": embeddings[i],
                "guru_slug": guru_slug,
            })

        # Write to Milvus with the correct collection name and dimension
        ids = list(insert_vectors(collection_name, docs, code=True, dimension=dimension))
        
        # Update the model
        self.doc_ids = ids
        self.in_milvus = True
        self.save()

        logger.info(f"Wrote GitHub file {self.path} to Milvus")
        return ids

    def delete_from_milvus(self):
        from core.milvus_utils import delete_vectors
        from core.utils import get_embedding_model_config
        code_collection_name, code_dimension = get_embedding_model_config(self.data_source.guru_type.code_embedding_model)
        delete_vectors(code_collection_name, self.doc_ids)

        data_source = self.data_source

        # Check for invalid doc_ids
        invalid_doc_ids = [doc_id for doc_id in self.doc_ids if doc_id not in data_source.doc_ids]
        valid_doc_ids = [doc_id for doc_id in self.doc_ids if doc_id in data_source.doc_ids]

        if invalid_doc_ids:
            logger.error(f"Found doc_ids of github file {self.path} that don't exist in data_source: {invalid_doc_ids}. guru_type: {self.data_source.guru_type.slug}. Github link: {self.link}")

        if valid_doc_ids:
            for doc_id in valid_doc_ids:
                data_source.doc_ids.remove(doc_id)
            data_source.save()

        self.in_milvus = False
        self.doc_ids = []
        self.save()



class APIKey(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    key = models.CharField(max_length=100, unique=True)
    integration = models.BooleanField(default=False)
    name = models.CharField(max_length=100, null=True, blank=True)
    date_created = models.DateTimeField(auto_now_add=True)
    date_updated = models.DateTimeField(auto_now=True)

    @classmethod
    def validate_key(cls, api_key):
        try:
            return cls.objects.get(key=api_key)
        except cls.DoesNotExist:
            return None


class Integration(models.Model):
    class Type(models.TextChoices):
        DISCORD = "DISCORD"
        SLACK = "SLACK"
        GITHUB = "GITHUB"

    type = models.CharField(
        max_length=50,
        choices=[(tag.value, tag.value) for tag in Type],
        default=Type.DISCORD.value,
    )

    workspace_name = models.TextField(null=True, blank=True)
    external_id = models.TextField()
    guru_type = models.ForeignKey(GuruType, on_delete=models.CASCADE)
    code = models.TextField(null=True, blank=True)
    api_key = models.OneToOneField(APIKey, on_delete=models.SET_NULL, null=True, blank=True, related_name='integration_owner')
    access_token = models.TextField()
    refresh_token = models.TextField(null=True, blank=True)
    channels = models.JSONField(default=list, blank=True, null=False)
    github_private_key = models.TextField(null=True, blank=True)
    github_client_id = models.TextField(null=True, blank=True)
    github_secret = models.TextField(null=True, blank=True)
    github_bot_name = models.TextField(null=True, blank=True)
    github_html_url = models.TextField(null=True, blank=True)
    date_created = models.DateTimeField(auto_now_add=True)
    date_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.type} - {self.guru_type.name}"

    @property
    def masked_access_token(self):
        if settings.ENV == 'selfhosted':
            if self.access_token:
                return self.access_token[:10] + ('*' * len(self.access_token[10:]))
            else:
                return None
        return None

    @property
    def masked_github_client_id(self):
        if settings.ENV == 'selfhosted':
            if self.github_client_id:
                return self.github_client_id[:3] + ('*' * len(self.github_client_id[3:-3])) + self.github_client_id[-3:]
            else:
                return None
        return None

    @property
    def masked_github_secret(self):
        if settings.ENV == 'selfhosted':
            if self.github_secret:
                return self.github_secret[:3] + ('*' * len(self.github_secret[3:-3])) + self.github_secret[-3:]
            else:
                return None
        return None

    class Meta:
        unique_together = ['type', 'guru_type']


class CrawlState(models.Model):
    class Status(models.TextChoices):
        RUNNING = "RUNNING", "Running"
        COMPLETED = "COMPLETED", "Completed"
        STOPPED = "STOPPED", "Stopped"
        FAILED = "FAILED", "Failed"

    class Source(models.TextChoices):
        UI = "UI", "User Interface"
        API = "API", "API"

    url = models.URLField(max_length=2000)
    status = models.CharField(
        max_length=50,
        choices=Status.choices,
        default=Status.RUNNING,
    )
    source = models.CharField(
        max_length=30,
        choices=Source.choices,
        default=Source.API,
    )
    discovered_urls = models.JSONField(default=list)
    error_message = models.TextField(blank=True, null=True)
    start_time = models.DateTimeField(auto_now_add=True)
    end_time = models.DateTimeField(null=True, blank=True)
    last_polled_at = models.DateTimeField(auto_now_add=True)
    link_limit = models.IntegerField(default=1500)
    guru_type = models.ForeignKey(GuruType, on_delete=models.CASCADE, null=True, blank=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True) # null on selfhosted

    def __str__(self):
        return f"Crawl {self.id} - {self.url} ({self.status}) - {self.guru_type.name} - {self.user.email if self.user else 'selfhosted'}"


class GuruCreationForm(models.Model):

    name = models.CharField(max_length=100)
    email = models.EmailField()
    github_repo = models.URLField(max_length=2000)
    docs_url = models.URLField(max_length=2000)
    use_case = models.TextField(blank=True, null=True)
    notified = models.BooleanField(default=False)
    source = models.CharField(max_length=50)
    date_created = models.DateTimeField(auto_now_add=True)
    date_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.email})"

    class Meta:
        ordering = ['-date_created']

