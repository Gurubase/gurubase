#!/bin/bash

set -o errexit
set -o nounset

cd backend && exec celery --app backend flower