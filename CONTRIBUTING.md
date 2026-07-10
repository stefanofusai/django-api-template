# Contributing

This repository is a Cookiecutter template. Most project files live under the
literal `{{cookiecutter.project_slug}}/` directory and are rendered into a
generated Django application.

## Development Loop

Edit the template, then bake a project and run checks inside the bake:

```shell
uv sync --locked
uv run --locked cookiecutter . -o /tmp/bake --no-input
cd /tmp/bake/my-project
cp .env.example .env
docker compose -f .docker/compose/dev.yaml --env-file=.env up -d --wait postgres
uv run pytest
uv run pre-commit run --all-files
```

Tests connect to the dev-compose Postgres on `localhost:5432` and honor a
`DATABASE_URL` override.

For template-level changes, also run the root pre-commit hooks:

```shell
uv run --locked pre-commit run --all-files
```

CI bakes the template on every pull request, runs the baked test suite and
pre-commit hooks, validates invalid cookiecutter inputs, and builds the Docker
image.

## Commits

Use conventional commit subjects, for example:

```text
docs: clarify production configuration
```

Keep generated-project dependency files consistent when changing template
dependencies.
