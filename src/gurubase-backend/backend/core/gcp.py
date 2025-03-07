import logging
from django.conf import settings
import traceback
from django.core.files.storage import FileSystemStorage as DjangoFileSystemStorage

# storage = GoogleCloudStorage()
logger = logging.getLogger(__name__)


def replace_media_root_with_nginx_base_url(url):
    # TODO: Update this when selfhosted url setting is added
    if settings.ENV == 'selfhosted':
        # Replace also for development environment
        if not url:
            logger.error("URL is None", traceback.format_exc())
            return ''
        path = url.split(settings.MEDIA_ROOT)[1]
        return f'{settings.NGINX_BASE_URL}/media{path}'
    return url

def replace_media_root_with_localhost(url):
    if settings.ENV == 'selfhosted':
        if not url:
            logger.error("URL is None", traceback.format_exc())
            return ''
        port = settings.NGINX_BASE_URL[settings.NGINX_BASE_URL.rfind(":"):][1:]
        host = settings.BASE_URL.split("//")[1].split(":")[0]
        # Replace also for development environment
        path = url.split(settings.MEDIA_ROOT)[1]
        return f'http://{host}:{port}/media{path}'
    return url


class GCP:
    def __init__(self, bucket_name=settings.GS_BUCKET_NAME):
        from storages.backends.gcloud import GoogleCloudStorage
        self.bucket_name = bucket_name
        self.storage = GoogleCloudStorage(bucket_name=bucket_name)

    def get_url_prefix(self):
        return f'https://storage.googleapis.com/{self.bucket_name}'

    def upload_image(self, file, target_path):
        try:
            path = self.storage.save(target_path, file)
            return self.storage.url(path), True
        except Exception as e:
            logger.error(f"Error while uploading og image to gcp bucket :{e}", exc_info=True)
            return "", False

    def delete_image(self, id, target_path):
        try:
            self.storage.delete(target_path)
            return True
        except Exception as e:
            logger.error(f"Error while deleting og image from gcp bucket on question deletion with id={id} :{e}", exc_info=True)
            return "", False

    def upload_file(self, file, target_path):
        try:
            self.storage.save(target_path, file)
            return self.storage.url(target_path), True
        except Exception as e:
            logger.error(f"Error while uploading file to gcp bucket :{e}", exc_info=True)
            return "", False

    def delete_file(self, target_path):
        try:
            self.storage.delete(target_path)
            return True
        except Exception as e:
            logger.error(f"Error while deleting file from gcp bucket :{e}", exc_info=True)
            return False


class FileSystemStorage:
    def __init__(self):
        self.storage = DjangoFileSystemStorage()
        self.bucket_name = settings.GS_BUCKET_NAME

    def get_url_prefix(self):
        return settings.MEDIA_URL.rstrip('/')

    def upload_image(self, file, target_path):
        try:
            path = self.storage.save(target_path, file)
            return self.storage.url(path), True
        except Exception as e:
            logger.error(f"Error while uploading image to filesystem: {e}", exc_info=True)
            return "", False

    def delete_image(self, id, target_path):
        try:
            self.storage.delete(target_path)
            return True
        except Exception as e:
            logger.error(f"Error while deleting image from filesystem with id={id}: {e}", exc_info=True)
            return False

    def upload_file(self, file, target_path):
        try:
            path = self.storage.save(target_path, file)
            return self.storage.url(path), True
        except Exception as e:
            logger.error(f"Error while uploading file to filesystem: {e}", exc_info=True)
            return "", False

    def delete_file(self, target_path):
        try:
            self.storage.delete(target_path)
            return True
        except Exception as e:
            logger.error(f"Error while deleting file from filesystem: {e}", exc_info=True)
            return False

if settings.ENV != 'selfhosted':
    OG_IMAGES_GCP = GCP(bucket_name=settings.GS_BUCKET_NAME)
    DATA_SOURCES_GCP = GCP(bucket_name=settings.GS_DATA_SOURCES_BUCKET_NAME)
    PLOTS_GCP = GCP(bucket_name=settings.GS_PLOTS_BUCKET_NAME)
else:
    DATA_SOURCES_FILESYSTEM = FileSystemStorage()
