# django-api-template

[![CI](https://img.shields.io/badge/CI-GitHub%20Actions-blue)](.github/workflows/ci.yaml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

A Cookiecutter template for a production-minded Django 6 API service with
Django Ninja, typed settings, reproducible uv-managed dependencies, Docker
Compose deployment defaults, and CI gates for the baked project.

## What You Get

- `/api/v1/` business API versioning plus unversioned health and readiness
  probes
- Optional cache-backed throttling for public API routes
- 100% pytest coverage gate with factories and Schemathesis property-based
  contract tests
- actionlint, gitleaks, gitlint, markdownlint, Ruff, shellcheck, Ty, uv-audit, yamlfmt,
  yamllint, and other pre-commit checks
- Custom user model from the initial bake
- Dependabot for Compose, Docker, GitHub Actions, pre-commit hooks, and uv
- Dockerfile and Docker Compose definitions for development and production
- `django-split-settings` with `ci`, `dev`, and `prod` overlays
- OpenAPI schema export command with committed `docs/openapi/` schemas and a
  CI drift gate, ready for client generation
- Optional Celery worker and beat services, chosen at bake time
- Optional CORS support for explicit browser origins
- Optional Django native Content Security Policy for browser-rendered surfaces
- Optional email stack: Resend API, SMTP, or no production email provider
- Optional example `notes` resource demonstrating the model-to-tests vertical
  slice
- Optional S3-compatible media storage with a provider-neutral recovery contract
- Optional Sentry integration
- Optional Traefik ingress with Let's Encrypt or operator-provided TLS
- `pg_dump` backup script and restore runbook for the bundled Postgres
- PostgreSQL and Redis as bundled Compose services or external production
  services
- Standardized production deploy path with docker-rollout when Traefik is
  enabled
- uv-managed Python 3.14 dependencies
- Vendored `.agents/` skills and `AGENTS.md` guidance

## Design Decisions

- API versioning is explicit: internal probes stay under `/api/`, while
  business endpoints start at `/api/v1/`.
- Celery uses Redis and stores results only for tasks that opt in, keeping the
  default result backend quiet.
- Custom user model ships from day one because changing it later is one of
  Django's expensive irreversible decisions.
- Django Ninja is the API layer because it gives typed handlers and OpenAPI
  output with little framework overhead.
- `django-split-settings` keeps settings split by concern, with small
  environment overlays for `ci`, `dev`, and `prod`.
- Docker Compose is the deployment contract; production can bundle Traefik,
  PostgreSQL, and Redis or point at external backing services.
- Liveness (`/api/health`) and readiness (`/api/ready`) are separate so
  container restarts and load-balancer routing can make different decisions.
- PostgreSQL is the database target everywhere, including tests: the suite runs
  against a real Postgres so migrations and engine semantics are exercised.
- Production Sentry is boot-required when enabled, so broken observability
  fails before traffic reaches the app.
- Metrics are a project-level add-on, not a template knob: Sentry already
  covers error rates and sampled latency, and a scraped `/metrics` endpoint
  would add an unauthenticated attack surface plus a full knob lifecycle to
  maintain, which is not worth it for single-operator deployments. The
  generated README documents the django-prometheus and OpenTelemetry recipes.
- CORS is opt-in and requires explicit allowed browser origins; throttling is
  deliberately not enabled by default.
- The `src/` layout keeps import paths honest and avoids accidentally
  importing from the repository root.
- uv exact pins and generated lockfiles make fresh bakes reproducible.
- Tests measure all of `src/` and fail below 100% coverage.

## Requirements

- Docker Compose >= 5.3.0 for `pre_start` lifecycle hooks
- Python 3.14
- [uv 0.11.19](https://docs.astral.sh/uv/)

## Usage

```shell
uvx --from=cookiecutter==2.7.1 cookiecutter gh:stefanofusai/django-api-template
```

## Variables

| Name | Default | Description |
| --- | --- | --- |
| `project_name` | `My Project` | Human-readable project name. |
| `project_slug` | `my-project` | Repository and package distribution name, derived from `project_name` unless set explicitly. |
| `description` | `A Django Ninja API service.` | Generated README and package description. Must not contain `"`, `\`, or newlines. |
| `author_name` | `John Doe` | Package author and maintainer name. Must not contain `"`, `\`, or newlines. |
| `author_email` | `john.doe@example.com` | Package author and maintainer email. |
| `github_username` | `johndoe` | GitHub owner (user or org) used for Dependabot assignees and the GHCR image path. |
| `domain_name` | `example.com` | Deployment domain pre-filled into `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`, and `TRAEFIK_DOMAIN`. |
| `api_auth` | `session` | Authentication used by the example notes API: `session` (Django session auth with CSRF) or `jwt` (JWT access and refresh tokens via `django-ninja-jwt`); only takes effect when `use_example_api=yes`. |
| `api_throttling` | `none` | Public API throttling: `none` disables throttling, `basic` enables cache-backed fixed-window throttling. |
| `behind_proxy` | `yes` | Trust an upstream TLS-terminating proxy's `X-Forwarded-Proto`; use `no` only for plain-HTTP private-network production. |
| `email_provider` | `resend` | Production email provider: `resend`, `smtp`, or `none`. |
| `postgres` | `compose` | Run production Postgres as a bundled Compose service, or point `DATABASE_URL` at an external/managed Postgres-compatible database. |
| `redis` | `compose` | Run production Redis as a bundled Compose service, or point `CACHE_URL` and `CELERY_BROKER_URL` at external Redis-protocol providers. |
| `traefik_tls` | `letsencrypt` | Use `external` to serve an operator-provided PEM pair instead of running ACME; ignored when `use_traefik=no`. |
| `use_celery` | `worker+beat` | Celery services to include: `worker+beat`, `worker`, or `none`. |
| `use_cors` | `no` | Enable explicit browser origins with `django-cors-headers` and `CORS_ALLOWED_ORIGINS`. |
| `use_csp` | `no` | Enable Django native CSP headers: `script-src` blocks inline scripts (self-hosted Swagger UI, `unsafe-eval` retained for the admin theme); inline styles are still allowed. |
| `use_example_api` | `no` | Include the example `notes` model, router, and tests demonstrating the full API pattern. |
| `use_s3_media` | `yes` | Store production media on S3-compatible object storage. |
| `use_sentry` | `yes` | Include the production Sentry integration. |
| `use_traefik` | `yes` | Include the bundled Traefik reverse proxy. |

`project_slug` must start with a lowercase letter, contain only lowercase
letters, digits, and single hyphen separators, and be 50 characters or fewer.
The feature-knob defaults reproduce the historical full-stack output.
`domain_name` must be a bare lowercase hostname with at least one dot.

## Required Configuration

After baking, copy `.env.example` to `.env`:

```shell
cp .env.example .env
```

Before production deploy:

- Replace `SECRET_KEY` with a securely generated value.
- Set `CORS_ALLOWED_ORIGINS` when `use_cors=yes`.
- Set `AWS_STORAGE_BUCKET_NAME` when `use_s3_media=yes`.
- Set `RESEND_API_KEY` when `email_provider=resend`, or `EMAIL_HOST` when
  `email_provider=smtp`.
- Set `SENTRY_DSN` when `use_sentry=yes`.
- Set `TRAEFIK_ACME_EMAIL` when `use_traefik=yes` and
  `traefik_tls=letsencrypt`.
- Review `DATABASE_URL`, `CACHE_URL`, and `CELERY_BROKER_URL` when baking with
  external Postgres or Redis.
- Bake with the real `domain_name` so `ALLOWED_HOSTS`,
  `CSRF_TRUSTED_ORIGINS`, and `TRAEFIK_DOMAIN` are pre-filled; production boot
  refuses `example.com` in `ALLOWED_HOSTS`.

See the generated `.env.example` comments and the generated README's
Production section for the full deployment checklist.

## Post-Generation

The post-generation hook initializes a Git repository and runs `uv lock` when uv
is available. `uv.lock` is generated in the baked project instead of stored in
the template because it embeds the project name.

After generation:

```shell
uv sync --locked
cp .env.example .env
uv run pre-commit install --install-hooks
mkdir -p docs/openapi
uv run python manage.py export_openapi_schema --api=internal --output=docs/openapi/openapi-internal.json
uv run python manage.py export_openapi_schema --api=v1 --output=docs/openapi/openapi-v1.json
git add -A
git commit -m "feat: initial project scaffold"
```

## Verification

Run the complete bake verification with one locked command:

```shell
uv run --locked python scripts/verify_bake.py
```

Freshly baked projects are expected to pass:

```shell
docker compose -f .docker/compose/dev.yaml --env-file=.env up -d --wait postgres
uv run pytest
uv run pre-commit run --all-files
docker compose -f .docker/compose/dev.yaml --env-file=.env up -d --build --wait
curl -fsS http://localhost:8000/api/ready
docker compose -f .docker/compose/dev.yaml --env-file=.env down -v
```

## License

MIT.
