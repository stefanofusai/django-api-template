#!/bin/sh
set -eu

replace_env() {
    key=$1
    value=$2

    sed -i "s|^${key}=.*|${key}=${value}|" .env
}

{%- if cookiecutter.use_s3_media == "yes" %}
replace_env AWS_STORAGE_BUCKET_NAME "$(uuidgen)"
{%- endif %}
{%- if cookiecutter.email_provider == "smtp" %}
replace_env EMAIL_HOST "$(uuidgen).smtp.example.com"
{%- elif cookiecutter.email_provider == "resend" %}
replace_env RESEND_API_KEY "$(uuidgen)"
{%- endif %}
replace_env SECRET_KEY "$(uuidgen)$(uuidgen)"
{%- if cookiecutter.use_sentry == "yes" %}
replace_env SENTRY_DSN "https://$(uuidgen | tr -d -)@sentry.example.com/1"
{%- endif %}
