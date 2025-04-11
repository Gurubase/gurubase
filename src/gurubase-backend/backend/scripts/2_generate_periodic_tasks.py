import json
import os
import sys
from datetime import datetime, timedelta

import django

sys.path.append('/workspaces/gurubase/src/gurubase-backend/backend')
sys.path.append('/workspaces/gurubase-backend/backend')
sys.path.append('/workspace/backend')
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.settings")
django.setup()

from django_celery_beat.models import IntervalSchedule, PeriodicTask, CrontabSchedule
from django.conf import settings

DAYS = 'days'
HOURS = 'hours'
MINUTES = 'minutes'
SECONDS = 'seconds'
MICROSECONDS = 'microseconds'


periodic_tasks = {
    'task_raw_questions_to_questions': {
        'every': 1,
        'period': HOURS,
        'task': 'core.tasks.task_raw_questions_to_questions',
        'enabled': False,
        'last_run_at': datetime.utcnow() - timedelta(days=90),
        'kwargs': {}
    },
    'task_set_similarities': {
        'every': 1,
        'period': HOURS,
        'task': 'core.tasks.set_similarities',
        'enabled': False,
        'last_run_at': datetime.utcnow() - timedelta(days=90),
        'kwargs': {}
    },
    'task_rewrite_content_for_wrong_markdown_content': {
        'every': 20,
        'period': MINUTES,
        'task': 'core.tasks.rewrite_content_for_wrong_markdown_content',
        'enabled': False,
        'last_run_at': datetime.utcnow() - timedelta(days=90),
        'kwargs': {}
    },
    'task_update_question_as_the_question_content_h1': {
        'every': 30,
        'period': MINUTES,
        'task': 'core.tasks.update_question_as_the_question_content_h1',
        'enabled': False,
        'last_run_at': datetime.utcnow() - timedelta(days=90),
        'kwargs': {}
    },
     'task_fill_empty_og_images': {
        'every': 30,
        'period': MINUTES,
        'task': 'core.tasks.fill_empty_og_images',
        'enabled': False,
        'last_run_at': datetime.utcnow() - timedelta(days=90),
        'kwargs': {}
    },
    'task_find_duplicate_question_titles': {
        'every': 35,
        'period': MINUTES,
        'task': 'core.tasks.find_duplicate_question_titles',
        'enabled': False,
        'last_run_at': datetime.utcnow() - timedelta(days=90),
        'kwargs': {}
    },
    'task_copy_raw_questions': {
        'every': 1,
        'period': HOURS,
        'task': 'core.tasks.copy_raw_questions',
        'enabled': False,
        'last_run_at': datetime.utcnow() - timedelta(days=90),
        'kwargs': {}
    },
    'task_process_titles': {
        'every': 1,
        'period': HOURS,
        'task': 'core.tasks.process_titles',
        'enabled': False,
        'last_run_at': datetime.utcnow() - timedelta(days=90),
        'kwargs': {}
    },
    'task_data_source_retrieval': {
        'every': 2,
        'period': MINUTES,
        'task': 'core.tasks.data_source_retrieval',
        'enabled': True,
        'last_run_at': datetime.utcnow() - timedelta(days=90),
        'kwargs': {}
    },
    # 'task_data_source_to_milvus': {
    #     'every': 20,
    #     'period': MINUTES,
    #     'task': 'core.tasks.data_sources_to_milvus',
    #     'enabled': True,
    #     'last_run_at': datetime.utcnow() - timedelta(days=90),
    #     'kwargs': {}
    # },
    'task_llm_eval': {
        'every': 30,
        'period': DAYS,
        'task': 'core.tasks.llm_eval',
        'enabled': False,
        'last_run_at': None,
        # Kwargs will be updated manually
        'kwargs': {"guru_types": ["kubernetes", "php", "javascript"], "check_answer_relevance": True, "check_context_relevance": True, "check_groundedness": True}
    },
    'task_llm_eval_result': {
        'every': 30,
        'period': DAYS,
        'task': 'core.tasks.llm_eval_result',
        'enabled': False,
        'last_run_at': None,
        # Kwargs will be updated manually
        'kwargs': {"pairs": [("electrum", 1), ("refine", 1)]} # Pairs are (guru_slug, version)
    },
    'task_get_content_links': {
        'every': 10,
        'period': MINUTES,
        'task': 'core.tasks.get_content_links',
        'enabled': True,
        'last_run_at': datetime.utcnow() - timedelta(days=90),
        'kwargs': {}
    },
    'task_check_link_validity': {
        'every': 10,
        'period': MINUTES,
        'task': 'core.tasks.check_link_validity',
        'enabled': True,
        'last_run_at': datetime.utcnow() - timedelta(days=90),
        'kwargs': {}
    },
    'task_check_favicon_validity': {
        'every': 1,
        'period': DAYS,
        'task': 'core.tasks.check_favicon_validity',
        'enabled': True,
        'last_run_at': datetime.utcnow() - timedelta(days=90),
        'kwargs': {}
    },
    'task_move_questions_to_milvus': {
        'every': 1,
        'period': HOURS,
        'task': 'core.tasks.move_questions_to_milvus',
        'enabled': True,
        'last_run_at': datetime.utcnow() - timedelta(days=90),
        'kwargs': {}
    },
    'task_process_sitemap': {
        'every': 1,
        'period': HOURS,
        'task': 'core.tasks.process_sitemap',
        'enabled': False,
        'last_run_at': datetime.utcnow() - timedelta(days=90),
        'kwargs': {}
    },
    'task_summarize_data_sources': {
        'every': 30,
        'period': MINUTES,
        'task': 'core.tasks.summarize_data_sources',
        'enabled': False,
        'last_run_at': datetime.utcnow() - timedelta(days=90),
        'kwargs': {'guru_type_slugs': ["*"]} # For more info on usage, visit implementation
    },
    'task_generate_questions_from_summaries': {
        'every': 30,
        'period': MINUTES,
        'task': 'core.tasks.generate_questions_from_summaries',
        'enabled': False,
        'last_run_at': datetime.utcnow() - timedelta(days=90),
        'kwargs': {'guru_type_slugs': ["*"]} # For more info on usage, visit implementation
    },
    'task_process_summary_questions': {
        'every': 1,
        'period': HOURS,
        'task': 'core.tasks.process_summary_questions',
        'enabled': False,
        'last_run_at': datetime.utcnow() - timedelta(days=90),
        'kwargs': {}
    },
    'task_update_guru_type_details': {
        'every': 5,
        'period': MINUTES,
        'task': 'core.tasks.update_guru_type_details',
        'enabled': True,
        'last_run_at': datetime.utcnow() - timedelta(days=90),
        'kwargs': {}
    },
    'task_check_datasource_in_milvus_false_and_success': {
        'every': 30,
        'period': MINUTES,
        'task': 'core.tasks.check_datasource_in_milvus_false_and_success',
        'enabled': True,
        'last_run_at': datetime.utcnow() - timedelta(days=90),
        'kwargs': {}
    },
    'task_send_request_to_questions_for_cloudflare_cache': {
        'every': 1,
        'period': HOURS,
        'task': 'core.tasks.send_request_to_questions_for_cloudflare_cache',
        'enabled': True,
        'last_run_at': datetime.utcnow() - timedelta(days=90),
        'kwargs': {}
    },
    'task_update_github_details': {
        'every': 1,
        'period': HOURS,
        'task': 'core.tasks.update_github_details',
        'enabled': True,
        'last_run_at': datetime.utcnow() - timedelta(days=90),
        'kwargs': {}
    },
    'task_update_guru_type_sitemap_status': {
        'every': 1,
        'period': HOURS,
        'task': 'core.tasks.update_guru_type_sitemap_status',
        'enabled': False,
        'last_run_at': datetime.utcnow() - timedelta(days=90),
        'kwargs': {}
    },
    'task_update_github_repositories_for_successful_repos': {
        'every': 12,
        'period': HOURS,
        'task': 'core.tasks.update_github_repositories',
        'enabled': True,
        'last_run_at': datetime.utcnow() - timedelta(days=90),
        'kwargs': {'successful_repos': True}
    },
    'task_update_github_repositories_for_failed_repos': {
        'every': 1,
        'period': HOURS,
        'task': 'core.tasks.update_github_repositories',
        'enabled': True,
        'last_run_at': datetime.utcnow() - timedelta(days=90),
        'kwargs': {'successful_repos': False}
    },
    'task_stop_inactive_ui_crawls': {
        'every': 3,  # Change settings.LOGGING.filters.hide_info_specific_task when changing this
        'period': SECONDS,
        'task': 'core.tasks.stop_inactive_ui_crawls',
        'enabled': True,
        'last_run_at': datetime.utcnow() - timedelta(days=90),
        'kwargs': {}
    }
}

