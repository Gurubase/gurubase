#!/bin/bash

set -o errexit
set -o nounset

cd backend && exec celery --app backend worker --concurrency 2 --pool=threads --purge --hostname backendworker1@%h
