# {{ cookiecutter.project_slug }}

[![Tests](https://github.com/{{ cookiecutter.github_username }}/{{ cookiecutter.project_slug }}/actions/workflows/tests.yaml/badge.svg?branch=main)](https://github.com/{{ cookiecutter.github_username }}/{{ cookiecutter.project_slug }}/actions/workflows/tests.yaml)
[![Coverage](https://img.shields.io/badge/coverage-100%25-brightgreen)](#testing)

{{ cookiecutter.description }}

The project is built on Django, Django Ninja, PostgreSQL, Redis, Celery,
django-celery-beat, django-celery-results, django-structlog,
django-storages, Docker Compose, pytest, Ruff, Ty, and uv.

## Architecture

```text
src/config/          Django settings, URLs, Celery app, WSGI entrypoint
src/apps/core/       shared abstract model bases
src/apps/api/        Django Ninja API, schemas, pagination, request metadata
tests/               unit and integration tests
.docker/             Dockerfile, Compose files, entrypoint scripts
.github/            CI, pre-commit, dependency audit, Docker build workflows
```

Settings use `django-split-settings` with reusable components and environment
overlays:

- `ci` uses SQLite, eager Celery tasks, and in-memory storage.
- `dev` enables developer tooling and filesystem-backed media.
- `prod` uses secure cookie/HTTPS settings, WhiteNoise static files, and
  private S3-compatible storage.

## Quickstart

Requirements:

- Docker Compose >= 2.30 (lifecycle hooks and start_interval)
- Python 3.14
- [uv](https://docs.astral.sh/uv/)

Install dependencies and create a local environment file:

```shell
uv sync --locked
cp .env.example .env
uv run pre-commit install --install-hooks
```

Start the local stack:

```shell
docker compose -f .docker/compose/dev.yaml up --build
```

The API runs migrations with a Compose `pre_start` step before the service
starts. When the API is healthy, the Celery services start and you can open:

- API docs: <http://localhost:8000/api/docs>
- Django Admin: <http://localhost:8000/admin/>
- health: <http://localhost:8000/api/health>
- readiness: <http://localhost:8000/api/ready>
- versioned API docs: <http://localhost:8000/api/v1/docs>

Create a staff user inside the running API container:

```shell
docker compose -f .docker/compose/dev.yaml exec api python manage.py createsuperuser
```

Stop the stack with:

```shell
docker compose -f .docker/compose/dev.yaml down
```

## Local Setup

`.env.example` contains the variables needed by the Compose stack. The defaults
target local PostgreSQL and Redis containers:

- `AWS_STORAGE_BUCKET_NAME` is required in production; optional AWS variables
  are commented.
- `CACHE_URL` uses Redis database 0.
- `CELERY_BROKER_URL` uses Redis database 1.
- `CELERY_WORKER_CONCURRENCY` and `CELERY_WORKER_MAX_TASKS_PER_CHILD` size the
  worker process.
- `DATABASE_URL` points Django at the `postgres` service.
- `GUNICORN_*` values are required by the production web entrypoint.

The development Compose file starts `api`, `celery-beat`, `celery-worker`,
`postgres`, and `redis`. It bind-mounts `manage.py` and `src/` for local code
changes, and stores media files in a Docker volume.

Development prints email to the console, tests keep email in memory, and
production sends through Resend via django-anymail. Set `RESEND_API_KEY` in
production, set `DEFAULT_FROM_EMAIL` once the sending domain is known, and send
messages asynchronously with `apps.core.tasks.send_email.delay(...)`.

Periodic task schedules are managed in Django Admin through
django-celery-beat's `DatabaseScheduler`. Run exactly one `celery-beat`
instance for a deployment. The `celery-beat` service has no healthcheck and
relies on the Compose restart policy.

## Usage

Check readiness:

```shell
curl -fsS http://localhost:8000/api/ready
```

Browse the API docs:

```shell
open http://localhost:8000/api/docs
```

Browse the versioned business API docs:

```shell
open http://localhost:8000/api/v1/docs
```

Use Django Admin:

```shell
open http://localhost:8000/admin/
```

## Production

Start the production stack:

```shell
docker compose -f .docker/compose/prod.yaml up -d --wait
```

The `api` service publishes no ports. Put your own ingress or reverse proxy in
front of it. The proxy must terminate TLS, set `X-Forwarded-Proto: https` on
forwarded requests, and strip or overwrite any client-supplied
`X-Forwarded-Proto` value. Set `FORWARDED_ALLOW_IPS` to the proxy address so
Gunicorn trusts it. Without that proxy contract, `SECURE_PROXY_SSL_HEADER` is
unsafe and `SECURE_SSL_REDIRECT` will loop.

Before deploying, generate real secrets:

```shell
uv run python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

Use the generated value for `SECRET_KEY`, set a strong `POSTGRES_PASSWORD`, and
keep `127.0.0.1` in `ALLOWED_HOSTS` alongside your domain because the container
healthcheck probes over localhost. The production stack reads the same `.env`
file as development, and production boot refuses `django-insecure-` keys.
Set `SENTRY_DSN` from your Sentry project settings; production boot fails if it
is missing or blank. Sentry release names use the package version from
`pyproject.toml`; tune `SENTRY_ENABLE_LOGS`,
`SENTRY_PROFILE_SESSION_SAMPLE_RATE`, and `SENTRY_TRACES_SAMPLE_RATE` from the
environment.

Use `/api/health` as liveness: it checks that the process is up and backs the
container healthcheck. Use `/api/ready` as readiness: it checks that the
database and cache are reachable for load-balancer routing.

Operational probes are unversioned; business endpoints live under `/api/v1/`.
To introduce v2, create a
`v2_api = NinjaAPI(urls_namespace="v2", version="2.0.0")` instance and mount
it at `path("api/v2/", v2_api.urls)`.

Redis runs append-only for broker durability. Cache and broker share one Redis
instance on databases 0 and 1. Under memory pressure, Redis's default
`noeviction` policy rejects writes instead of evicting keys, which also blocks
task enqueues. Split Redis instances if cache volume grows.

The admin at `/admin/` is exposed wherever the API is routed. Restrict it at
the proxy with an IP allowlist or route only `/api/` publicly.

## Testing

Run the test suite:

```shell
uv run pytest
```

The suite uses CI settings, in-memory SQLite and storage, eager Celery tasks,
and enforces 100% coverage through `pytest-cov`.

Run repository checks:

```shell
uv run pre-commit run --all-files
```

Useful focused checks:

```shell
uv run pre-commit run ruff-check --all-files
uv run pre-commit run ty --all-files
```

CI runs tests, deploy checks, pre-commit, dependency audit, and Docker image
build validation through GitHub Actions.
