#!/usr/bin/env bash
# Render build script. Exits on the first error so a broken build never goes live.
set -o errexit

pip install --upgrade pip
pip install -r requirements.txt

python manage.py collectstatic --noinput
python manage.py migrate --noinput
python manage.py bootstrap_demo