if settings.ENV == 'selfhosted':
    periodic_tasks.pop('task_raw_questions_to_questions')
    periodic_tasks.pop('task_set_similarities')
    periodic_tasks.pop('task_move_questions_to_milvus')
    periodic_tasks.pop('task_rewrite_content_for_wrong_markdown_content')
    periodic_tasks.pop('task_update_question_as_the_question_content_h1')
    periodic_tasks.pop('task_fill_empty_og_images')
    periodic_tasks.pop('task_find_duplicate_question_titles')
    periodic_tasks.pop('task_copy_raw_questions')
    periodic_tasks.pop('task_process_titles')
    periodic_tasks.pop('task_llm_eval')
    periodic_tasks.pop('task_llm_eval_result')
    periodic_tasks.pop('task_get_content_links')
    periodic_tasks.pop('task_check_link_validity')
    periodic_tasks.pop('task_process_sitemap')
    periodic_tasks.pop('task_summarize_data_sources')
    periodic_tasks.pop('task_generate_questions_from_summaries')
    periodic_tasks.pop('task_process_summary_questions')
    periodic_tasks.pop('task_check_datasource_in_milvus_false_and_success')
    periodic_tasks.pop('task_send_request_to_questions_for_cloudflare_cache')
    periodic_tasks.pop('task_update_guru_type_sitemap_status')


