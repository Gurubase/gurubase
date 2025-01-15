import os
import sys
import django



sys.path.append('/workspaces/gurubase-backend/backend')
sys.path.append('/workspace/backend')
sys.path.append('/workspaces/kubernetesguru-backend/backend')
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.settings")

django.setup()
from core.utils import get_default_settings

default_settings = get_default_settings()
default_settings.pricings = {
    'gpt-4o-2024-08-06': {
        'prompt': 2.5 / 1_000_000,
        'cached_prompt': 1.25 / 1_000_000,
        'completion': 10 / 1_000_000
    },
    'gpt-4o-mini-2024-07-18': {
        'prompt': 0.15 / 1_000_000,
        'cached_prompt': 0.075 / 1_000_000,
        'completion': 0.6 / 1_000_000
    },
    'gemini-1.5-flash': {
        'prompt': 0.075 / 1_000_000,
        'completion': 0.3 / 1_000_000
    },
    'gemini-1.5-flash-002': {
        'prompt': 0.075 / 1_000_000,
        'completion': 0.3 / 1_000_000
    }
}

default_settings.trust_score_threshold = 0.5
default_settings.save()