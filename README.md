# django-api-template

A Cookiecutter template for a modern Django Ninja API service.

## What You Get

- Dependabot for Compose, Docker, GitHub Actions, pre-commit hooks, and uv
- Django 6 and Django Ninja in a `src/` layout
- Dockerfile and Docker Compose definitions
- `django-split-settings` with `ci`, `dev`, and `prod` overlays
- Optional Celery (worker, or worker and beat), chosen at bake time
- Optional email provider: Resend API, SMTP, or none
- Optional S3-compatible media storage
- Optional Sentry integration
- Optional Traefik ingress with Let's Encrypt or operator-provided TLS
- PostgreSQL for local and production Compose stacks
- pytest with 100% coverage, Hypothesis, and Schemathesis
- actionlint, gitlint, markdownlint, Ruff, Ty, uv-audit, yamlfmt, yamllint, and
  other pre-commit checks
- uv-managed Python 3.14 dependencies
- Vendored `.agents/` skills and `AGENTS.md` guidance

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
| `author_name` | `Stefano Fusai` | Package author and maintainer name. Must not contain `"`, `\`, or newlines. |
| `author_email` | `stefanofusai@gmail.com` | Package author and maintainer email. |
| `github_username` | `stefanofusai` | Badge and Dependabot assignee username. |
| `use_celery` | `worker+beat` | Celery services to include: `worker+beat`, `worker`, or `none`. |
| `email_provider` | `resend` | Production email provider: `resend`, `smtp`, or `none`. |
| `use_sentry` | `yes` | Include the production Sentry integration. |
| `use_s3_media` | `yes` | Store production media on S3-compatible object storage. |
| `use_traefik` | `yes` | Include the bundled Traefik reverse proxy. |
| `traefik_tls` | `letsencrypt` | Use `external` to serve an operator-provided PEM pair instead of running ACME; ignored when `use_traefik=no`. |

`project_slug` must start with a lowercase letter, contain only lowercase
letters, digits, and single hyphen separators, and be 50 characters or fewer.
The feature-knob defaults reproduce the historical full-stack output.

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
docker compose -f .docker/compose/dev.yaml up --build
curl -fsS http://localhost:8000/api/ready
docker compose -f .docker/compose/dev.yaml down -v
```
