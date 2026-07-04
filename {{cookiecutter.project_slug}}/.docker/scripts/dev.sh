#!/bin/sh
set -eu

exec python manage.py \
    runserver_plus \
    0.0.0.0:8000
