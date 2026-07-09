# AGENTS.md

## Command Workflow

- Put short flags before long flags in shell commands, alphabetize short flags
  and long flags within their groups, and write long flags with values using
  `--flag=value`.
- Use `rg` or `rg --files` for searching.
{%- if cookiecutter.use_celery != "none" %}
- Use `uv run ...` for Python tooling, tests, pre-commit, Django, and Celery commands.
{%- else %}
- Use `uv run ...` for Python tooling, tests, pre-commit, and Django commands.
{%- endif %}
- Do not commit unless explicitly asked.
- Preserve existing uncommitted work. Never revert user changes unless explicitly asked.
- Keep `pyproject.toml` and `uv.lock` in sync when dependencies or dependency groups change.
- If sandboxed `uv`, `pytest`, or pre-commit commands fail because they need cache access, rerun with escalation rather than changing project state to work around it.

## Project Context

{% if cookiecutter.use_celery != "none" and cookiecutter.use_s3_media == "yes" -%}
- This is a Python 3.14 Django 6 project using Django Ninja, Celery, django-structlog, django-storages, pytest, Ruff, Ty, uv, Docker, and Compose.
{%- elif cookiecutter.use_celery != "none" %}
- This is a Python 3.14 Django 6 project using Django Ninja, Celery, django-structlog, pytest, Ruff, Ty, uv, Docker, and Compose.
{%- elif cookiecutter.use_s3_media == "yes" %}
- This is a Python 3.14 Django 6 project using Django Ninja, django-structlog, django-storages, pytest, Ruff, Ty, uv, Docker, and Compose.
{%- else %}
- This is a Python 3.14 Django 6 project using Django Ninja, django-structlog, pytest, Ruff, Ty, uv, Docker, and Compose.
{%- endif %}
- Settings use `django-split-settings` with responsibility-based components and environment overlays. Keep this structure.
- Environment overlays should mutate only environment-specific differences.
- Do not add `django-configurations`, settings builder functions, wildcard imports, or tests that only assert configuration values.
- Pin dependencies in `pyproject.toml` to exact versions, and use the latest intended release when adding or updating a dependency.
- Put dependencies imported by settings loaded outside `prod` in main dependencies. A prod-only dependency can live in the `prod` group only when non-prod settings never import it.

## Style

- Follow Ruff formatting and linting. Ruff selects `ALL`, so keep changes explicit and tidy.
- Avoid trailing commas on newlines unless Ruff adds them to keep long lines valid/readable.
- Never add `from __future__ import annotations`.
- Avoid `Protocol` or other speculative abstractions unless multiple real implementations already need them.
- Only add code comments that state constraints the code cannot show — upstream
  defaults, cross-file couplings, deliberately unusual constructs — and that
  name the misreading they prevent (see `src/apps/api/pagination.py` for the
  canonical example). Never add comments that narrate what the code does.
- Prefer clear, explicit code over clever compression.
- Use extended YAML block style instead of compact flow style, for example
  `branches:` followed by `- main` instead of `branches: [main]`.
- Order unordered list items alphabetically when dependency order does not
  matter. This includes Markdown inventory bullets, YAML lists of pre-commit
  hook ids, full Docker Compose volume entries, GitHub Actions matrix entries,
  Dependabot update entries, environment-variable documentation, and command
  argument lists. For example, put `check-dependabot` before
  `check-github-workflows`, `CACHE_URL` before `DATABASE_URL`,
  `../../src:/app/src` before `media_data:/app/media`, and `docker` before
  `github-actions`.
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
- Order model fields logically, not alphabetically. Declare timestamp fields first, including ones not inherited from `CreatedAtUpdatedAtModel` such as a `deleted_at` soft-delete field, then relations, then scalar attributes, with large `TextField` bodies last.
- Order Django Ninja schema fields to match their model's field order, not alphabetically.
- Order factory fields to match their model's field order, not alphabetically; order factories and their `register(...)` calls to follow model/dependency order (a factory referenced by another via `SubFactory` comes first).
- Lead Django admin `list_display` with timestamp fields (`created_at`, `updated_at`), then the remaining columns.
- Alphabetize parameters in tests, helper functions, and Django Ninja endpoints when framework conventions do not require a leading parameter such as `self`, `request`, `sender`, or Django admin's `request, queryset`.
- When forwarding keyword arguments to a callee, pass them in the order the callee declares its parameters: declared parameters in signature order first, then arguments captured by `**kwargs`. For example, when wrapping a client whose method is `post(path, data=None, json=None, **request_params)`, pass `json=` (declared) before `user=` (a `**request_params` argument).

