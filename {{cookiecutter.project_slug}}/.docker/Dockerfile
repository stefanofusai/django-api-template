FROM python:3.14.5-slim AS base

FROM base AS builder

COPY --from=ghcr.io/astral-sh/uv:0.11.29 /uv /uvx /bin/

WORKDIR /app

ARG UV_DEPENDENCY_GROUP=prod

ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy
ENV UV_PROJECT_ENVIRONMENT=/app/.venv

# Dependencies only (no project) so this layer caches until the lockfile
# changes; the post-COPY sync below installs the rest.
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --group=${UV_DEPENDENCY_GROUP} --locked --no-default-groups --no-install-project

COPY . /app

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --group=${UV_DEPENDENCY_GROUP} --locked --no-default-groups

# collectstatic only for the prod image: prod serves pre-collected static
# via whitenoise (a prod-group dep), whereas dev serves static from source
# through runserver_plus, so a dev build neither needs nor has whitenoise.
# Throwaway env values: prod settings require them at import time but nothing
# reads them during collectstatic; DATABASE_URL is parse-only (no connection).
RUN if [ "$UV_DEPENDENCY_GROUP" = "prod" ]; then \
        ALLOWED_HOSTS=localhost \
{%- if cookiecutter.use_s3_media == "yes" %}
        AWS_STORAGE_BUCKET_NAME=mock-storage-bucket \
{%- endif %}
{%- if cookiecutter.redis == "compose" %}
        CACHE_URL=rediscache://:mock-redis-password@localhost:6379/0 \
{%- else %}
        CACHE_URL=locmemcache:// \
{%- endif %}
{%- if cookiecutter.use_celery != "none" and cookiecutter.redis == "compose" %}
        CELERY_BROKER_URL=redis://:mock-redis-password@localhost:6379/1 \
{%- endif %}
        CSRF_TRUSTED_ORIGINS=https://localhost \
        DATABASE_URL=postgres://postgres:mock-postgres-password@localhost:5432/postgres \
{%- if cookiecutter.email_provider != "none" %}
        DEFAULT_FROM_EMAIL=noreply@example.test \
{%- endif %}
        DJANGO_ENV=prod \
{%- if cookiecutter.email_provider == "smtp" %}
        EMAIL_HOST=smtp.example.test \
{%- endif %}
{%- if cookiecutter.postgres == "compose" %}
        POSTGRES_PASSWORD=mock-postgres-password \
{%- endif %}
{%- if cookiecutter.email_provider == "resend" %}
        RESEND_API_KEY=mock-resend-api-key \
{%- endif %}
{%- if cookiecutter.redis == "compose" %}
        REDIS_PASSWORD=mock-redis-password \
{%- endif %}
        SECRET_KEY=mock-secret-key-0123456789-abcdefghijklmnopqrstuvwxyz \
{%- if cookiecutter.use_sentry == "yes" %}
        SENTRY_DSN=https://mock-sentry-key@sentry.example.test/1 \
{%- endif %}
        .venv/bin/python manage.py collectstatic --no-input; \
    fi

FROM base AS runtime

# Apt package versions follow the pinned Debian base image and remain patchable.
# hadolint ignore=DL3008
RUN apt-get update \
    && apt-get install --no-install-recommends --yes \
        curl \
    && rm -rf /var/lib/apt/lists/*

ENV PATH=/app/.venv/bin:$PATH
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONPATH=/app/src
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN addgroup --system app \
    && adduser --home=/app --ingroup=app --system app

COPY --chown=app:app --from=builder /app /app

USER app

EXPOSE 8000

CMD ["/app/.docker/scripts/gunicorn.sh"]
