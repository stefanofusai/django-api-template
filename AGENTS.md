# AGENTS.md

## Command Workflow

- If the `rtk` CLI is available, prefix shell commands with `rtk`
  (token-optimizing proxy); otherwise run commands directly.
- Put short flags before long flags in shell commands, alphabetize short flags
  and long flags within their groups, and write long flags with values using
  `--flag=value`.
- Use the fff MCP tools for file search operations when available; otherwise
  use `rg` or `rg --files`.
- Do not commit unless explicitly asked.
- Preserve existing uncommitted work. Never revert user changes unless
  explicitly asked.
- Keep generated-project dependency files consistent when editing template
  dependencies: `{{cookiecutter.project_slug}}/pyproject.toml` changes normally
  require regenerating or updating the baked `uv.lock` after cookiecutter
  renders the project.

## Project Context

- This repository is a Cookiecutter template for a Python 3.14 Django 6 API
  service using Django Ninja, Celery, django-structlog, django-storages, pytest,
  Ruff, Ty, uv, Docker, and Compose.
- Root-level files control the template itself: `cookiecutter.json`, `hooks/`,
  `.github/`, `plans/`, and `README.md`.
- Files under `{{cookiecutter.project_slug}}/` are rendered into the generated
  project. Keep Jinja expressions valid and avoid changes that only work before
  rendering.
- `.github/workflows/*` and `.agents/*` are copied without rendering. Do not add
  Cookiecutter variables to those paths unless `_copy_without_render` is changed
  deliberately.
- The generated project's `AGENTS.md` should stay focused on the baked Django
  application. Root guidance belongs in this file.
- Do not add root-project instructions that assume the root repository is the
  generated Django app.

## Template Variables

- Keep `project_slug` derived from `project_name` unless there is a clear reason
  to change `cookiecutter.json`.
- Preserve hook validation for values written into rendered files:
  `author_name` and `description` must not contain double quotes, backslashes, or
  newlines; `author_email` must be an email address; `github_username` must be a
  valid GitHub username.
- `project_slug` must start with a lowercase letter, contain only lowercase
  letters, digits, and single hyphen separators, and stay 50 characters or
  fewer.

## Style

- Follow Ruff formatting and linting for Python files that are valid before
  rendering.
- Remember that `hooks/pre_gen_project.py` contains Cookiecutter substitutions
  and is not plain Python until rendered.
- Avoid trailing commas on newlines unless Ruff adds them to keep long lines
  valid/readable.
- Never add `from __future__ import annotations`.
- Prefer clear, explicit code over clever compression.
- Use extended YAML block style instead of compact flow style, for example
  `branches:` followed by `- main` instead of `branches: [main]`.
- Order unordered list items alphabetically when dependency order does not
  matter. This includes Markdown inventory bullets, YAML lists of pre-commit
  hook ids, Docker Compose volume entries, GitHub Actions matrix entries,
  Dependabot update entries, environment-variable documentation, and command
  argument lists. For example, put `check-dependabot` before
  `check-github-workflows`, `CACHE_URL` before `DATABASE_URL`,
  `/app/media` before `/app/src`, and `docker` before `github-actions`.
- Put blank lines around control-flow blocks and between their branches. Apply
  this to `if`/`elif`/`else`, `try`/`except`/`else`/`finally`, `for`, `while`,
  `with` context managers, and other multi-line control blocks.
- At module scope, order declaration blocks as call-style markers such as
  `pytestmark`, then constants, then variables. Separate each block with a blank
  line, and keep constants blocks prefixed and suffixed by a blank line unless
  they are at the start or end of a file.
- Order constants alphabetically within each file when dependency order does not
  matter.
- Order `pyproject.toml` subsections alphabetically when dependency order does
  not matter; for example, place `[tool.coverage.*]` before
  `[tool.django-stubs]`.
- Order public classes, public functions, and methods alphabetically within
  their group when dependency order does not matter.
- Keep classes and functions grouped separately.
- Put private helper utilities at the bottom of the file under a `# Utils`
  heading, alphabetized there.
- Respect semantic ordering constraints, such as Django model fields,
  inheritance dependencies, decorators, framework-required signatures,
  Cookiecutter rendering behavior, and import-time behavior.

## Template Maintenance

- Keep root `README.md` aligned with `cookiecutter.json`, hooks, and the
  generated project surface.
- Keep generated-project documentation aligned with files under
  `{{cookiecutter.project_slug}}/`.
- Keep operational constants fixed in generated code unless there is a real
  deployment need to configure them.
- Add environment variables only for secrets, deployment topology, or resource
  sizing.
- Do not add empty optional values to `.env.example`; document optional AWS
  variables as commented examples.
- Keep Docker images pinned, not floating.
- Format complex shell commands over multiple lines with backslashes.
- For curl healthchecks, use compact short flags in the established style, such
  as `-fsS -o /dev/null`.

## Verification

- Run relevant root checks before completion:
  - `pre-commit run --all-files`
- For template behavior changes, bake a project in a temporary output directory
  and run the generated-project checks that match the change.
- Freshly baked projects are expected to pass:
  - `uv run pytest`
  - `uv run pre-commit run --all-files`
  - `docker compose -f .docker/compose/dev.yaml up --build`
  - `curl -fsS http://localhost:8000/api/ready`
  - `docker compose -f .docker/compose/dev.yaml down -v`
- Prefix these with `rtk` when it is available.
