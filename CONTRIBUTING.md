# Contributing

This repository is a Cookiecutter template. Most project files live under the
literal `{{cookiecutter.project_slug}}/` directory and are rendered into a
generated Django application.

## Development Loop

Edit the template, then run the locked verifier:

```shell
uv sync --locked
uv run --locked python scripts/verify_bake.py
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