## GitHub Actions Naming

- Use `.yaml` for workflow files and name them with lower kebab-case basenames
  that describe the workflow scope, for example `docker-checks.yaml` or
  `openapi-schema-export.yaml`.
- Keep each workflow `name:` as a Title Case noun phrase aligned with the file
  basename, such as `Docker Checks`, `Dependency Audit`, or
  `OpenAPI Schema Export`.
- Use lower kebab-case job ids, and keep them stable because other workflow
  fields may reference them through `needs`.
- Use concise, user-facing job `name:` values because they become GitHub status
  check names. Prefer action-oriented names such as `Audit dependencies`,
  `Check deployment settings`, `Check migrations`, and
  `Smoke test Docker Compose`.
- For matrix jobs, put the matrix value at the end in parentheses.
- Use sentence case imperative step names, for example
  `Check out repository`, `Set up Python`, `Install dependencies`,
  `Export OpenAPI schemas`, `Probe API container health`, and
  `Tear down Docker Compose`.
- When adding, renaming, or removing generated-project workflow jobs, update
  repository branch protection required status checks to match each job's
  rendered `name`.

## Django And Configuration

- Respect `django-extra-checks`: models need `__str__`, `Meta.ordering`, admin registration, gettext verbose/help text, explicit FK `related_name` and `db_index`, choice constraints, and `UniqueConstraint` instead of `unique_together`.
- In settings modules, put declarations and settings mutations before function
  calls or similar side effects. For example, initialize integrations such as
  `sentry_sdk.init(...)` after the settings values they depend on have been
  declared.
{%- if cookiecutter.use_sentry == "yes" %}
- Order `sentry_sdk.init(...)` keyword arguments according to Sentry's
  documented options order:
  <https://docs.sentry.io/platforms/python/configuration/options/#available-options>.
{%- endif %}
- Add environment variables only for secrets, deployment topology, or resource sizing.
- Mock env values (CI workflows, CI scripts, the Dockerfile's build-time
  collectstatic env, pytest env) use fixed `mock-<variable-name>` literals,
  e.g. `mock-postgres-password`; the mock
  `SECRET_KEY=mock-secret-key-0123456789-abcdefghijklmnopqrstuvwxyz` must stay
  ≥50 chars with ≥5 unique chars so `manage.py check --deploy` passes. Never
  generate mock values at runtime (`uuidgen`, `$RANDOM`), and never promote a
  mock value to a real credential.
- Placeholder hostnames follow a two-tier rule: `example.com` appears only in
  human-facing documentation (README prose, `.env.example` comments) and the
  production `ALLOWED_HOSTS` boot sentinel; machine-consumed placeholders in
  tests, CI scripts, workflows, and the Docker build env use reserved `.test`
  hostnames such as `smtp.example.test`, which can never resolve publicly.
- Keep `.env.example` grouped by concern, not globally byte-sorted. Alphabetize keys only within each block.
- In `.env.example`, comments must be own-line only; never put inline comments after a value.
- In `.env.example`, empty uncommented values mean required in production and must have a boot guard or prod-only consumer that fails loudly.
- In `.env.example`, commented values are optional overrides with safe code defaults.
- The API has no default auth. Endpoints requiring protection must add ninja
  auth (global `auth=` on the API instance, or per-router/per-operation);
  never ship a mutating endpoint unauthenticated.
{%- if cookiecutter.use_example_api == "yes" and cookiecutter.api_auth == "jwt" %}
- The example JWT mode uses `django-ninja-jwt`, `apps.api.auth.jwt_auth`, and
  the library controllers. Do not add custom credential storage unless a
  project explicitly needs personal access tokens.
{%- endif %}
{%- if cookiecutter.use_celery != "none" %}
- Celery results are opt-in per task: use `@shared_task(ignore_result=False)`
  when a task's result must be persisted; tasks are at-least-once
  (`acks_late` + `reject_on_worker_lost`), so keep them idempotent.
{%- endif %}
- Do not add empty optional values to `.env.example`; document optional AWS variables as commented examples.
- Keep operational constants fixed in code unless there is a real deployment need to configure them.
- Keep Django Ninja routers resource-oriented. Mount resource routers at their resource prefix and keep route-local paths relative.
{%- if cookiecutter.use_example_api == "yes" %}
- The example notes resource uses `apps.notes.controllers.NotesController`, a
  django-ninja-extra class-based controller; `/api/health` and `/api/ready`
  remain plain function-based routers on `internal_api`.
{%- else %}
- `/api/health` and `/api/ready` remain plain function-based routers on
  `internal_api`.
{%- endif %}
- Mount business routers on `v1_api` (under `/api/v1/`); `internal_api` is reserved for internal probes and must stay unversioned.

