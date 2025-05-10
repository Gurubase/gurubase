import logging
from django.conf import settings
from django.db import models
from django.core.exceptions import ValidationError
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

from core.models import APIKey, Binge, GuruType

# Create your models here.

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

class Integration(models.Model):
    class Type(models.TextChoices):
        DISCORD = "DISCORD"
        SLACK = "SLACK"
        GITHUB = "GITHUB"
        JIRA = "JIRA"
        ZENDESK = "ZENDESK"
        CONFLUENCE = "CONFLUENCE"

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

    jira_api_key = models.TextField(null=True, blank=True)
    jira_user_email = models.TextField(null=True, blank=True)
    jira_domain = models.TextField(null=True, blank=True)

    confluence_api_token = models.TextField(null=True, blank=True)
    confluence_user_email = models.TextField(null=True, blank=True)
    confluence_domain = models.TextField(null=True, blank=True)

    zendesk_domain = models.TextField(null=True, blank=True)
    zendesk_api_token = models.TextField(null=True, blank=True)
    zendesk_user_email = models.TextField(null=True, blank=True)

    allow_dm = models.BooleanField(default=False)

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

    @property
    def masked_jira_api_key(self):
        if self.jira_api_key:
            return self.jira_api_key[:3] + ('*' * len(self.jira_api_key[3:-3])) + self.jira_api_key[-3:]
        else:
            return None
        
    @property
    def masked_zendesk_api_token(self):
        if self.zendesk_api_token:
            return self.zendesk_api_token[:3] + ('*' * len(self.zendesk_api_token[3:-3])) + self.zendesk_api_token[-3:]
        else:
            return None

    @property
    def masked_confluence_api_token(self):
        if self.confluence_api_token:
            return self.confluence_api_token[:3] + ('*' * len(self.confluence_api_token[3:-3])) + self.confluence_api_token[-3:]
        else:
            return None

    class Meta:
        unique_together = ['type', 'guru_type']
