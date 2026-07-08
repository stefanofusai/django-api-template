#!/bin/sh
set -eu

append_env() {
    key=$1
    value=$2

    printf '%s=%s\n' "$key" "$value" >> .env
}

replace_env() {
    key=$1
    value=$2

    sed -i "s|^${key}=.*|${key}=${value}|" .env
}

set_env() {
    key=$1
    value=$2

    if grep -q "^${key}=" .env; then
        replace_env "$key" "$value"
    else
        append_env "$key" "$value"
    fi
}

{%- if cookiecutter.postgres == "compose" or cookiecutter.postgres == "external" %}
postgres_password=$(uuidgen)
{%- endif %}
{%- if cookiecutter.redis == "compose" or cookiecutter.redis == "external" %}
redis_password=$(uuidgen)
{%- endif %}

replace_env ALLOWED_HOSTS "localhost,127.0.0.1,api.example.test"
{%- if cookiecutter.use_s3_media == "yes" %}
replace_env AWS_STORAGE_BUCKET_NAME "$(uuidgen)"
{%- endif %}
{%- if cookiecutter.redis == "compose" or cookiecutter.redis == "external" %}
replace_env CACHE_URL "rediscache://:${redis_password}@redis:6379/0"
{%- endif %}
{%- if (cookiecutter.redis == "compose" or cookiecutter.redis == "external") and cookiecutter.use_celery != "none" %}
replace_env CELERY_BROKER_URL "redis://:${redis_password}@redis:6379/1"
{%- endif %}
{%- if cookiecutter.postgres == "compose" %}
replace_env DATABASE_URL "postgres://{{ cookiecutter.project_slug.replace('-', '_') }}:${postgres_password}@postgres:5432/{{ cookiecutter.project_slug.replace('-', '_') }}"
{%- elif cookiecutter.postgres == "external" %}
replace_env DATABASE_URL "postgres://ci:${postgres_password}@postgres:5432/ci"
{%- endif %}
{%- if cookiecutter.email_provider == "smtp" %}
replace_env EMAIL_HOST "$(uuidgen).smtp.example.com"
{%- endif %}
{%- if cookiecutter.postgres == "compose" %}
replace_env POSTGRES_PASSWORD "$postgres_password"
{%- elif cookiecutter.postgres == "external" %}
set_env POSTGRES_DB ci
set_env POSTGRES_PASSWORD "$postgres_password"
set_env POSTGRES_USER ci
{%- endif %}
{%- if cookiecutter.redis == "compose" %}
replace_env REDIS_PASSWORD "$redis_password"
{%- elif cookiecutter.redis == "external" %}
set_env REDIS_PASSWORD "$redis_password"
{%- endif %}
{%- if cookiecutter.email_provider == "resend" %}
replace_env RESEND_API_KEY "$(uuidgen)"
{%- endif %}
replace_env SECRET_KEY "$(uuidgen)$(uuidgen)"
{%- if cookiecutter.use_sentry == "yes" %}
replace_env SENTRY_DSN "https://$(uuidgen | tr -d -)@sentry.example.com/1"
{%- endif %}
