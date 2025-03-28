"""
Django settings for backend project.

Generated by 'django-admin startproject' using Django 4.1.13.

For more information on this file, see
https://docs.djangoproject.com/en/4.1/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/4.1/ref/settings/
"""

from pathlib import Path
from decouple import config, Csv
import os
import sys
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

ENV = config('ENV', default='selfhosted')
logger.info(f'ENV: {ENV}')

ROOT_EMAIL = config('ROOT_EMAIL', default='root@gurubase.io')
ROOT_PASSWORD = config('ROOT_PASSWORD', default='ChangeMe')

SENTRY_ENABLED = config('SENTRY_ENABLED', default=False, cast=bool)

if SENTRY_ENABLED or ENV == "selfhosted":
    import sentry_sdk
    from sentry_sdk.integrations.celery import CeleryIntegration
    from sentry_sdk.integrations.django import DjangoIntegration    
    # Use the configured DSN or fallback to selfhosted DSN - https://sentry.zendesk.com/hc/en-us/articles/26741783759899-My-DSN-key-is-publicly-visible-is-this-a-security-vulnerability
    SENTRY_DSN = config('SENTRY_DSN', default="https://004f52d6be335c0087a2c582f238ede2@o1185050.ingest.us.sentry.io/4508715634982912")
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[DjangoIntegration(), CeleryIntegration(monitor_beat_tasks=False)],
        traces_sample_rate=0.05,
        send_default_pii=True,
        environment=ENV,
    )

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/4.1/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = config(
    'SECRET_KEY', default='tmp-Wu7Msa5mDVgFCkFQAbnSPsBTA8bzyZ-Wu7Msa5mDVgFCkFQAbnSPsBTA8bzyZ')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = config('DEBUG', default=False, cast=bool)

AUTH_USER_MODEL = "accounts.User"

# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',
    'django_filters',
    'django_extensions',
    'core.apps.CoreConfig',
    'accounts.apps.AccountsConfig',
    'django.contrib.sitemaps',
    'rest_framework',
    'corsheaders',
    'django_celery_beat',
    'django_celery_results',
]

SITE_ID = 1

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'corsheaders.middleware.CorsMiddleware',
]

ROOT_URLCONF = 'backend.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'backend.context_processors.environment_processor',
            ],
        },
    },
]

WSGI_APPLICATION = 'backend.wsgi.application'


# Database
# https://docs.djangoproject.com/en/4.1/ref/settings/#databases

if 'test' in sys.argv:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
            'OPTIONS': {
                'timeout': 20,
            },
        }
    }
else:
    db_name = config('POSTGRES_DB_NAME', default="gurubase")
    host = config('POSTGRES_HOST', default="gurubase-postgres")
    port = config('POSTGRES_PORT', default=5432, cast=int)
    db_password = config('POSTGRES_PASSWORD', default="ChangeMe")
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': db_name,
            'USER': config('POSTGRES_USER', default='postgres'),
            'PASSWORD': db_password,
            'HOST': host,
            'PORT': port,
            # 'OPTIONS': {
            #     'isolation_level': psycopg2.extensions.ISOLATION_LEVEL_READ_UNCOMMITTED,
            # },
        }
    }


# Password validation
# https://docs.djangoproject.com/en/4.1/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/4.1/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/4.1/howto/static-files/

STATIC_URL = 'backend/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'backend/static')
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'static'),
]

MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
MEDIA_URL = '/media/'

# Default primary key field type
# https://docs.djangoproject.com/en/4.1/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

REST_FRAMEWORK = {
    'DEFAULT_FILTER_BACKENDS': ['django_filters.rest_framework.DjangoFilterBackend'],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 100000,
    'DEFAULT_RENDERER_CLASSES': (
        'rest_framework.renderers.JSONRenderer',
    ),
    'EXCEPTION_HANDLER': 'core.utils.custom_exception_handler_throttled',
}

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '[%(asctime)s] [%(levelname)s] %(message)s',
            'datefmt': '%Y-%m-%d %H:%M:%S'
        },
    },
    'handlers': {
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose', 
            'filters': ['hide_info_specific_task'],
        },
    },
    'loggers': {
        '': {  # Default logger
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': True,
        },
        'celery': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'celery.beat': {  
            'handlers': ['console'],
            'level': 'INFO',
        },
    },
    'filters': {
        'hide_info_specific_task': {
            '()': 'django.utils.log.CallbackFilter',
            'callback': lambda record: not (
                ('task_stop_inactive_ui_crawls' in record.getMessage() or 'core.tasks.stop_inactive_ui_crawls' in record.getMessage()) and 
                record.levelno == logging.INFO and
                not (datetime.fromtimestamp(record.created).minute == 0 and 
                     datetime.fromtimestamp(record.created).second <= 3)
            )
        }
    }
}


