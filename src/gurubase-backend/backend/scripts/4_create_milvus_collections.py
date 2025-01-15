
import os
import sys

import django
sys.path.append('/workspaces/gurubase/src/gurubase-backend/backend')
sys.path.append('/workspaces/gurubase-backend/backend')
sys.path.append('/workspace/backend')
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.settings")
django.setup()

from django.conf import settings
from core.milvus_utils import create_code_context_collection

collection_name = settings.GITHUB_REPO_CODE_COLLECTION_NAME

create_code_context_collection(collection_name)
