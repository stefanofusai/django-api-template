#!/bin/sh
# Env lives in this rendered script, not inline in the calling workflow, because
# .github/workflows/* ship without Jinja rendering (cookiecutter
# _copy_without_render), so knob-conditional env vars can only be branched here.
set -eu

ALLOWED_HOSTS=localhost \
CACHE_URL=locmemcache:// \
{%- if cookiecutter.use_cors == "yes" %}
CORS_ALLOWED_ORIGINS=https://app.example.com \
{%- endif %}
DATABASE_URL=postgres://postgres:postgres@localhost:5432/postgres \
{%- if cookiecutter.email_provider != "none" %}
DEFAULT_FROM_EMAIL=noreply@example.com \
{%- endif %}
DJANGO_ENV=ci \
SECRET_KEY=ci-secret-for-migrations-0123456789-abcdefghijklmnopqrstuvwxyz \
uv run --group=ci --locked --no-default-groups \
    manage.py makemigrations --check --dry-run

ALLOWED_HOSTS=localhost \
CACHE_URL=locmemcache:// \
{%- if cookiecutter.use_cors == "yes" %}
CORS_ALLOWED_ORIGINS=https://app.example.com \
{%- endif %}
DATABASE_URL=postgres://postgres:postgres@localhost:5432/postgres \
{%- if cookiecutter.email_provider != "none" %}
DEFAULT_FROM_EMAIL=noreply@example.com \
{%- endif %}
DJANGO_ENV=ci \
SECRET_KEY=ci-secret-for-migrations-0123456789-abcdefghijklmnopqrstuvwxyz \
uv run --group=ci --locked --no-default-groups \
    manage.py lintmigrations