BASE_URL = config('BASE_URL', default='http://localhost:8029')
BACKEND_URL = config('BACKEND_URL', default='http://localhost:8028')
OPENAI_API_KEY = config('OPENAI_API_KEY', default='')
OPENAI_TEXT_EMBEDDING_MODEL = config('OPENAI_TEXT_EMBEDDING_MODEL', default='text-embedding-3-small')

MILVUS_HOST = config('MILVUS_HOST', default='gurubase-milvus-standalone')
MILVUS_PORT = config('MILVUS_PORT', default='19530', cast=int)
AUTH_TOKEN = config('AUTH_TOKEN', default='0wu9L7xAWcKXgxwx0iBA7BchJ0r4W7') # hardcoded for selfhosted
SITEMAP_LIMIT = config('SITEMAP_LIMIT', default=5000, cast=int)
ALLOWED_HOSTS = config('ALLOWED_HOSTS', cast=Csv(), default='*')

# security
CORS_ORIGIN_ALLOW_ALL = True

if ENV == "production":
    CORS_ORIGIN_ALLOW_ALL = False
    CORS_ALLOWED_ORIGIN_REGEXES = [
        # r"^(http://localhost:30[0-9]{2})$",
        r"^https://(.+).getanteon.com$",
        r"^https://(.+).gurubase.io$",
        r"^https://(.+).gurubase.ai$",
        r"^https://(.+)getanteon.vercel.app$",
        r"^https://gurubase.io$",
        r"^https://gurubase.ai$",
        r"^https://kubernetesguru.getanteon.com$",
        r"^https://kubernetesguru-backend-api.getanteon.com$",
    ]
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
else:
    CORS_ORIGIN_ALLOW_ALL = True
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    CORS_ORIGIN_WHITELIST = [
        'http://localhost:3000',
        'https://localhost:3000',
    ]

USE_X_FORWARDED_HOST = True
USE_X_FORWARDED_PORT = True

TYPESENSE_API_KEY = config('TYPESENSE_API_KEY', default='xxx')
TYPESENSE_HOST = config('TYPESENSE_HOST', default='typesense-svc')
TYPESENSE_PORT = config('TYPESENSE_PORT', default=8108, cast=int)
TYPESENSE_PROTOCOL = config('TYPESENSE_PROTOCOL', default='http')

CELERY_BROKER_HOST = config('CELERY_BROKER_HOST', default='gurubase-rabbitmq')
CELERY_BROKER_PORT = config('CELERY_BROKER_PORT', default=5672, cast=int)
CELERY_BROKER_URL = f"amqp://{CELERY_BROKER_HOST}:{CELERY_BROKER_PORT}"
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_DEFAULT_QUEUE='kubernetesgurubackend-queue'
CELERY_ENABLE_UTC = True
CELERY_TASK_DEFAULT_QUEUE='kubernetesgurubackend-queue'
CELERY_RESULT_BACKEND = 'django-db' # django_celery_results
CELERY_RESULT_EXTENDED=True

RAW_QUESTIONS_TO_QUESTION_LIMIT_PER_TASK = config('RAW_QUESTIONS_TO_QUESTION_LIMIT_PER_TASK', default=4, cast=int)
SIMILARITY_FETCH_BATCH_SIZE = config('SIMILARITY_FETCH_BATCH_SIZE', default=100, cast=int)
SIMILARITY_SAVE_BATCH_SIZE = config('SIMILARITY_SAVE_BATCH_SIZE', default=50, cast=int)
FILL_OG_IMAGES_FETCH_BATCH_SIZE = config('FILL_OG_IMAGES_FETCH_BATCH_SIZE', default=100, cast=int)
STACKEXCHANGE_KEY = config('STACKEXCHANGE_KEY', default='xxx')
STREAM_ENABLED = config('STREAM_ENABLED', default=True, cast=bool)
CLAUDE_API_KEY = config('CLAUDE_API_KEY', default='xxx')
GEMINI_API_KEY = config('GEMINI_API_KEY', default='xxx')

