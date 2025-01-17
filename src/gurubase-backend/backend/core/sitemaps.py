import logging
from django.contrib.sitemaps import Sitemap
from django.conf import settings
from .models import GuruType, Question

logger = logging.getLogger(__name__)

class GuruTypeSitemap(Sitemap):
    protocol = 'https' if settings.ENV in ['production', 'staging'] else 'http'

    def items(self):
        return GuruType.objects.filter(active=True)

    def location(self, item: GuruType):
        return f'/g/{item.slug}'

class GuruTypeQuestionSitemap(Sitemap):
    limit = settings.SITEMAP_LIMIT
    protocol = 'https' if settings.ENV in ['production', 'staging'] else 'http'

    def __init__(self, guru_type_slug):
        self.guru_type_slug = guru_type_slug

    def items(self):
        return Question.objects.filter(
            add_to_sitemap=True,
            guru_type__slug=self.guru_type_slug,
            parent=None
        ).order_by('id')

    def location(self, item: Question):
        return f'/g/{item.guru_type.slug}/{item.slug}'

class StaticSitemap(Sitemap):
    # https://gurubase.io
    protocol = 'https' if settings.ENV in ['production', 'staging'] else 'http'

    def items(self):
        return ['main']

    def location(self, item):
        return '/'

# Create a dictionary of sitemaps dynamically
def get_sitemaps():
    sitemaps = {
        'gurubase-main-site': StaticSitemap(),
        'gurubase-guru-types': GuruTypeSitemap(),
    }
    try:
        guru_types = GuruType.objects.filter(active=True, has_sitemap_added_questions=True)
        for guru_type in guru_types:
            sitemaps[guru_type.slug] = GuruTypeQuestionSitemap(guru_type.slug)
    except Exception as e:
        logger.error(f'Error while getting sitemaps. This may be due to a change in the database schema. Please make sure you redeploy the app for the sitemaps to work.', exc_info=True)
    return sitemaps

# Use this function in your urls.py

