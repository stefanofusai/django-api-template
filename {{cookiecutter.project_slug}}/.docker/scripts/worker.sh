#!/bin/sh
set -eu

exec celery \
    -A config \
    worker \
    --concurrency="$CELERY_WORKER_CONCURRENCY" \
    --hostname=worker@%h \
    --loglevel="$LOG_LEVEL" \
    --max-tasks-per-child="$CELERY_WORKER_MAX_TASKS_PER_CHILD"
