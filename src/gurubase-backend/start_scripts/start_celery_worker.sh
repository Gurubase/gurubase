#!/bin/bash

set -o errexit
set -o nounset

cd backend && exec celery --app backend worker --concurrency 2 --purge --hostname backendworker1@%h --loglevel=INFO
