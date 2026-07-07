#!/bin/sh
set -eu

exec gunicorn \
    --access-logfile=- \
    --bind=0.0.0.0:8000 \
    --graceful-timeout="$GUNICORN_GRACEFUL_TIMEOUT" \
    --no-control-socket \
    --pythonpath=src \
    --timeout="$GUNICORN_TIMEOUT" \
    --worker-class=uvicorn_worker.UvicornWorker \
    --workers="$GUNICORN_WORKERS" \
    config.asgi:application
