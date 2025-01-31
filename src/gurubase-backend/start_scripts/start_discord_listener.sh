#!/bin/bash

set -o errexit
set -o nounset

cd backend && python manage.py discordListener