REDIS_HOST = config('REDIS_HOST', default='gurubase-redis')
REDIS_PORT = config('REDIS_PORT', default=6379, cast=int)

GPT_MODEL = config('GPT_MODEL', default='gpt-4o-2024-08-06')
GPT_MODEL_MINI = config('GPT_MODEL_MINI', default='gpt-4o-mini-2024-07-18')


CACHES = {
    'alternate': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': f'redis://{REDIS_HOST}:{REDIS_PORT}',
    },
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'unique-snowflake',
    },
}

EMBED_API_URL = config('EMBED_API_URL', default='http://gurubase-text-embeddings:8056/embed')
EMBED_API_KEY = config('EMBED_API_KEY', default='')

RERANK_API_URL = config('RERANK_API_URL', default='http://gurubase-reranker:8057/rerank')
RERANK_API_KEY = config('RERANK_API_KEY', default='')
MILVUS_QUESTIONS_COLLECTION_NAME = config('MILVUS_QUESTIONS_COLLECTION_NAME', default='questions')
VECTOR_DISTANCE_THRESHOLD = config('VECTOR_DISTANCE_THRESHOLD', default=0.3, cast=float)
RAW_QUESTIONS_TO_QUESTIONS_LOCK = config('RAW_QUESTIONS_TO_QUESTIONS_LOCK', default='raw_questions_to_questions_lock')
RAW_QUESTIONS_TO_QUESTIONS_LOCK_DURATION_SECONDS = config('RAW_QUESTIONS_TO_QUESTIONS_LOCK_DURATION_SECONDS', default=600, cast=int)
SOURCE_GURU_BACKEND_URL = config('SOURCE_GURU_URL', default='https://kubernetesguru-backend-staging-api.getanteon.com')
SOURCE_GURU_TOKEN = config('SOURCE_GURU_TOKEN', default='xxx')
RAW_QUESTIONS_COPY_LOCK = config('RAW_QUESTIONS_COPY_LOCK', default='raw_questions_copy_lock')
RAW_QUESTIONS_COPY_LOCK_DURATION_SECONDS = config('RAW_QUESTIONS_COPY_LOCK_DURATION_SECONDS', default=1800, cast=int)
RAW_QUESTIONS_COPY_LAST_PAGE_NUM_KEY = config('RAW_QUESTIONS_COPY_LAST_PAGE_NUM_KEY', default='raw_questions_copy_last_page_num')
BOT_AUTH_TOKEN = config('BOT_AUTH_TOKEN', default='xxx')
TITLE_PROCESS_LOCK = config('TITLE_PROCESS_LOCK', default='title_process_lock')
TITLE_PROCESS_LOCK_DURATION_SECONDS = config('TITLE_PROCESS_LOCK_DURATION_SECONDS', default=1800, cast=int)
LLM_EVAL_ENABLED = config('LLM_EVAL_ENABLED', default=False, cast=bool)
SPLIT_SIZE = config('SPLIT_SIZE', default=2000, cast=int)
SPLIT_OVERLAP = config('SPLIT_OVERLAP', default=300, cast=int)
SPLIT_MIN_LENGTH = config('SPLIT_MIN_LENGTH', default=500, cast=int)

OG_IMAGE_GENERATE = config('OG_IMAGE_GENERATE', default=False, cast=bool)

STORAGE_TYPE = config('STORAGE_TYPE', default='local') # gcloud or local
if STORAGE_TYPE == 'gcloud':
    from google.oauth2 import service_account
    DEFAULT_FILE_STORAGE = 'storages.backends.gcloud.GoogleCloudStorage'
    GS_CREDENTIALS = service_account.Credentials.from_service_account_file(
        # This file is mounted from kubernetes secret
        os.path.join(BASE_DIR, 'gcp' ,'credentials.json')
    )
else:
    DEFAULT_FILE_STORAGE = 'django.core.files.storage.FileSystemStorage'

