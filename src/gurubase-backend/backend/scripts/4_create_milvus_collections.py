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
from core.models import Settings
from core.utils import get_embedding_model_config

# Get the default embedding model
default_model = Settings.get_default_embedding_model()

# Get the collection name and dimension for the default model
collection_name, dimension = get_embedding_model_config(default_model)

# Create the collection with the appropriate configuration
create_code_context_collection(collection_name, dimension=dimension)
