#!/bin/sh
# Env lives in this rendered script, not inline in the calling workflow, because
# .github/workflows/* ship without Jinja rendering (cookiecutter
# _copy_without_render), so knob-conditional env vars can only be branched here.
set -eu

ALLOWED_HOSTS=localhost \
{%- if cookiecutter.use_s3_media == "yes" %}
AWS_STORAGE_BUCKET_NAME=$(uuidgen) \
{%- endif %}
CACHE_URL=redis://:redis-ci-password@localhost:6379/0 \
{%- if cookiecutter.use_celery != "none" %}
CELERY_BROKER_URL=redis://:redis-ci-password@localhost:6379/1 \
{%- endif %}
CSRF_TRUSTED_ORIGINS=https://localhost \
DATABASE_URL=postgres://postgres:postgres@localhost:5432/postgres \
{%- if cookiecutter.email_provider != "none" %}
DEFAULT_FROM_EMAIL=noreply@example.com \
{%- endif %}
DJANGO_ENV=prod \
{%- if cookiecutter.email_provider == "smtp" %}
EMAIL_HOST=smtp.example.com \
{%- endif %}
{%- if cookiecutter.email_provider == "resend" %}
RESEND_API_KEY=$(uuidgen) \
{%- endif %}
POSTGRES_PASSWORD=postgres \
REDIS_PASSWORD=redis-ci-password \
SECRET_KEY=$(uuidgen)$(uuidgen) \
{%- if cookiecutter.use_sentry == "yes" %}
SENTRY_DSN=https://$(uuidgen)@sentry.example.com/1 \
{%- endif %}
uv run --group=ci --locked --no-default-groups \
    manage.py check --fail-level=WARNING

ALLOWED_HOSTS=localhost \
{%- if cookiecutter.use_s3_media == "yes" %}
AWS_STORAGE_BUCKET_NAME=$(uuidgen) \
{%- endif %}
CACHE_URL=redis://:redis-ci-password@localhost:6379/0 \
{%- if cookiecutter.use_celery != "none" %}
CELERY_BROKER_URL=redis://:redis-ci-password@localhost:6379/1 \
{%- endif %}
CSRF_TRUSTED_ORIGINS=https://localhost \
DATABASE_URL=postgres://postgres:postgres@localhost:5432/postgres \
{%- if cookiecutter.email_provider != "none" %}
DEFAULT_FROM_EMAIL=noreply@example.com \
{%- endif %}
DJANGO_ENV=prod \
{%- if cookiecutter.email_provider == "smtp" %}
EMAIL_HOST=smtp.example.com \
{%- endif %}
{%- if cookiecutter.email_provider == "resend" %}
RESEND_API_KEY=$(uuidgen) \
{%- endif %}
POSTGRES_PASSWORD=postgres \
REDIS_PASSWORD=redis-ci-password \
SECRET_KEY=$(uuidgen)$(uuidgen) \
{%- if cookiecutter.use_sentry == "yes" %}
SENTRY_DSN=https://$(uuidgen | tr -d -)@sentry.example.com/1 \
{%- endif %}
uv run --group=ci --locked --no-default-groups \
    manage.py check --deploy --fail-level=WARNING