GS_BUCKET_NAME = 'gurubase-og-images'
GS_DATA_SOURCES_BUCKET_NAME = 'gurubase-customguru-files'
PDF_ICON_URL = 'https://s3.eu-central-1.amazonaws.com/anteon-strapi-cms-wuby8hpna3bdecoduzfibtrucp5x/pdf_icon_9268153e39.svg'
YOUTUBE_ICON_URL = 'https://s3.eu-central-1.amazonaws.com/anteon-strapi-cms-wuby8hpna3bdecoduzfibtrucp5x/youtube_dfa3f7b5b9.svg'
STACKOVERFLOW_ICON_URL = 'https://cdn.jsdelivr.net/gh/devicons/devicon/icons/stackoverflow/stackoverflow-original.svg'
WEBSITE_ICON_URL = 'https://cdn.jsdelivr.net/gh/devicons/devicon/icons/chrome/chrome-original.svg'
FIRECRAWL_API_KEY = config('FIRECRAWL_API_KEY', default='xxx')
LOG_STREAM_TIMES = config('LOG_STREAM_TIMES', default=False, cast=bool)
DATA_SOURCE_RETRIEVAL_LOCK_DURATION_SECONDS = config('DATA_SOURCE_RETRIEVAL_LOCK_DURATION_SECONDS', default=600, cast=int)
DATA_SOURCE_FETCH_BATCH_SIZE = config('DATA_SOURCE_FETCH_BATCH_SIZE', default=100, cast=int)
TASK_FETCH_LIMIT = config('TASK_FETCH_LIMIT', default=1000, cast=int)
SLACK_NOTIFIER_WEBHOOK_URL = config('SLACK_NOTIFIER_WEBHOOK_URL', default='xxx')
SLACK_NOTIFIER_ENABLED = config('SLACK_NOTIFIER_ENABLED', default=False, cast=bool)
JWT_EXPIRATION_SECONDS = config('JWT_EXPIRATION_SECONDS', default=60, cast=int)
FAVICON_PLACEHOLDER_URL = config('FAVICON_PLACEHOLDER_URL', default='https://s3.eu-central-1.amazonaws.com/anteon-strapi-cms-wuby8hpna3bdecoduzfibtrucp5x/favicon_default_4e64b8c2ec.svg')
SUMMARIZATION_MAX_LENGTH = config('SUMMARIZATION_MAX_LENGTH', default=400000, cast=int) # According to https://platform.openai.com/docs/models/gpt-4o, I couldn't find anything relating the prompt token limit. But the output token limit is 128000, which is sufficiently enough for 10000 chars.
SUMMARIZATION_OVERLAP_LENGTH = config('SUMMARIZATION_OVERLAP_LENGTH', default=500, cast=int)
SUMMARIZATION_MIN_LENGTH = config('SUMMARIZATION_MIN_LENGTH', default=1000, cast=int)
QUESTION_GENERATION_COUNT = config('QUESTION_GENERATION_COUNT', default=1, cast=int)
GS_PLOTS_BUCKET_NAME = config('GS_PLOTS_BUCKET_NAME', default='gurubase-customguru-files')

AUTH0_MANAGEMENT_API_TOKEN = config('AUTH0_MANAGEMENT_API_TOKEN', default='')
AUTH0_DOMAIN = config('AUTH0_DOMAIN', default='')
AUTH0_AUDIENCE = config('AUTH0_AUDIENCE', default='xxx')
AUTH0_CLIENT_ID = config('AUTH0_CLIENT_ID', default='')
AUTH0_CLIENT_SECRET = config('AUTH0_CLIENT_SECRET', default='')
AUTH0_MANAGEMENT_API_DOMAIN = config('AUTH0_MANAGEMENT_API_DOMAIN', default='')

SUMMARY_GENERATION_MODEL = config('SUMMARY_GENERATION_MODEL', default='gemini-1.5-flash-002') # gpt-4o-2024-08-06 or gemini-1.5-flash-002
SUMMARY_QUESTION_GENERATION_MODEL = config('SUMMARY_QUESTION_GENERATION_MODEL', default='gemini-1.5-flash-002') # gpt-4o-mini-2024-07-18 or gemini-1.5-flash-002

