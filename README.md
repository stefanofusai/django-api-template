# django-api-template

A Cookiecutter template for a modern Django Ninja API service.

## What You Get

- Celery and Redis included by default
- Dependabot for Compose, Docker, GitHub Actions, pre-commit hooks, and uv
- Django 6 and Django Ninja in a `src/` layout
- Dockerfile and Docker Compose definitions
- `django-split-settings` with `ci`, `dev`, and `prod` overlays
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
| `project_slug` | `my-project` | Repository and package distribution name. |
| `description` | `A Django Ninja API service.` | Generated README and package description. |
| `author_name` | `Stefano Fusai` | Package author and maintainer name. |
| `author_email` | `stefanofusai@gmail.com` | Package author and maintainer email. |
| `github_username` | `stefanofusai` | Badge and Dependabot assignee username. |

`project_slug` must start with a lowercase letter and contain only lowercase
letters, digits, and single hyphen separators.

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
