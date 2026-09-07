#!/usr/bin/env bash
set -e

pip install -r requirements_deploy.txt

python manage.py collectstatic --noinput

python manage.py migrate --noinput || echo "WARNING: Migration encountered an issue during build. App will start and run migrations if needed."