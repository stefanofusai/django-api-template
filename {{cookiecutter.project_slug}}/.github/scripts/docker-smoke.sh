#!/bin/sh
set -eu

replace_env() {
    key=$1
    value=$2

    sed -i "s|^${key}=.*|${key}=${value}|" .env
}

{%- if cookiecutter.postgres == "compose" %}
postgres_password=$(uuidgen)
{%- endif %}
{%- if cookiecutter.redis == "compose" %}
redis_password=$(uuidgen)
{%- endif %}

replace_env ALLOWED_HOSTS "localhost,127.0.0.1,api.example.test"
{%- if cookiecutter.use_s3_media == "yes" %}
replace_env AWS_STORAGE_BUCKET_NAME "$(uuidgen)"
{%- endif %}
{%- if cookiecutter.redis == "compose" %}
replace_env CACHE_URL "rediscache://:${redis_password}@redis:6379/0"
{%- endif %}
{%- if cookiecutter.redis == "compose" and cookiecutter.use_celery != "none" %}
replace_env CELERY_BROKER_URL "redis://:${redis_password}@redis:6379/1"
{%- endif %}
{%- if cookiecutter.postgres == "compose" %}
replace_env DATABASE_URL "postgres://{{ cookiecutter.project_slug.replace('-', '_') }}:${postgres_password}@postgres:5432/{{ cookiecutter.project_slug.replace('-', '_') }}"
{%- endif %}
{%- if cookiecutter.email_provider == "smtp" %}
replace_env EMAIL_HOST "$(uuidgen).smtp.example.com"
{%- endif %}
{%- if cookiecutter.postgres == "compose" %}
replace_env POSTGRES_PASSWORD "$postgres_password"
{%- endif %}
{%- if cookiecutter.redis == "compose" %}
replace_env REDIS_PASSWORD "$redis_password"
{%- endif %}
{%- if cookiecutter.email_provider == "resend" %}
replace_env RESEND_API_KEY "$(uuidgen)"
{%- endif %}
replace_env SECRET_KEY "$(uuidgen)$(uuidgen)"
{%- if cookiecutter.use_sentry == "yes" %}
replace_env SENTRY_DSN "https://$(uuidgen | tr -d -)@sentry.example.com/1"
{%- endif %}
