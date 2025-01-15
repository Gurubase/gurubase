#!/bin/bash

set -o errexit
set -o pipefail
set -o nounset

APP_PORT=8018

cd backend && ./manage.py migrate && python manage.py collectstatic --noinput --clear && gunicorn --worker-tmp-dir /dev/shm --workers 8 --timeout 120 --bind 0.0.0.0:$APP_PORT backend.wsgi
