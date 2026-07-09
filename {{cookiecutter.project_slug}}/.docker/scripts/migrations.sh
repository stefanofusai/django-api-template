#!/bin/sh
set -eu

export DATABASE_STATEMENT_TIMEOUT=0

python manage.py \
    migrate \
    --no-input
