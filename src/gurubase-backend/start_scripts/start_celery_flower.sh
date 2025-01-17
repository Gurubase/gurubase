#!/bin/bash

set -o errexit
set -o nounset

cd backend && celery --app backend flower