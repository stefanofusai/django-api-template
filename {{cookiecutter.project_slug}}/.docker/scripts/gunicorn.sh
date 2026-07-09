#!/bin/sh
set -eu

exec gunicorn \
    --bind=0.0.0.0:8000 \
    --graceful-timeout="$GUNICORN_GRACEFUL_TIMEOUT" \
    --max-requests="$GUNICORN_MAX_REQUESTS" \
    --max-requests-jitter="$GUNICORN_MAX_REQUESTS_JITTER" \
    --no-control-socket \
    --pythonpath=src \
    --timeout="$GUNICORN_TIMEOUT" \
    --worker-class=uvicorn_worker.UvicornWorker \
    --workers="$GUNICORN_WORKERS" \
    config.asgi:application
