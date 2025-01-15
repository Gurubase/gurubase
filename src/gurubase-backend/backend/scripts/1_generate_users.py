
import os
import sys

import django
sys.path.append('/workspaces/gurubase/src/gurubase-backend/backend')
sys.path.append('/workspaces/gurubase-backend/backend')
sys.path.append('/workspace/backend')
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.settings")
django.setup()

from django.contrib.auth import get_user_model
from django.conf import settings

ROOT_EMAIL = settings.ROOT_EMAIL
ROOT_PASSWORD = settings.ROOT_PASSWORD

if not ROOT_EMAIL:
    print("ERR: You must set ROOT_EMAIL environment variable")
if not ROOT_PASSWORD:
    print("ERR: You must set ROOT_PASSWORD environment variable")

user_model = get_user_model()

# Create root user
user = user_model.objects.filter(email=ROOT_EMAIL)[0:1]
if not user:
    user = user_model.objects.create_superuser(email=ROOT_EMAIL, password=ROOT_PASSWORD, name='root')
    print("Created root user.")
    print(f"Email: {ROOT_EMAIL}")
    print(f"Password: {ROOT_PASSWORD}")
else:
    print("Root user already exists.")
