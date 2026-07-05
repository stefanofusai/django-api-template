# {{ cookiecutter.project_slug }}

[![Tests](https://github.com/{{ cookiecutter.github_username }}/{{ cookiecutter.project_slug }}/actions/workflows/tests.yaml/badge.svg?branch=main)](https://github.com/{{ cookiecutter.github_username }}/{{ cookiecutter.project_slug }}/actions/workflows/tests.yaml)
[![Coverage](https://img.shields.io/badge/coverage-100%25-brightgreen)](#testing)

{{ cookiecutter.description }}

{% if cookiecutter.use_celery == "worker+beat" and cookiecutter.use_s3_media == "yes" -%}
The project is built on Django, Django Ninja, PostgreSQL, Redis, Celery,
django-celery-beat, django-celery-results, django-structlog,
django-storages, Docker Compose, pytest, Ruff, Ty, and uv.
{%- elif cookiecutter.use_celery == "worker" and cookiecutter.use_s3_media == "yes" %}
The project is built on Django, Django Ninja, PostgreSQL, Redis, Celery,
django-celery-results, django-structlog, django-storages, Docker Compose,
pytest, Ruff, Ty, and uv.
{%- elif cookiecutter.use_celery == "worker+beat" %}
The project is built on Django, Django Ninja, PostgreSQL, Redis, Celery,
django-celery-beat, django-celery-results, django-structlog, Docker Compose,
pytest, Ruff, Ty, and uv.
{%- elif cookiecutter.use_celery == "worker" %}
The project is built on Django, Django Ninja, PostgreSQL, Redis, Celery,
django-celery-results, django-structlog, Docker Compose, pytest, Ruff, Ty,
and uv.
{%- elif cookiecutter.use_s3_media == "yes" %}
The project is built on Django, Django Ninja, PostgreSQL, Redis,
django-structlog, django-storages, Docker Compose, pytest, Ruff, Ty, and uv.
{%- else %}
The project is built on Django, Django Ninja, PostgreSQL, Redis,
django-structlog, Docker Compose, pytest, Ruff, Ty, and uv.
{%- endif %}

## Architecture

```text
{% if cookiecutter.use_celery != "none" -%}
src/config/          Django settings, URLs, Celery app, WSGI entrypoint
{%- else %}
src/config/          Django settings, URLs, WSGI entrypoint
{%- endif %}
src/apps/core/       shared abstract model bases
src/apps/api/        Django Ninja API, schemas, pagination, request metadata
tests/               unit and integration tests
.docker/             Dockerfile, Compose files, entrypoint scripts
.github/            CI, pre-commit, dependency audit, Docker build workflows
```

Settings use `django-split-settings` with reusable components and environment
overlays:

{% if cookiecutter.use_celery != "none" -%}
- `ci` uses SQLite, eager Celery tasks, and in-memory storage.
{%- else %}
- `ci` uses SQLite and in-memory storage.
{%- endif %}
- `dev` enables developer tooling and filesystem-backed media.
{% if cookiecutter.use_s3_media == "yes" -%}
- `prod` uses secure cookie/HTTPS settings, WhiteNoise static files, and
  private S3-compatible storage.
{%- else %}
- `prod` uses secure cookie/HTTPS settings, WhiteNoise static files, and
  filesystem-backed media.
{%- endif %}

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
{%- if cookiecutter.use_celery != "none" %}
starts. When the API is healthy, the Celery services start and you can open:
{%- else %}
starts. When the API is healthy, you can open:
{%- endif %}

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

{%- if cookiecutter.use_s3_media == "yes" %}

- `AWS_STORAGE_BUCKET_NAME` is required in production; optional AWS variables
  are commented.
{%- else %}

{% endif %}
- `CACHE_URL` uses Redis database 0.
{%- if cookiecutter.use_celery != "none" %}
- `CELERY_BROKER_URL` uses Redis database 1.
- `CELERY_WORKER_CONCURRENCY` and `CELERY_WORKER_MAX_TASKS_PER_CHILD` size the
  worker process.
{%- endif %}
- `DATABASE_URL` points Django at the `postgres` service.
- `GUNICORN_*` values are required by the production web entrypoint.

{% if cookiecutter.use_celery == "worker+beat" -%}
The development Compose file starts `api`, `celery-beat`, `celery-worker`,
`postgres`, and `redis`. It bind-mounts `manage.py` and `src/` for local code
changes, and stores media files in a Docker volume.
{%- elif cookiecutter.use_celery == "worker" %}
The development Compose file starts `api`, `celery-worker`, `postgres`, and
`redis`. It bind-mounts `manage.py` and `src/` for local code changes, and
stores media files in a Docker volume.
{%- else %}
The development Compose file starts `api`, `postgres`, and `redis`. It
bind-mounts `manage.py` and `src/` for local code changes, and stores media
files in a Docker volume.
{%- endif %}

{% if cookiecutter.email_provider == "resend" -%}
Development prints email to the console, tests keep email in memory, and
production sends through Resend via django-anymail. Set `RESEND_API_KEY` in
production, set `DEFAULT_FROM_EMAIL` once the sending domain is known, and send
{%- if cookiecutter.use_celery != "none" %}
messages asynchronously with `apps.core.tasks.send_email.delay(...)`.
{%- else %}
messages with `django.core.mail.send_mail(...)`.
{%- endif %}
{%- elif cookiecutter.email_provider == "smtp" %}
Development prints email to the console, tests keep email in memory, and
production sends through your SMTP relay. Set `EMAIL_HOST` in production,
optionally set the other `EMAIL_*` relay values, and send
{%- if cookiecutter.use_celery != "none" %}
messages asynchronously with `apps.core.tasks.send_email.delay(...)`.
{%- else %}
messages with `django.core.mail.send_mail(...)`.
{%- endif %}
{%- endif %}

{% if cookiecutter.use_celery == "worker+beat" -%}
Periodic task schedules are managed in Django Admin through
django-celery-beat's `DatabaseScheduler`. Run exactly one `celery-beat`
instance for a deployment. The `celery-beat` service has no healthcheck and
relies on the Compose restart policy.
{%- endif %}

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

API docs and the OpenAPI schema are public in development and staff-only in
production (`API_DOCS_DECORATOR`). The API itself ships unauthenticated: when
you add the first endpoint that needs protection, set a global auth class
(`NinjaAPI(auth=...)`) or per-router auth; see
<https://django-ninja.dev/guides/authentication/>.

Use Django Admin:

```shell
open http://localhost:8000/admin/
```

## Production

Start the production stack:

```shell
docker compose -f .docker/compose/prod.yaml --env-file=.env up -d --wait
```

{% if cookiecutter.use_traefik == "yes" and cookiecutter.traefik_tls == "letsencrypt" -%}
The production stack includes Traefik. Traefik terminates TLS with Let's
Encrypt using `TRAEFIK_ACME_EMAIL` and `TRAEFIK_DOMAIN`, routes only to healthy
API containers, and overwrites client-supplied forwarded headers. The `api`
service publishes no ports, so `FORWARDED_ALLOW_IPS=*` is safe: only services
on the Compose network can reach it. Port 80 serves probes and lets Django
redirect non-probe HTTP requests; port 443 serves normal traffic.

During `docker rollout`, Traefik actively checks `/api/health`, retries short
backend selection races, waits briefly before stopping the old API container,
and keeps the old process alive for a short drain window after Docker emits the
stop event. Those pieces cover both sides of replacement: the new backend is
not relied on until its HTTP health check passes, and the old backend keeps
serving while Traefik removes it from rotation.
{%- elif cookiecutter.use_traefik == "yes" and cookiecutter.traefik_tls == "external" %}
The production stack includes Traefik. Traefik serves TLS from
`.docker/certs/cert.pem` and `.docker/certs/key.pem`, routes only to healthy
API containers, and overwrites client-supplied forwarded headers. The `api`
service publishes no ports, so `FORWARDED_ALLOW_IPS=*` is safe: only services
on the Compose network can reach it. Port 80 serves probes and lets Django
redirect non-probe HTTP requests; port 443 serves normal traffic.

During `docker rollout`, Traefik actively checks `/api/health`, retries short
backend selection races, waits briefly before stopping the old API container,
and keeps the old process alive for a short drain window after Docker emits the
stop event. Those pieces cover both sides of replacement: the new backend is
not relied on until its HTTP health check passes, and the old backend keeps
serving while Traefik removes it from rotation.
{%- else %}
Bring your own ingress. The production `api` service publishes
`127.0.0.1:8000:8000`; put your proxy on the host in front of that loopback
listener. The proxy must forward `Host` and overwrite client-supplied
`X-Forwarded-Proto` so Django can enforce HTTPS without redirect loops.
{%- endif %}

Before deploying, generate real secrets:

```shell
uv run python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

Use the generated value for `SECRET_KEY`, set a strong `POSTGRES_PASSWORD`, and
keep `127.0.0.1` in `ALLOWED_HOSTS` alongside your domain because the container
healthcheck probes over localhost. The production stack reads the same `.env`
file as development, and production boot refuses `django-insecure-` keys.
{% if cookiecutter.use_sentry == "yes" -%}
Set `SENTRY_DSN` from your Sentry project settings; production boot fails if it
is missing or blank. Sentry release names use the package version from
`pyproject.toml`; tune `SENTRY_ENABLE_LOGS`,
`SENTRY_PROFILE_SESSION_SAMPLE_RATE`, and `SENTRY_TRACES_SAMPLE_RATE` from the
{% if cookiecutter.use_traefik == "yes" -%}
environment. Run production Compose commands from the project root with
`--env-file=.env` so Traefik labels resolve deployment values from the root
environment file.
{%- else %}
environment. Run production Compose commands from the project root with
`--env-file=.env` so deployment values resolve from the root environment file.
{%- endif %}
{%- else %}
Run production Compose commands from the project root with `--env-file=.env`
so deployment values resolve from the root environment file.
{%- endif %}

{%- if cookiecutter.use_traefik == "yes" and cookiecutter.traefik_tls == "external" %}
Place the operator-provided PEM pair at `.docker/certs/cert.pem` and
`.docker/certs/key.pem` on the host. A Cloudflare Origin CA certificate is a
worked example: set the zone's SSL mode to "Full (strict)" and choose the
validity window you want. A purchased certificate, corporate CA certificate, or
externally managed certificate works the same way. Restart the `traefik`
service after replacing files; renewal is the operator's or issuing service's
responsibility.
{%- endif %}
{%- if cookiecutter.use_traefik == "yes" %}

Install docker-rollout once on each host:

```shell
mkdir -p ~/.docker/cli-plugins
curl -fsSL https://raw.githubusercontent.com/wowu/docker-rollout/v0.13/docker-rollout \
  -o ~/.docker/cli-plugins/docker-rollout
chmod +x ~/.docker/cli-plugins/docker-rollout
docker rollout --help
```

Deploy from the project root:

```shell
git pull
docker compose -f .docker/compose/prod.yaml --env-file=.env build
docker compose -f .docker/compose/prod.yaml --env-file=.env run --no-deps --rm api /app/.docker/scripts/migrations.sh
docker rollout -f .docker/compose/prod.yaml --env-file=.env api
docker compose -f .docker/compose/prod.yaml --env-file=.env up -d
```
{%- else %}
Deploy from the project root:

```shell
git pull
docker compose -f .docker/compose/prod.yaml --env-file=.env build
docker compose -f .docker/compose/prod.yaml --env-file=.env run --no-deps --rm api /app/.docker/scripts/migrations.sh
docker compose -f .docker/compose/prod.yaml --env-file=.env up -d
```

Container replacement has brief downtime. Overlap deployment requires the
bundled proxy path.
{%- endif %}

{% if cookiecutter.use_traefik == "yes" -%}
Migrations must stay N-1 compatible because old code keeps serving while the
new schema is live during the rollout overlap. Ship additive migrations first,
then destructive cleanup in a later deploy. The final `up -d` converges the
{%- else %}
Migrations should stay additive across a deploy. Ship destructive cleanup in a
later deploy. The final `up -d` converges the
{%- endif %}
{%- if cookiecutter.use_celery == "worker+beat" %}
remaining services; `celery-worker` and `celery-beat` may restart briefly, and
`acks_late` lets interrupted worker tasks be redelivered.
{%- elif cookiecutter.use_celery == "worker" %}
remaining services; `celery-worker` may restart briefly, and `acks_late` lets
interrupted worker tasks be redelivered.
{%- else %}
remaining services.
{%- endif %}

{%- if cookiecutter.use_traefik == "yes" %}

Traefik mounts the Docker socket read-only for service discovery. That mount is
standard for single-host Docker proxies, but it is effectively root-equivalent
on the host if Traefik is compromised.
{%- endif %}

Use `/api/health` as liveness: it checks that the process is up and backs the
container healthcheck. Use `/api/ready` as readiness: it checks that the
database and cache are reachable for load-balancer routing.

Persistent database connections default to 60 seconds with health checks. Set
`CONN_MAX_AGE=0` when running behind PgBouncer in transaction mode.

Internal probes are unversioned; business endpoints live under `/api/v1/`.
To introduce v2, create a
`v2_api = NinjaAPI(urls_namespace="v2", version="2.0.0")` instance and mount
it at `path("api/v2/", v2_api.urls)`.

{% if cookiecutter.use_celery != "none" -%}
Redis runs append-only for broker durability. Cache and broker share one Redis
instance on databases 0 and 1. Under memory pressure, Redis's default
`noeviction` policy rejects writes instead of evicting keys, which also blocks
task enqueues. Split Redis instances if cache volume grows.
{%- else %}
Redis runs append-only for cache durability. Under memory pressure, Redis's
default `noeviction` policy rejects writes instead of evicting keys.
{%- endif %}

The admin at `/admin/` is exposed wherever the API is routed. Restrict it at
the proxy with an IP allowlist or route only `/api/` publicly.

## Testing

Run the test suite:

```shell
uv run pytest
```

{% if cookiecutter.use_celery != "none" -%}
The suite uses CI settings, in-memory SQLite and storage, eager Celery tasks,
and enforces 100% coverage through `pytest-cov`.
{%- else %}
The suite uses CI settings, in-memory SQLite and storage, and enforces 100%
coverage through `pytest-cov`.
{%- endif %}

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
