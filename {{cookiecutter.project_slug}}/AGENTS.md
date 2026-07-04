# AGENTS.md

## Command Workflow

- Always prefix shell commands with `rtk`.
- Put short flags before long flags in shell commands, alphabetize short flags
  and long flags within their groups, and write long flags with values using
  `--flag=value`.
- Use `rg` or `rg --files` for searching.
- Use `uv run ...` for Python tooling, tests, pre-commit, Django, and Celery commands.
- Do not commit unless explicitly asked.
- Preserve existing uncommitted work. Never revert user changes unless explicitly asked.
- Keep `pyproject.toml` and `uv.lock` in sync when dependencies or dependency groups change.
- If sandboxed `uv`, `pytest`, or pre-commit commands fail because they need cache access, rerun with escalation rather than changing project state to work around it.

## Project Context

- This is a Python 3.14 Django 6 project using Django Ninja, Celery, django-structlog, django-storages, pytest, Ruff, Ty, uv, Docker, and Compose.
- Settings use `django-split-settings` with responsibility-based components and environment overlays. Keep this structure.
- Environment overlays should mutate only environment-specific differences.
- Do not add `django-configurations`, settings builder functions, wildcard imports, or tests that only assert configuration values.
- Pin dependencies in `pyproject.toml` to exact versions, and use the latest intended release when adding or updating a dependency.

## Style

- Follow Ruff formatting and linting. Ruff selects `ALL`, so keep changes explicit and tidy.
- Avoid trailing commas on newlines unless Ruff adds them to keep long lines valid/readable.
- Never add `from __future__ import annotations`.
- Avoid `Protocol` or other speculative abstractions unless multiple real implementations already need them.
- Prefer clear, explicit code over clever compression.
- Use extended YAML block style instead of compact flow style, for example
  `branches:` followed by `- main` instead of `branches: [main]`.
- Put blank lines around control-flow blocks and between their branches. Apply this to `if`/`elif`/`else`, `try`/`except`/`else`/`finally`, `for`, `while`, `with` context managers, and other multi-line control blocks.
- At module scope, order declaration blocks as call-style markers such as
  `pytestmark`, then constants, then variables. Separate each block with a
  blank line, and keep constants blocks prefixed and suffixed by a blank line
  unless they are at the start or end of a file.
- Order constants alphabetically within each file when dependency order does not matter.
- Order `pyproject.toml` subsections alphabetically when dependency order does not matter; for example, place `[tool.coverage.*]` before `[tool.django-stubs]`.
- Order public classes, public functions, and methods alphabetically within their group when dependency order does not matter.
- Keep classes and functions grouped separately.
- Put private helper utilities at the bottom of the file under a `# Utils` heading, alphabetized there.
- Respect semantic ordering constraints, such as Django model fields, inheritance dependencies, decorators, framework-required signatures, and import-time behavior.
- Alphabetize parameters in tests, helper functions, and Django Ninja endpoints when framework conventions do not require a leading parameter such as `self`, `request`, `sender`, or Django admin's `request, queryset`.

## Django And Configuration

- Respect `django-extra-checks`: models need `__str__`, `Meta.ordering`, admin registration, gettext verbose/help text, explicit FK `related_name` and `db_index`, choice constraints, and `UniqueConstraint` instead of `unique_together`.
- Add environment variables only for secrets, deployment topology, or resource sizing.
- Do not add empty optional values to `.env.example`; document optional AWS variables as commented examples.
- Keep operational constants fixed in code unless there is a real deployment need to configure them.
- Keep Django Ninja routers resource-oriented. Mount resource routers at their resource prefix and keep route-local paths relative.

## Testing

- The full suite enforces 100% coverage. Focused test commands are useful, but final verification should include `rtk uv run pytest`.
- Run relevant checks before completion:
  - `rtk uv run pre-commit run ruff-check --all-files`
  - `rtk uv run pre-commit run ty --all-files`
  - `rtk uv run pytest`
  - `rtk uv run pre-commit run --all-files` for broad changes
- Register factories in `tests/factories.py` when adding concrete models.
- Use pytest-factoryboy model fixtures directly and prefer attribute
  parametrization for factory-backed model setup.
- Avoid direct `Model.objects.create(...)` and direct Django model construction in tests unless the test specifically needs an invalid unsaved object; use factory `.build(...)` for those invalid cases.
- Use Faker/factory values for incidental names, URLs, UUIDs, and response metadata.
- Keep fixed literals only when they are the behavior under test.
- Test names must follow `test_<subject>_<expected_behavior>_when_<condition>`, using `for_<scenario>` when it reads better.
- Keep test functions alphabetized within each file.

## Pre-Commit And Type Checking

- The official Astral Ty hook is expected: `astral-sh/ty-pre-commit`, hook id `ty`, with `--locked` and `--no-python-downloads`.
- `.agents/` should stay excluded both in `.pre-commit-config.yaml` and in `[tool.ty.src] exclude`.
- Remember that Ty checks the full project, not only staged files.
- If Ty reports `uv.lock` is stale, update and stage `uv.lock` with the related `pyproject.toml` change.

## Docker And Runtime

- Keep Docker images pinned, not floating.
- Long-running services should use restart policies; one-shot migration services should remain `restart: no`.
- Use `gunicorn.sh` for the web process and `GUNICORN_WORKERS` for worker count.
- Do not reintroduce `WEB_CONCURRENCY` for Gunicorn workers.
- Keep Gunicorn's control socket disabled unless permissions are deliberately redesigned.
- Use `celery -A config`, not `--app=config`.
- Format complex shell commands over multiple lines with backslashes.
- For curl healthchecks, use compact short flags in the established style, such as `-fsS -o /dev/null`.
