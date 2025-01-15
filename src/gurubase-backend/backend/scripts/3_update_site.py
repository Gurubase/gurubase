
import os
import sys

import django
sys.path.append('/workspaces/gurubase/src/gurubase-backend/backend')
sys.path.append('/workspaces/gurubase-backend/backend')
sys.path.append('/workspace/backend')
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.settings")
django.setup()

from django.contrib.sites.models import Site
from django.conf import settings

site_id = settings.SITE_ID
new_domain = settings.BASE_URL
new_domain = new_domain.replace("http://", "").replace("https://", "")

site = Site.objects.get(id=site_id)
site.domain = new_domain
site.name = new_domain
site.save()

print(f"Site updated: {site.domain}")