GENERATED_QUESTION_PER_GURU_LIMIT = config('GENERATED_QUESTION_PER_GURU_LIMIT', default=100, cast=int)
GITHUB_TOKEN = config('GITHUB_TOKEN', default='')
DEFAULT_DOMAIN_KNOWLEDGE = config('DEFAULT_DOMAIN_KNOWLEDGE', default='programming, software development')

SITEMAP_ADD_CONTEXT_RELEVANCE_THRESHOLD = config('SITEMAP_ADD_CONTEXT_RELEVANCE_THRESHOLD', default=0.5, cast=float)

FOLLOW_UP_QUESTION_LIMIT = config('FOLLOW_UP_QUESTION_LIMIT', default=100, cast=int)
FOLLOW_UP_QUESTION_TIME_LIMIT_SECONDS = config('FOLLOW_UP_QUESTION_TIME_LIMIT_SECONDS', default=7200, cast=int) # 2 hours
GENERATE_FOLLOW_UP_EXAMPLES = config('GENERATE_FOLLOW_UP_EXAMPLES', default=True, cast=bool)
FOLLOW_UP_EXAMPLE_COUNT = config('FOLLOW_UP_EXAMPLE_COUNT', default=3, cast=int)

BINGE_HISTORY_PAGE_SIZE = config('BINGE_HISTORY_PAGE_SIZE', default=30, cast=int)

GITHUB_REPO_CODE_COLLECTION_NAME = config('GITHUB_REPO_CODE_COLLECTION_NAME', default='github_repo_code')

CLOUDFLARE_BASE_URL = config('CLOUDFLARE_BASE_URL', default='https://api.cloudflare.com/client/v4')
CLOUDFLARE_ZONE_ID = config('CLOUDFLARE_ZONE_ID', default='xxx')
CLOUDFLARE_AUTH_TOKEN = config('CLOUDFLARE_AUTH_TOKEN', default='xxx')

LARGE_GEMINI_MODEL = config('LARGE_GEMINI_MODEL', default='gemini-1.5-pro')

if ENV == "selfhosted":
    NGINX_BASE_URL = config('NGINX_BASE_URL', default='http://gurubase-nginx:8029')

DISCORD_CLIENT_ID = config('DISCORD_CLIENT_ID', default='')
DISCORD_CLIENT_SECRET = config('DISCORD_CLIENT_SECRET', default='')
DISCORD_REDIRECT_URI = config('DISCORD_REDIRECT_URI', default='')
DISCORD_BOT_TOKEN = config('DISCORD_BOT_TOKEN', default='')

SLACK_CLIENT_ID = config('SLACK_CLIENT_ID', default='')
SLACK_CLIENT_SECRET = config('SLACK_CLIENT_SECRET', default='')

WEBSITE_EXTRACTION = config('WEBSITE_EXTRACTION', default='crawl4ai')

API_CONCURRENCY_THROTTLE_RATE = config('API_CONCURRENCY_THROTTLE_RATE', default='10/m')
WEBSHARE_TOKEN = config('WEBSHARE_TOKEN', default='')
GITHUB_FILE_BATCH_SIZE = config('GITHUB_FILE_BATCH_SIZE', default=100, cast=int)
CRAWL_INACTIVE_THRESHOLD_SECONDS = config('CRAWL_INACTIVE_THRESHOLD_SECONDS', default=7, cast=int)
ADMIN_EMAIL = config('ADMIN_EMAIL', default='')
MAILGUN_API_KEY = config('MAILGUN_API_KEY', default='')
FIRECRAWL_BATCH_SIZE = config('FIRECRAWL_BATCH_SIZE', default=5, cast=int)
FIRECRAWL_TIMEOUT_MS = config('FIRECRAWL_TIMEOUT_MS', default=30000, cast=int)
YOUTUBE_API_KEY = config('YOUTUBE_API_KEY', default='')
GITHUB_APP_CLIENT_ID = config('GITHUB_APP_CLIENT_ID', default='')
GITHUB_CONTEXT_CHAR_LIMIT = config('GITHUB_CONTEXT_CHAR_LIMIT', default=5000, cast=int)
SLACK_CUSTOM_GURU_NOTIFIER_WEBHOOK_URL = config('SLACK_CUSTOM_GURU_NOTIFIER_WEBHOOK_URL', default='')
