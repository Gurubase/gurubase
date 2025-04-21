import os
import sys
import django
import logging
from tqdm import tqdm
from time import sleep
# Setup Django environment
sys.path.append('/workspaces/gurubase/src/gurubase-backend/backend')
sys.path.append('/workspaces/gurubase-backend/backend')
sys.path.append('/workspace/backend')
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.settings")
django.setup()

from django.db import transaction
from core.models import DataSource, GithubFile

logger = logging.getLogger(__name__)

def total_datasources():
    return DataSource.objects.count()

def total_not_processed_datasources():
    return DataSource.objects.filter(status=DataSource.Status.NOT_PROCESSED).count()

def total_github_files():
    return GithubFile.objects.count()

def reset_datasources():
    """
    Resets all DataSource statuses to NOT_PROCESSED and sets in_milvus to False.
    """
    try:
        total_datasources = DataSource.objects.count()
        logger.info(f"Found {total_datasources} datasources to reset")

        processed = 0
        batch_size = 100
        
        with tqdm(total=total_datasources, desc="Resetting datasources") as pbar:
            # Use iterator() to avoid loading all objects into memory at once
            for datasource in DataSource.objects.iterator(chunk_size=batch_size):
                with transaction.atomic():
                    datasource.status = DataSource.Status.NOT_PROCESSED
                    datasource.in_milvus = False
                    datasource.doc_ids = []
                    datasource.save()
                    processed += 1
                    pbar.update(1)

                if processed % 1000 == 0:
                    sleep(1)

        logger.info(f"Successfully reset {processed} datasources")
        
        if processed != total_datasources:
            logger.warning(f"Mismatch in update count: Expected {total_datasources}, Updated {processed}")

    except Exception as e:
        logger.error(f"Error resetting datasources: {str(e)}")
        raise

def delete_github_files():
    """
    Deletes all GithubFiles from the database.
    """
    try:
        total_github_files = GithubFile.objects.count()
        logger.info(f"Found {total_github_files} GitHub files to delete")

        processed = 0
        batch_size = 100
        
        with tqdm(total=total_github_files, desc="Deleting GitHub files") as pbar:
            # Use iterator() to avoid loading all objects into memory at once
            for github_file in GithubFile.objects.iterator(chunk_size=batch_size):
                with transaction.atomic():
                    github_file.delete()
                    processed += 1
                    pbar.update(1)

                if processed % 1000 == 0:
                    sleep(1)

        logger.info(f"Successfully deleted {processed} GitHub files")
        
        if processed != total_github_files:
            logger.warning(f"Mismatch in delete count: Expected {total_github_files}, Deleted {processed}")

    except Exception as e:
        logger.error(f"Error deleting GitHub files: {str(e)}")
        raise

def main():
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

    logger.info("Starting reset script")
    try:
        # logger.info("Step 1: Resetting datasources")
        # reset_datasources()
        
        logger.info("Step 2: Deleting GitHub files")
        delete_github_files()
        
        logger.info("Successfully completed all reset operations")
    except Exception as e:
        logger.error(f"Script failed: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    print(f"Total datasources: {total_datasources()}")
    print(f"Total not processed datasources: {total_not_processed_datasources()}")
    print(f"Total GitHub files: {total_github_files()}")
    print("Do you want to continue? (y/n)")
    if input() == "y":
        main()  