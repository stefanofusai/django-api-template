#!/bin/sh
set -eu

export DATABASE_STATEMENT_TIMEOUT="${CELERY_DATABASE_STATEMENT_TIMEOUT:-300000}"

exec celery \
    -A config \
    worker \
    --concurrency="$CELERY_WORKER_CONCURRENCY" \
    --hostname=celery-worker@%h \
    --loglevel="$LOG_LEVEL" \
    --max-tasks-per-child="$CELERY_WORKER_MAX_TASKS_PER_CHILD"
