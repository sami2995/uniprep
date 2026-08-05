#!/usr/bin/env bash

pip install -r requirements_deploy.txt

python manage.py collectstatic --noinput

python manage.py migrate