## Testing

- Organize tests by app, then by type: `tests/<app>/{integration,unit}/` (for example `tests/api/integration/`, `tests/core/unit/`, `tests/notes/integration/`). `tests/conftest.py` applies the `integration`/`unit` marker from the `integration`/`unit` path segment, so a new app's tests just need those subdirectories. Shared helpers stay at the `tests/` root (`conftest.py`, `factories.py`{% if cookiecutter.use_example_api == "yes" %}, `utils.py`{% endif %}).
- Prefix autouse fixtures with `_` (they are ambient infrastructure, never
  requested by name — see `_clear_cache`, `_zeal`, and `_broker_ready_default`
  in `tests/conftest.py`). Autouse fixtures the whole suite needs belong in
  `tests/conftest.py`, not duplicated per module.
- When a test needs a fixture only for its side effect and never references
  it in the body, request it via `@pytest.mark.usefixtures("fixture_name")`
  instead of declaring it as a parameter and voiding it with
  `_ = fixture_name` (see `tests/api/unit/pagination_test.py`). This only
  works for test functions/classes.{% if cookiecutter.use_example_api == "yes" %} A fixture that depends on
  another fixture purely for side effect still needs the explicit
  parameter, voided with `_ = ...` if unused (see
  `authenticated_schema_headers` in `tests/api/integration/schema_test.py`).{% endif %}
- The full suite enforces 100% coverage. Focused test commands are useful, but final verification should include `uv run pytest`.
- Run relevant checks before completion:
  - `uv run pre-commit run ruff-check --all-files`
  - `uv run pre-commit run ty --all-files`
  - `uv run pytest`
  - `uv run pre-commit run --all-files` for broad changes
- Register factories in `tests/factories.py` when adding concrete models
  (see `UserFactory`).
- To add a new API resource, use the `new-api-resource` agent skill in
  `.agents/skills/`.
- Use pytest-factoryboy model fixtures directly and prefer attribute
  parametrization for factory-backed model setup.
- When a test needs multiple model instances, register named model fixtures
  with sequence suffixes such as `note_1` and `note_2`; use `LazyFixture(...)`
  only when a fixture attribute must point at another fixture, such as a note
  owned by `user_1`.
- Use Django's `@override_settings(...)` or `@modify_settings(...)` for tests
  that change Django settings; do not mock or patch `django.conf.settings` or
  derived settings objects directly.
- Avoid direct `Model.objects.create(...)` and direct Django model construction in tests unless the test specifically needs an invalid unsaved object; use factory `.build(...)` for those invalid cases.
- Use Faker/factory values for incidental names, URLs, UUIDs, and response metadata.
- Keep fixed literals only when they are the behavior under test.
- Test names must follow `test_<subject>_<expected_behavior>_when_<condition>`, using `for_<scenario>` when it reads better.
- Keep test functions alphabetized within each file.
- Test API endpoints through the ninja `TestClient` fixtures (`internal_api_client`, `v1_api_client`, `authenticated_client`) using `response.data` and router-relative paths; pass `user=` (or use `authenticated_client`) for authenticated endpoints.
- When a test must use Django's test `client` for full-URL/routing behavior, resolve URLs with `django.urls.reverse(...)` instead of hardcoding paths, and read the body via `response.json()`.

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
{%- if cookiecutter.use_celery != "none" %}
- Use `celery -A config`, not `--app=config`.
{%- endif %}
- Format complex shell commands over multiple lines with backslashes.
- For curl healthchecks, use compact short flags in the established style, such as `-fsS -o /dev/null`.
