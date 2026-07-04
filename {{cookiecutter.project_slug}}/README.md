# {{ cookiecutter.project_slug }}

[![Tests](https://github.com/{{ cookiecutter.github_username }}/{{ cookiecutter.project_slug }}/actions/workflows/tests.yaml/badge.svg?branch=main)](https://github.com/{{ cookiecutter.github_username }}/{{ cookiecutter.project_slug }}/actions/workflows/tests.yaml)
[![Coverage](https://img.shields.io/badge/coverage-100%25-brightgreen)](#testing)

{{ cookiecutter.description }}

The project is built on Django, Django Ninja, PostgreSQL, Redis, Celery,
django-celery-results, django-structlog, django-storages, Docker Compose,
pytest, Ruff, Ty, and uv.

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

- Docker with Compose lifecycle hook support
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
starts. When the API is healthy, the worker starts and you can open:

- readiness: <http://localhost:8000/api/ready>
- API docs: <http://localhost:8000/api/docs>
- Django Admin: <http://localhost:8000/admin/>

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

- `DATABASE_URL` points Django at the `postgres` service.
- `CACHE_URL` uses Redis database 0.
- `CELERY_BROKER_URL` uses Redis database 1.
- `CELERY_WORKER_CONCURRENCY` and `CELERY_WORKER_MAX_TASKS_PER_CHILD` size the
  worker process.
- `GUNICORN_*` values are required by the production web entrypoint.
- Optional AWS variables are commented, while `AWS_STORAGE_BUCKET_NAME` is
  required in production.

The development Compose file starts `api`, `worker`, `postgres`, and `redis`.
It bind-mounts `manage.py` and `src/` for local code changes, and stores media
files in a Docker volume.

## Usage

Check readiness:

```shell
curl -fsS http://localhost:8000/api/ready
```

Browse the API docs:

```shell
open http://localhost:8000/api/docs
```

Use Django Admin:

```shell
open http://localhost:8000/admin/
```

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
