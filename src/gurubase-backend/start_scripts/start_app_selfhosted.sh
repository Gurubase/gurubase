#!/bin/bash

set -o errexit
set -o pipefail
set -o nounset

APP_PORT=8008

cd backend && ./manage.py migrate && python scripts/1_generate_users.py && python scripts/2_generate_periodic_tasks.py && python scripts/3_update_site.py && python scripts/5_fill_llm_prices.py && python scripts/4_create_milvus_collections.py && python manage.py collectstatic --noinput --verbosity 0 && gunicorn --worker-tmp-dir /dev/shm --workers 8 --timeout 120 --bind 0.0.0.0:$APP_PORT backend.wsgi
