from django.conf import settings

def environment_processor(request):
    return {
        'is_production': settings.ENV == 'production'
    }
