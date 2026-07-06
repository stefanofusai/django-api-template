#!/bin/sh
set -eu

ALLOWED_HOSTS=localhost \
{%- if cookiecutter.use_s3_media == "yes" %}
AWS_STORAGE_BUCKET_NAME=$(uuidgen) \
{%- endif %}
CACHE_URL=locmemcache:// \
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
SECRET_KEY=$(uuidgen)$(uuidgen) \
{%- if cookiecutter.use_sentry == "yes" %}
SENTRY_DSN=https://$(uuidgen | tr -d -)@sentry.example.com/1 \
{%- endif %}
uv run --group=ci --locked --no-default-groups \
    python manage.py check --deploy --fail-level=WARNING --tag=security