def get_interval_schedule(task_configuration):
    interval_schedules_queryset = IntervalSchedule.objects.filter(
        every=task_configuration['every'], period=task_configuration['period'])
    if not interval_schedules_queryset:
        interval_schedule = IntervalSchedule(every=task_configuration['every'], period=task_configuration['period'])
        interval_schedule.save()
    else:
        interval_schedule = interval_schedules_queryset[0]
    return interval_schedule


if __name__ == '__main__':
    # Clean up existing tasks except system tasks
    PeriodicTask.objects.exclude(name__startswith='celery.').delete()
    
    # Task creation logic
    for task_name, task_configuration in periodic_tasks.items():
        if 'cron' in task_configuration:
            cron_configuration = task_configuration['cron']
            crontab_schedules_queryset = CrontabSchedule.objects.filter(
                minute=cron_configuration['minute'],
                hour=cron_configuration['hour']
            )
            if not crontab_schedules_queryset:
                crontab_schedule = CrontabSchedule(minute=cron_configuration['minute'],
                                                   hour=cron_configuration['hour'])
                crontab_schedule.save()
            else:
                crontab_schedule = crontab_schedules_queryset[0]
            if PeriodicTask.objects.filter(name=task_name).count() > 0:
                print(f"Periodic task ({task_name}) exists !!!")
                continue
            periodic_task = PeriodicTask(name=task_name,
                                         task=task_configuration['task'],
                                         crontab=crontab_schedule,
                                         enabled=task_configuration["enabled"],
                                         last_run_at=task_configuration["last_run_at"],
                                         kwargs=json.dumps(task_configuration['kwargs']))
            periodic_task.save()
            print(f"Periodic task ({task_name}) created")
            continue
        else:
            if PeriodicTask.objects.filter(name=task_name).count() > 0:
                print(f"Periodic task ({task_name}) exists !!!")
                continue

            interval_schedule = get_interval_schedule(task_configuration=task_configuration)
            periodic_task = PeriodicTask(name=task_name,
                                         task=task_configuration['task'],
                                         interval=interval_schedule,
                                         enabled=task_configuration["enabled"],
                                         last_run_at=task_configuration["last_run_at"],
                                         kwargs=json.dumps(task_configuration['kwargs']))
            periodic_task.save()
            print(f"Periodic task ({task_name}) created")
