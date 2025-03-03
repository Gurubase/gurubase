#!/bin/bash

set -o errexit
set -o nounset

cd backend && \
python scripts/2_generate_periodic_tasks.py && \
exec celery --app backend beat --pidfile= --scheduler django_celery_beat.schedulers:DatabaseScheduler