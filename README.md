# django-api-template

[![CI](https://img.shields.io/badge/CI-GitHub%20Actions-blue)](.github/workflows/ci.yaml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

A Cookiecutter template for a production-minded Django 6 API service with
Django Ninja, typed settings, reproducible uv-managed dependencies, Docker
Compose deployment defaults, and CI gates for the baked project.

## What You Get

- `/api/v1/` business API versioning plus unversioned health and readiness
  probes
- 100% pytest coverage gate with factories and Schemathesis property-based
  contract tests
- actionlint, gitlint, markdownlint, Ruff, Ty, uv-audit, yamlfmt, yamllint,
  and other pre-commit checks
- Custom user model from the initial bake
- Dependabot for Compose, Docker, GitHub Actions, pre-commit hooks, and uv
- Dockerfile and Docker Compose definitions for development and production
- `django-split-settings` with `ci`, `dev`, and `prod` overlays
- Optional Celery worker and beat services, chosen at bake time
- Optional email stack: Resend API, SMTP, or no production email provider
- Optional S3-compatible media storage
- Optional Sentry integration
- Optional Traefik ingress with Let's Encrypt or operator-provided TLS
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
- PostgreSQL is the database target; SQLite is used only by the CI test
  overlay.
- Production Sentry is boot-required when enabled, so broken observability
  fails before traffic reaches the app.
- The template deliberately ships no CORS or throttling defaults; add them
  when a real consumer and policy exist.
- The `src/` layout keeps import paths honest and avoids accidentally
  importing from the repository root.
- uv exact pins and generated lockfiles make fresh bakes reproducible.
- Tests measure all of `src/` and fail below 100% coverage.

## Requirements

- Docker Compose >= 5.3.0 for `pre_start` lifecycle hooks
- Python 3.14
- [uv](https://docs.astral.sh/uv/)

## Usage

```shell
uvx cookiecutter gh:stefanofusai/django-api-template
```

## Variables

| Name | Default | Description |
| --- | --- | --- |
| `project_name` | `My Project` | Human-readable project name. |
| `project_slug` | `my-project` | Repository and package distribution name, derived from `project_name` unless set explicitly. |
| `description` | `A Django Ninja API service.` | Generated README and package description. Must not contain `"`, `\`, or newlines. |
| `author_name` | `John Doe` | Package author and maintainer name. Must not contain `"`, `\`, or newlines. |
| `author_email` | `john.doe@example.com` | Package author and maintainer email. |
| `github_username` | `johndoe` | Badge and Dependabot assignee username. |
| `domain_name` | `example.com` | Deployment domain pre-filled into `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`, and `TRAEFIK_DOMAIN`. |
| `email_provider` | `resend` | Production email provider: `resend`, `smtp`, or `none`. |
| `postgres` | `compose` | Run production Postgres as a bundled Compose service, or point `DATABASE_URL` at an external/managed Postgres-compatible database. |
| `redis` | `compose` | Run production Redis as a bundled Compose service, or point `CACHE_URL` and `CELERY_BROKER_URL` at external Redis-protocol providers. |
| `traefik_tls` | `letsencrypt` | Use `external` to serve an operator-provided PEM pair instead of running ACME; ignored when `use_traefik=no`. |
| `use_celery` | `worker+beat` | Celery services to include: `worker+beat`, `worker`, or `none`. |
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
- Set `AWS_STORAGE_BUCKET_NAME` when `use_s3_media=yes`.
- Set `RESEND_API_KEY` when `email_provider=resend`, or `EMAIL_HOST` when
  `email_provider=smtp`.
- Set `SENTRY_DSN` when `use_sentry=yes`.
- Set `TRAEFIK_ACME_EMAIL` when `use_traefik=yes` and
  `traefik_tls=letsencrypt`.
- Review `DATABASE_URL`, `CACHE_URL`, and `CELERY_BROKER_URL` when baking with
  external Postgres or Redis.
- Bake with the real `domain_name` so `ALLOWED_HOSTS`,
  `CSRF_TRUSTED_ORIGINS`, and `TRAEFIK_DOMAIN` are pre-filled.

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
git add -A
git commit -m "feat: initial project scaffold"
```

## Verification

Freshly baked projects are expected to pass:

```shell
uv run pytest
uv run pre-commit run --all-files
docker compose -f .docker/compose/dev.yaml up -d --build --wait
curl -fsS http://localhost:8000/api/ready
docker compose -f .docker/compose/dev.yaml down -v
```

## License

MIT.
