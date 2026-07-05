FROM python:3.14.5-slim AS base

FROM base AS builder

RUN apt-get update \
    && apt-get install --no-install-recommends --yes \
        uuid-runtime \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:0.11.19 /uv /uvx /bin/

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

# Throwaway values: prod settings require these at import time, but nothing
# reads them during collectstatic.
RUN ALLOWED_HOSTS=localhost \
    AWS_STORAGE_BUCKET_NAME=$(uuidgen) \
    CACHE_URL=locmemcache:// \
    CSRF_TRUSTED_ORIGINS=https://localhost \
    DATABASE_URL=sqlite:///:memory: \
    DJANGO_ENV=prod \
    RESEND_API_KEY=$(uuidgen) \
    SECRET_KEY=$(uuidgen)$(uuidgen) \
    SENTRY_DSN=https://$(uuidgen | tr -d -)@sentry.example.com/1 \
    .venv/bin/python manage.py collectstatic --no-input

FROM base AS runtime

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
