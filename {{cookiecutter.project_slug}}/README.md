# {{ cookiecutter.project_slug }}

[![Tests](https://github.com/{{ cookiecutter.github_username }}/{{ cookiecutter.project_slug }}/actions/workflows/tests.yaml/badge.svg?branch=main)](https://github.com/{{ cookiecutter.github_username }}/{{ cookiecutter.project_slug }}/actions/workflows/tests.yaml)
[![Coverage](https://img.shields.io/badge/coverage-100%25-brightgreen)](#testing)

{{ cookiecutter.description }}

{% if cookiecutter.use_celery == "worker+beat" and cookiecutter.use_cors == "yes" and cookiecutter.use_s3_media == "yes" -%}
The project is built on Django, Django Ninja, PostgreSQL, Redis, Celery,
django-celery-beat, django-celery-results, django-cors-headers,
django-structlog, django-storages, Docker Compose, pytest, Ruff, Ty, and uv.
{%- elif cookiecutter.use_celery == "worker" and cookiecutter.use_cors == "yes" and cookiecutter.use_s3_media == "yes" %}
The project is built on Django, Django Ninja, PostgreSQL, Redis, Celery,
django-celery-results, django-cors-headers, django-structlog, django-storages,
Docker Compose, pytest, Ruff, Ty, and uv.
{%- elif cookiecutter.use_celery == "worker+beat" and cookiecutter.use_s3_media == "yes" %}
The project is built on Django, Django Ninja, PostgreSQL, Redis, Celery,
django-celery-beat, django-celery-results, django-structlog,
django-storages, Docker Compose, pytest, Ruff, Ty, and uv.
{%- elif cookiecutter.use_celery == "worker" and cookiecutter.use_s3_media == "yes" %}
The project is built on Django, Django Ninja, PostgreSQL, Redis, Celery,
django-celery-results, django-structlog, django-storages, Docker Compose,
pytest, Ruff, Ty, and uv.
{%- elif cookiecutter.use_celery == "worker+beat" and cookiecutter.use_cors == "yes" %}
The project is built on Django, Django Ninja, PostgreSQL, Redis, Celery,
django-celery-beat, django-celery-results, django-cors-headers,
django-structlog, Docker Compose, pytest, Ruff, Ty, and uv.
{%- elif cookiecutter.use_celery == "worker" and cookiecutter.use_cors == "yes" %}
The project is built on Django, Django Ninja, PostgreSQL, Redis, Celery,
django-celery-results, django-cors-headers, django-structlog, Docker Compose,
pytest, Ruff, Ty, and uv.
{%- elif cookiecutter.use_celery == "worker+beat" %}
The project is built on Django, Django Ninja, PostgreSQL, Redis, Celery,
django-celery-beat, django-celery-results, django-structlog, Docker Compose,
pytest, Ruff, Ty, and uv.
{%- elif cookiecutter.use_celery == "worker" %}
The project is built on Django, Django Ninja, PostgreSQL, Redis, Celery,
django-celery-results, django-structlog, Docker Compose, pytest, Ruff, Ty,
and uv.
{%- elif cookiecutter.use_cors == "yes" and cookiecutter.use_s3_media == "yes" %}
The project is built on Django, Django Ninja, PostgreSQL, Redis,
django-cors-headers, django-structlog, django-storages, Docker Compose,
pytest, Ruff, Ty, and uv.
{%- elif cookiecutter.use_s3_media == "yes" %}
The project is built on Django, Django Ninja, PostgreSQL, Redis,
django-structlog, django-storages, Docker Compose, pytest, Ruff, Ty, and uv.
{%- elif cookiecutter.use_cors == "yes" %}
The project is built on Django, Django Ninja, PostgreSQL, Redis,
django-cors-headers, django-structlog, Docker Compose, pytest, Ruff, Ty, and
uv.
{%- else %}
The project is built on Django, Django Ninja, PostgreSQL, Redis,
django-structlog, Docker Compose, pytest, Ruff, Ty, and uv.
{%- endif %}

## Architecture

```text
{% if cookiecutter.use_celery != "none" -%}
src/config/          Django settings, URLs, Celery app, ASGI entrypoint
{%- else %}
src/config/          Django settings, URLs, ASGI entrypoint
{%- endif %}
src/apps/core/       shared abstract model bases
src/apps/api/        Django Ninja API, schemas, pagination, request metadata
{%- if cookiecutter.use_example_api == "yes" %}
src/apps/notes/      example notes resource (model, controller, schemas, tests)
{%- endif %}
tests/               unit and integration tests
.docker/             Dockerfile, Compose files, entrypoint scripts
.github/             dependency audit, deployment checks, Docker checks, migration checks, pre-commit, and test workflows
```

Settings use `django-split-settings` with reusable components and environment
overlays:

{% if cookiecutter.use_celery != "none" -%}
- `ci` uses eager Celery tasks and in-memory storage; the database always
  comes from `DATABASE_URL`.
{%- else %}
- `ci` uses in-memory storage; the database always comes from `DATABASE_URL`.
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

- Docker Compose >= 5.3.0 (`pre_start` lifecycle hooks)
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
docker compose -f .docker/compose/dev.yaml --env-file=.env up --build
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
docker compose -f .docker/compose/dev.yaml --env-file=.env exec api python manage.py createsuperuser
```

Stop the stack with:

```shell
docker compose -f .docker/compose/dev.yaml --env-file=.env down
```

## Local Setup

`.env.example` contains the variables needed by the Compose stack. The defaults
target local PostgreSQL and Redis containers:

{%- if cookiecutter.use_s3_media == "yes" %}

- `AWS_STORAGE_BUCKET_NAME` is required in production; optional AWS variables
  are commented.
{%- else %}

{% endif %}
- `AXES_COOLOFF_MINUTES` and `AXES_FAILURE_LIMIT` optionally tune the
  cache-backed failed-login lockout.
- `CACHE_URL` uses Redis database 0.
{%- if cookiecutter.api_throttling == "basic" %}
- `API_THROTTLE_ANON_RATE` and `API_THROTTLE_USER_RATE` optionally tune
  cache-backed public API throttling.
{%- endif %}
{%- if cookiecutter.use_cors == "yes" %}
- `CORS_ALLOWED_ORIGINS` lists browser origins allowed to call the API
  cross-origin.
{%- endif %}
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
production. Set `DEFAULT_FROM_EMAIL` to the sender address for outgoing mail,
and verify that sender domain in Resend. Send
{%- if cookiecutter.use_celery != "none" %}
messages asynchronously with `apps.core.tasks.send_email.delay(...)`.
{%- else %}
messages with `django.core.mail.send_mail(...)`.
{%- endif %}
{%- elif cookiecutter.email_provider == "smtp" %}
Development prints email to the console, tests keep email in memory, and
production sends through your SMTP relay. Set `EMAIL_HOST` in production,
optionally set the other `EMAIL_*` relay values. Set `DEFAULT_FROM_EMAIL` to
the sender address for outgoing mail, and make sure your relay permits that
sender. Send
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
relies on the Compose restart policy. The project ships one example:
`apps.core.tasks.clear_expired_sessions`, scheduled hourly via
`CELERY_BEAT_SCHEDULE`. `DatabaseScheduler` copies code-defined schedule
entries into its database tables on beat startup, after which Django Admin
owns the live schedule.
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
{%- if cookiecutter.use_example_api == "yes" %}

Try the example `notes` resource ({% if cookiecutter.api_auth == "jwt" %}JWT-authenticated{% else %}session-authenticated{% endif %} class-based controller CRUD)
documented at `/api/v1/docs`.
The list endpoint demonstrates filtering, ordering, pagination, and searching
with query parameters such as `?title=planning`, `?ordering=title`, and
`?search=apricot`.
{%- if cookiecutter.api_auth == "jwt" %}
JWT endpoints are available at `/api/v1/token/pair`,
`/api/v1/token/refresh`, `/api/v1/token/verify`, and
`/api/v1/token/blacklist`.
{%- if cookiecutter.use_celery == "worker+beat" %}
Refresh-token rotation blacklists old tokens; the scheduled
`flush-expired-tokens` Celery beat task purges expired blacklist rows daily.
{%- else %}
Refresh-token rotation blacklists old tokens; run
`python manage.py flushexpiredtokens` periodically, for example from host
cron or another scheduler, to keep the `token_blacklist` tables bounded.
{%- endif %}
{%- endif %}
{%- endif %}

API docs and the OpenAPI schema are public in development and staff-only in
production (`API_DOCS_DECORATOR`). The API itself ships unauthenticated: when
you add the first endpoint that needs protection, set a global auth class
(`NinjaAPI(auth=...)`) or per-router auth; see
<https://django-ninja.dev/guides/authentication/>.
{%- if cookiecutter.use_csp == "yes" %}

Content Security Policy headers are enabled through Django's native CSP
middleware. The starter policy blocks inline scripts: Swagger UI is served from
self-hosted static assets, and `unsafe-eval` is retained because the
django-unfold admin theme requires it, while inline styles are still allowed.
{%- endif %}

The versioned (`v1`) and internal OpenAPI schemas are committed under
`docs/openapi/` so API contract changes surface as reviewable diffs, and the
`OpenAPI Schema Export` workflow fails any pull request whose committed
schemas are stale. Regenerate and commit them whenever you change the API, and
point your OpenAPI client generator at these files:

```shell
mkdir -p docs/openapi
uv run python manage.py export_openapi_schema --api=internal --output=docs/openapi/openapi-internal.json
uv run python manage.py export_openapi_schema --api=v1 --output=docs/openapi/openapi-v1.json
```

Use Django Admin:

```shell
open http://localhost:8000/admin/
```

## Production

Start the production stack:

```shell
docker compose -f .docker/compose/prod.yaml --env-file=.env up -d --wait
```

### Deploying releases (recommended)

For release-based deploys, bump `[project] version` in `pyproject.toml`,
commit, tag `v<version>`, and push the tag. Only strict `vX.Y.Z` tags trigger
the release workflow. It runs the full test suite before publishing
`ghcr.io/<owner>/<repo>:v<version>` and refuses tags that do not match the
project version, keeping image tags aligned with Sentry release names.

The production Compose file pulls
`ghcr.io/{{ cookiecutter.github_username | lower }}/{{ cookiecutter.project_slug }}`
while the release workflow pushes to the actual `owner/repo` of the GitHub
repository. These must coincide: the repository should be named
`{{ cookiecutter.project_slug }}` and owned by
`{{ cookiecutter.github_username | lower }}`. If the repository is renamed or
moved to an org, update the three `image:` lines in
`.docker/compose/prod.yaml` to the matching `ghcr.io/<owner>/<repo>` path.

Deploy or roll back with one command from the project root:

```shell
./.docker/scripts/deploy.sh v<version>
```

The script updates `APP_VERSION` in `.env`, pulls the matching image, and
replaces the containers. There is no published `:latest` tag: release deploys
always set an explicit `APP_VERSION`, while an unset `APP_VERSION` means a
locally built unreleased image tagged `unreleased`, never a registry pull.
Rollback is the same command with the previous tag, for example
`./.docker/scripts/deploy.sh v<previous>`. Usually the previous image is still
cached on the host, so the pull is a no-op. Find earlier tags with
`git tag --sort=-v:refname | head` or on the GHCR package page.

Do not deploy releases with `up -d --build`; that builds source on the host
instead of running the published artifact. Rolling back an image does not roll
back the database: the production stack runs migrations before the API starts,
so keep migrations backward-compatible at least one release back. CI enforces
this contract with `lintmigrations` for project apps. If a deliberately
backward-incompatible migration has an approved deploy plan, add
`django_migration_linter.IgnoreMigration()` to that migration's `operations`
list to mark the exception explicitly. Private GHCR packages require
`docker login ghcr.io` on the host with a token that can read packages.

Run management commands against the running production stack through the
wrapper script. The template deliberately ships no registration endpoints, so
mint the first credential with:

```shell
./.docker/scripts/manage.sh createsuperuser
```

Password-based logins are protected by cache-backed django-axes lockout.
Tune `AXES_COOLOFF_MINUTES` and `AXES_FAILURE_LIMIT` in `.env` when the
defaults do not fit the deployment. To clear active lockouts manually, run
`uv run manage.py axes_reset` or the same command through the production
management wrapper.

Production serves Django through ASGI (`config.asgi`) using Gunicorn with
Uvicorn workers. Sync and async Django Ninja operations can coexist; use async
handlers only with async-safe libraries or Django's async ORM APIs.

{% if cookiecutter.use_traefik == "yes" and cookiecutter.traefik_tls == "letsencrypt" -%}
The production stack includes Traefik. Traefik terminates TLS with Let's
Encrypt using `TRAEFIK_ACME_EMAIL` and `TRAEFIK_DOMAIN`, routes only to healthy
API containers, and overwrites client-supplied forwarded headers. The `api`
service publishes no ports, so `FORWARDED_ALLOW_IPS=*` is safe: only services
on the Compose network can reach it. Port 80 serves probes and lets Django
redirect non-probe HTTP requests; port 443 serves normal traffic.

During `docker rollout`, Traefik actively checks `/api/health`, retries short
backend selection races, waits briefly before stopping the old API container,
then delivers SIGTERM: gunicorn stops accepting connections and finishes
in-flight requests for up to `GUNICORN_GRACEFUL_TIMEOUT` seconds while Traefik
has already removed the backend from rotation. Those pieces cover both sides of
replacement: the new backend is not relied on until its HTTP health check
passes, and the old backend keeps serving until gunicorn finishes draining.
{%- elif cookiecutter.use_traefik == "yes" and cookiecutter.traefik_tls == "external" %}
The production stack includes Traefik. Traefik serves TLS from
`.docker/certs/cert.pem` and `.docker/certs/key.pem`, routes only to healthy
API containers, and overwrites client-supplied forwarded headers. The `api`
service publishes no ports, so `FORWARDED_ALLOW_IPS=*` is safe: only services
on the Compose network can reach it. Port 80 serves probes and lets Django
redirect non-probe HTTP requests; port 443 serves normal traffic.

During `docker rollout`, Traefik actively checks `/api/health`, retries short
backend selection races, waits briefly before stopping the old API container,
then delivers SIGTERM: gunicorn stops accepting connections and finishes
in-flight requests for up to `GUNICORN_GRACEFUL_TIMEOUT` seconds while Traefik
has already removed the backend from rotation. Those pieces cover both sides of
replacement: the new backend is not relied on until its HTTP health check
passes, and the old backend keeps serving until gunicorn finishes draining.
{%- else %}
{%- if cookiecutter.behind_proxy == "yes" %}
Bring your own ingress. The production `api` service publishes
`127.0.0.1:8000:8000`; put your proxy on the host in front of that loopback
listener. The proxy must forward `Host` and overwrite client-supplied
`X-Forwarded-Proto` so Django can enforce HTTPS without redirect loops.
{%- else %}
The production `api` service publishes `127.0.0.1:8000:8000` for plain-HTTP
private-network use with no trusted proxy in front. In this mode Django does
not trust `X-Forwarded-Proto`, set HSTS, redirect HTTP to HTTPS, or mark
cookies `Secure`; do not expose this listener directly to the public internet.
{%- endif %}
{%- endif %}

`ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`, and `TRAEFIK_DOMAIN` are pre-filled
from `domain_name` when the project is baked. Bake with the real deployment
hostname so the generated `.env.example` is production-ready, and keep
`127.0.0.1` in `ALLOWED_HOSTS` because the container healthcheck probes over
localhost. Production boot refuses `example.com` in `ALLOWED_HOSTS`.

Before deploying, generate real secrets:

```shell
uv run python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

{% if cookiecutter.postgres == "compose" -%}
Use the generated value for `SECRET_KEY`, and set a strong
`POSTGRES_PASSWORD` and `REDIS_PASSWORD`. Keep `REDIS_PASSWORD` in sync with
the credentials embedded in `CACHE_URL`{% if cookiecutter.use_celery != "none" %} and `CELERY_BROKER_URL`{% endif %}. The production
stack reads the same `.env` file as development, and production boot refuses
`django-insecure-` keys, the shipped slug-default database password, or the
shipped slug-default Redis password.

The bundled Postgres has no backup mechanism of its own: it is a single
named Docker volume, and losing the host or the volume loses the data.
`.docker/scripts/postgres-backup.sh` runs `pg_dump` in custom format
against the running `postgres` service and prunes old dumps. Schedule it
with host cron, for example:

```shell
0 3 * * * cd /path/to/{{ cookiecutter.project_slug }} && ./.docker/scripts/postgres-backup.sh backup /var/backups/{{ cookiecutter.project_slug }}
```

Copy dumps off-host; a dump left on the same disk as the database does
not survive host loss.

To restore, stop the `api` service and any worker services first, then
run:

```shell
./.docker/scripts/postgres-backup.sh restore /var/backups/<project>/<stamp>.dump
```

The restore script refuses to run while `api` or worker services are still
running. Pass `--force` only for non-Compose restores or emergency contexts
where you have separately quiesced all writers.

Rehearse restores periodically so the procedure is proven before it is
needed under pressure. Use
`./.docker/scripts/postgres-backup.sh verify <dump>` to restore a dump into
a throwaway container, never the live database; run it on a schedule that
matches your risk tolerance. This is snapshot-based backup only: anything
written after the last dump is lost, and there is no point-in-time
recovery here. If your recovery point objective is measured in minutes
rather than hours, move to managed Postgres (`postgres=external`)
instead, where the provider owns backups, high availability, and
upgrades.
{%- else %}
Use the generated value for `SECRET_KEY`. The production stack reads the same
`.env` file as development, and production boot refuses `django-insecure-`
keys.
{%- if cookiecutter.redis == "compose" %}
Set a strong `REDIS_PASSWORD` too. Keep it in sync with the credentials
embedded in `CACHE_URL`{% if cookiecutter.use_celery != "none" %} and `CELERY_BROKER_URL`{% endif %}; production boot refuses the
shipped slug-default Redis password.
{%- endif %}

Set `DATABASE_URL` to the external PostgreSQL-compatible endpoint and append
`?sslmode=require`, unless your provider requires stricter settings such as
`verify-full` with a CA bundle. The `POSTGRES_*` variables only feed the local
development Compose stack and are ignored by production. Your provider owns
backups, high availability, and upgrades.
{%- endif %}
{% if cookiecutter.use_s3_media == "no" %}
The bundled media volume has no backup mechanism of its own. Use
`.docker/scripts/media-backup.sh` to archive files from the Compose media
volume through a throwaway tar container and prune old archives. Schedule it
with host cron, for example:

```shell
0 4 * * * cd /path/to/{{ cookiecutter.project_slug }} && ./.docker/scripts/media-backup.sh backup /var/backups/{{ cookiecutter.project_slug }}-media
```

Copy archives off-host; an archive left on the same disk as the media volume
does not survive host loss. To restore, stop the `api` service and any worker
services first, then run:

```shell
./.docker/scripts/media-backup.sh restore /var/backups/<project>-media/<stamp>.tar.gz
```

The restore script refuses to run while `api` or worker services are still
running. Pass `--force` only for non-Compose restores or emergency contexts
where you have separately quiesced all writers.

Restores extract files over the existing media tree and do not remove files
created after the backup. Rehearse restores periodically, and use
`./.docker/scripts/media-backup.sh verify <archive>` to check that an archive
can be listed before relying on it.
{%- endif %}
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

### Building on the host

Use this flow before the first published release, when GHCR is unreachable, or
when the project deliberately does not publish images.

{% if cookiecutter.use_traefik == "yes" %}

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
{% else %}
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

For either deploy flow, keep database changes compatible across the handoff.

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
`CONN_MAX_AGE=0` when running behind PgBouncer in transaction mode{% if cookiecutter.postgres == "external" -%}
, RDS Proxy, Neon's pooled endpoint, or another transaction-mode pooler
{%- endif %}.

Internal probes are unversioned; business endpoints live under `/api/v1/`.
To introduce v2, create a
`v2_api = NinjaAPI(urls_namespace="v2", version="2.0.0")` instance and mount
it at `path("api/v2/", v2_api.urls)`.

{% if cookiecutter.redis == "compose" and cookiecutter.use_celery != "none" -%}
Redis runs append-only for broker durability. Cache and broker share one Redis
instance on databases 0 and 1. Memory is bounded by `REDIS_MAXMEMORY` (default
256mb); under memory pressure, Redis's default `noeviction` policy rejects
writes instead of evicting keys, which surfaces as cache write errors and
blocked task enqueues rather than silent eviction or host OOM. Raise the value
or split Redis instances if cache volume grows.
{%- elif cookiecutter.redis == "compose" %}
Redis runs append-only for cache durability. Memory is bounded by
`REDIS_MAXMEMORY` (default 256mb); under memory pressure, Redis's default
`noeviction` policy rejects writes instead of evicting keys, which surfaces as
cache write errors rather than silent eviction or host OOM. Raise the value or
split instances as cache volume grows.
{%- elif cookiecutter.use_celery != "none" %}
Set `CACHE_URL=rediss://:<password>@<host>:<port>/0` and
`CELERY_BROKER_URL=rediss://:<password>@<host>:<port>/1?ssl_cert_reqs=required`
to your Redis-compatible provider's TLS endpoint. Celery requires the
`ssl_cert_reqs` parameter on `rediss://` broker URLs. The broker database must
use a `noeviction` policy at the provider or task enqueues can fail under
memory pressure. Keep cache and broker on separate databases, or separate
instances, as with the bundled setup.
{%- else %}
Set `CACHE_URL=rediss://:<password>@<host>:<port>/0` to your
Redis-compatible provider's TLS endpoint. Use a `noeviction` policy at the
provider so cache writes fail explicitly under memory pressure.
{%- endif %}

Container logs are capped at roughly 50 MB per container (`json-file` driver,
5 files of 10 MB) via the compose logging policy, so a chatty service cannot
fill the host disk. Per-service memory limits are deliberately not set in the
compose file — a wrong default can OOM-kill a legitimate workload — but you
can add a kernel-enforced cap per host by uncommenting a block like this under
the service you want to bound:

```yaml
# deploy:
#   resources:
#     limits:
#       memory: 512M
```

Size it to your host and workload before enabling it.

The admin at `/admin/` is exposed wherever the API is routed. Restrict it at
the proxy with an IP allowlist or route only `/api/` publicly.

### Metrics

The template ships no metrics endpoint or exporter. Sentry, when enabled,
already captures error rates and sampled request traces and latency, which
covers most single-operator needs. When you want RED/latency dashboards or
Prometheus-ecosystem alerting, add one of these at the project level:

- Scrape model: add
  [`django-prometheus`](https://github.com/korfuri/django-prometheus), which
  exposes a `/metrics` endpoint. Do NOT expose `/metrics` on the public
  ingress (the bundled Traefik router, or whatever proxy fronts the API);
  restrict it to an internal-only listener or an IP-allowlisted route, the
  same way `/admin/` is protected above.
- Push model: add
  [`opentelemetry-instrumentation-django`](https://opentelemetry.io/docs/languages/python/)
  with an OTLP exporter. It adds no scrape surface but needs a collector
  endpoint to push to.

## Testing

Run the test suite:

```shell
docker compose -f .docker/compose/dev.yaml --env-file=.env up -d --wait postgres
uv run pytest
```

Tests connect to `localhost:5432` by default and honor a `DATABASE_URL`
environment override; pytest-xdist creates per-worker `test_*_gwN` databases.

{% if cookiecutter.use_celery != "none" -%}
The suite uses CI settings, real PostgreSQL, in-memory storage, eager Celery
tasks, and enforces 100% coverage through `pytest-cov`.
{%- else %}
The suite uses CI settings, real PostgreSQL, in-memory storage, and enforces
100% coverage through `pytest-cov`.
{%- endif %}

[django-zeal](https://pypi.org/project/django-zeal/) runs in dev requests and
in every test via an autouse fixture, raising `NPlusOneError` the moment code
fetches a related object or field without `select_related`/`prefetch_related`.
Fix a failure by adding the missing `select_related`/`prefetch_related`, or,
for a deliberately singular access pattern, add a commented entry to
`ZEAL_ALLOWLIST` in the matching settings overlay.

Run repository checks:

```shell
uv run pre-commit run --all-files
```

Useful focused checks:

```shell
uv run pre-commit run ruff-check --all-files
uv run pre-commit run ty --all-files
```

CI runs tests, deploy checks, pre-commit, dependency audit, prod and dev Docker
image builds, and a production-stack boot smoke that probes liveness and
readiness through GitHub Actions. The smoke job always merges
`.docker/compose/ci-services.yaml` over `prod.yaml`; that overlay supplies
CI-only Postgres and Redis stand-ins for external-backend bakes and is never
part of production deploys.

## Verification

Freshly generated projects are expected to pass:

```shell
docker compose -f .docker/compose/dev.yaml --env-file=.env up -d --wait postgres
uv run pytest
uv run pre-commit run --all-files
docker compose -f .docker/compose/dev.yaml --env-file=.env up -d --build --wait
curl -fsS http://localhost:8000/api/ready
docker compose -f .docker/compose/dev.yaml --env-file=.env down -v
```

## License

MIT. See `LICENSE`.
