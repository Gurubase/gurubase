import os
import sys
import django
import logging
from typing import List
from tqdm import tqdm

# Setup Django environment
sys.path.append('/workspaces/gurubase/src/gurubase-backend/backend')
sys.path.append('/workspaces/gurubase-backend/backend')
sys.path.append('/workspace/backend')
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.settings")
django.setup()

from django.db import transaction
from core.models import GuruType, Question, DataSource, Binge, OutOfContextQuestion, CrawlState
from core.services.data_source_service import DataSourceService

logger = logging.getLogger(__name__)

def remove_guru(guru_slug: str) -> None:
    """
    Removes a guru and all its associated data in the following order:
    1. Questions
    2. DataSources
    3. Binges
    4. OutOfContextQuestions
    5. CrawlStates
    6. GuruType itself
    """
    try:
        guru_type = GuruType.objects.get(slug=guru_slug)
    except GuruType.DoesNotExist:
        logger.error(f"Guru {guru_slug} not found")
        return

    logger.info(f"Starting removal of guru: {guru_slug}")

    # 1. Remove Questions
    questions_count = Question.objects.filter(guru_type=guru_type).count()
    if questions_count > 0:
        logger.info(f"Removing {questions_count} questions for {guru_slug}")
        with tqdm(total=questions_count, desc="Removing questions") as pbar:
            # Delete in chunks to avoid memory issues
            while Question.objects.filter(guru_type=guru_type).exists():
                questions_to_delete = list(Question.objects.filter(guru_type=guru_type)[:10].values_list('id', flat=True))
                Question.objects.filter(id__in=questions_to_delete).delete()
                pbar.update(len(questions_to_delete))

    # 2. Remove DataSources
    datasources_count = DataSource.objects.filter(guru_type=guru_type).count()
    if datasources_count > 0:
        logger.info(f"Removing {datasources_count} data sources for {guru_slug}")
        service = DataSourceService(guru_type, None)  # None for user as we're running a script
        
        with tqdm(total=datasources_count, desc="Removing data sources") as pbar:
            while DataSource.objects.filter(guru_type=guru_type).exists():
                datasources = DataSource.objects.filter(guru_type=guru_type)[:50]
                ids = list(datasources.values_list('id', flat=True))
                try:
                    service.delete_data_sources(ids)
                except Exception as e:
                    logger.error(f"Error deleting data sources batch: {e}")
                pbar.update(len(ids))

    # 3. Remove Binges
    binge_count = Binge.objects.filter(guru_type=guru_type).count()
    if binge_count > 0:
        logger.info(f"Removing {binge_count} binges for {guru_slug}")
        with tqdm(total=binge_count, desc="Removing binges") as pbar:
            while Binge.objects.filter(guru_type=guru_type).exists():
                binges_to_delete = list(Binge.objects.filter(guru_type=guru_type)[:100].values_list('id', flat=True))
                deleted_count, _ = Binge.objects.filter(id__in=binges_to_delete).delete()
                pbar.update(deleted_count)

    # 4. Remove OutOfContextQuestions
    ooc_question_count = OutOfContextQuestion.objects.filter(guru_type=guru_type).count()
    if ooc_question_count > 0:
        logger.info(f"Removing {ooc_question_count} out-of-context questions for {guru_slug}")
        with tqdm(total=ooc_question_count, desc="Removing OOC questions") as pbar:
            while OutOfContextQuestion.objects.filter(guru_type=guru_type).exists():
                ooc_questions_to_delete = list(OutOfContextQuestion.objects.filter(guru_type=guru_type)[:100].values_list('id', flat=True))
                deleted_count, _ = OutOfContextQuestion.objects.filter(id__in=ooc_questions_to_delete).delete()
                pbar.update(deleted_count)
                
    # 5. Remove CrawlStates
    crawl_state_count = CrawlState.objects.filter(guru_type=guru_type).count()
    if crawl_state_count > 0:
        logger.info(f"Removing {crawl_state_count} crawl states for {guru_slug}")
        with tqdm(total=crawl_state_count, desc="Removing crawl states") as pbar:
            while CrawlState.objects.filter(guru_type=guru_type).exists():
                crawl_states_to_delete = list(CrawlState.objects.filter(guru_type=guru_type)[:100].values_list('id', flat=True))
                deleted_count, _ = CrawlState.objects.filter(id__in=crawl_states_to_delete).delete()
                pbar.update(deleted_count)

    # 6. Remove GuruType
    try:
        with transaction.atomic():
            logger.info(f"Attempting to delete GuruType: {guru_slug}")
            guru_type.delete()
            logger.info(f"Successfully removed guru: {guru_slug}")
    except Exception as e:
        logger.error(f"Error deleting guru type {guru_slug}: {e}")

def main():
    if len(sys.argv) != 2:
        logger.error("Usage: python remove_gurus.py guru1,guru2,guru3")
        return

    # Get guru slugs from command line argument and split by comma
    gurus_to_remove = sys.argv[1].split(',')
    
    if not gurus_to_remove:
        logger.error("No gurus specified for removal")
        return

    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

    for guru_slug in gurus_to_remove:
        print(f"--------------------------------")
        guru_slug = guru_slug.strip()  # Remove any whitespace
        print(f"Removing guru")
        try:
            remove_guru(guru_slug)
        except Exception as e:
            logger.error(f"Failed to remove guru {guru_slug}: {e}")

if __name__ == "__main__":
    main()