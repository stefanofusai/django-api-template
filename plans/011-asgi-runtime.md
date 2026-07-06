# Plan 011: Serve the generated API through ASGI instead of WSGI

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving to the
> next step. If anything in the "STOP conditions" section occurs, stop and
> report — do not improvise. When done, update the status row for this plan
> in `plans/README.md` — unless a reviewer dispatched you and told you they
> maintain the index.
>
> **Drift check (run first)**:
> `git diff --stat ce9ee33..HEAD -- '{{cookiecutter.project_slug}}/pyproject.toml' '{{cookiecutter.project_slug}}/.docker/scripts/gunicorn.sh' '{{cookiecutter.project_slug}}/.docker/scripts/dev.sh' '{{cookiecutter.project_slug}}/src/config' '{{cookiecutter.project_slug}}/tests/integration/api/schema_test.py' '{{cookiecutter.project_slug}}/README.md' README.md`
> If any in-scope file changed since this plan was written, compare the
> "Current state" excerpts against the live code before proceeding; on a
> mismatch, treat it as a STOP condition.

## Status

- **Priority**: P2
- **Effort**: M
- **Risk**: MED — changes the process serving the app in every generated
  deployment and touches dependency locking, smoke tests, docs, and API
  contract tests
- **Depends on**: 004 and 005 preferred first (they stabilize prod server
  shutdown and smoke-test the shipped compose file); serialize with any plan
  editing `pyproject.toml`, Docker scripts, or API schema tests
- **Category**: migration
- **Planned at**: commit `ce9ee33`, 2026-07-05

## Why this matters

Django Ninja supports `async def` operations, and its async guide says those
views should be run behind an ASGI server such as Uvicorn. The generated
project currently ships only a WSGI entrypoint and runs Gunicorn against
`config.wsgi`, so the template starts future services from a sync-only web
runtime even though the API framework can route sync and async operations
together. Moving the generated web runtime to ASGI makes async endpoints a
first-class path for external API calls, async ORM use, and other IO-bound
work without forcing every endpoint to become async.

This is not a blanket performance promise. Existing sync Django/ORM code stays
sync, and async endpoints must still use async-safe libraries or Django's async
ORM APIs. The value is making ASGI the default runtime boundary so new services
do not need to perform this migration later.

Reference docs:

- Django Ninja async support:
  <https://django-ninja.dev/guides/async-support/>
- Uvicorn deployment notes: the bundled `uvicorn.workers` import path is
  deprecated; use the separate `uvicorn-worker` package for Gunicorn workers:
  <https://uvicorn.dev/deployment/>
- Schemathesis Python API includes `schemathesis.openapi.from_asgi` for direct
  ASGI app testing:
  <https://schemathesis.readthedocs.io/en/stable/reference/python/>

## Current state

Cookiecutter template; generated project under the literal
`{{cookiecutter.project_slug}}/` directory (quote it in shell). Keep Jinja
expressions valid and remember `.github/workflows/*` inside the generated
project is copied without rendering.

- `{{cookiecutter.project_slug}}/src/config/wsgi.py` is the only web
  application entrypoint:

  ```python
  from django.core.wsgi import get_wsgi_application

  application = get_wsgi_application()
  ```

- `{{cookiecutter.project_slug}}/src/config/settings/components/core.py:1-9`
  configures Django for WSGI only:

  ```python
  from config.settings import env

  ALLOWED_HOSTS = env.list("ALLOWED_HOSTS")
  API_DOCS_DECORATOR = "apps.api.docs.public"
  DEBUG = False
  ROOT_URLCONF = "config.urls"
  SECRET_KEY = env("SECRET_KEY")
  TIME_ZONE = "UTC"
  WSGI_APPLICATION = "config.wsgi.application"
  ```

- `{{cookiecutter.project_slug}}/.docker/scripts/gunicorn.sh:4-12` serves the
  WSGI app:

  ```sh
  exec gunicorn \
      --access-logfile=- \
      --bind=0.0.0.0:8000 \
      --graceful-timeout="$GUNICORN_GRACEFUL_TIMEOUT" \
      --no-control-socket \
      --pythonpath=src \
      --timeout="$GUNICORN_TIMEOUT" \
      --workers="$GUNICORN_WORKERS" \
      config.wsgi
  ```

- `{{cookiecutter.project_slug}}/pyproject.toml:68-74` puts Gunicorn in the
  `prod` dependency group, but no ASGI server or Gunicorn ASGI worker is
  present:

  ```toml
  prod = [
  {%- if cookiecutter.use_s3_media == "yes" %}
      "django-storages[s3]==1.14.6",
  {%- endif %}
      "gunicorn==26.0.0",
      "whitenoise==6.12.0",
  ]
  ```

- `{{cookiecutter.project_slug}}/tests/integration/api/schema_test.py:1-22`
  tests the OpenAPI schema via WSGI:

  ```python
  import pytest
  import schemathesis
  from schemathesis import Case

  from config.wsgi import application

  @pytest.fixture
  def api_schema() -> object:
      return schemathesis.openapi.from_wsgi(
          "/api/openapi.json",
          application,
      )
  ```

- `{{cookiecutter.project_slug}}/README.md:35-39` documents
  `src/config/` as containing the WSGI entrypoint.

- `{{cookiecutter.project_slug}}/src/config/__init__.py` comments mention
  `config.wsgi` as the web import path when Celery is enabled. Those comments
  must be updated when the runtime moves.

## Commands you will need

| Purpose | Command | Expected on success |
|---------|---------|---------------------|
| Root checks | `rtk uvx pre-commit run --all-files` | exit 0 |
| Bake default | `rtk uvx cookiecutter . --no-input -o /tmp/plan011` | baked project in `/tmp/plan011/my-project` |
| Baked tests | `cd /tmp/plan011/my-project && rtk uv run pytest` | exit 0, 100% coverage |
| Baked pre-commit | `cd /tmp/plan011/my-project && rtk git add -A && rtk uv run pre-commit run --all-files` | exit 0 |
| Docker build | `cd /tmp/plan011/my-project && rtk docker build -f .docker/Dockerfile --build-arg=UV_DEPENDENCY_GROUP=prod .` | image builds |
| Dev stack smoke | `cd /tmp/plan011/my-project && rtk cp .env.example .env && rtk docker compose -f .docker/compose/dev.yaml up -d --build --wait && rtk curl -fsS http://localhost:8000/api/ready && rtk docker compose -f .docker/compose/dev.yaml down -v` | readiness probe returns 200; stack tears down |

If plan 001 has already landed by the time this plan is executed, follow its
updated Postgres-backed test commands instead of the SQLite command above.

## Scope

**In scope**:

- `{{cookiecutter.project_slug}}/pyproject.toml`
- `{{cookiecutter.project_slug}}/uv.lock` in baked verification only; do not
  commit a root lockfile that does not exist
- `{{cookiecutter.project_slug}}/.docker/scripts/gunicorn.sh`
- `{{cookiecutter.project_slug}}/.docker/scripts/dev.sh` if dev should use
  Uvicorn reload instead of Django's WSGI-based runserver path
- `{{cookiecutter.project_slug}}/src/config/asgi.py` (create)
- `{{cookiecutter.project_slug}}/src/config/wsgi.py` (delete if no longer
  referenced; otherwise keep only with a clear compatibility reason)
- `{{cookiecutter.project_slug}}/src/config/__init__.py`
- `{{cookiecutter.project_slug}}/src/config/settings/components/core.py`
- `{{cookiecutter.project_slug}}/tests/integration/api/schema_test.py`
- `{{cookiecutter.project_slug}}/README.md`
- root `README.md` if its feature list or design decisions mention WSGI
- `plans/README.md` status row for this plan

**Out of scope**:

- Converting existing API operations from `def` to `async def`.
- Adding Channels, WebSockets, SSE, background task runners, or lifespan
  startup/shutdown hooks.
- Changing Celery behavior.
- Renaming `.docker/scripts/gunicorn.sh` unless the executor also updates every
  reference and proves no stale name remains.
- Tuning worker counts or adding resource limits; plan 007 owns resource
  bounds.

## Git workflow

- Work directly on `main`; do not create or switch to a plan branch unless the
  operator explicitly asks.
- Do NOT commit, push, or open a PR unless the operator explicitly instructs it.
- If asked to commit, use a conventional commit such as
  `feat: serve generated api through asgi`.

## Steps

### Step 1: Add the ASGI runtime dependencies

In `{{cookiecutter.project_slug}}/pyproject.toml`, keep `gunicorn==26.0.0` in
the `prod` group and add the ASGI worker package:

```toml
    "gunicorn==26.0.0",
    "uvicorn-worker==0.4.0",
    "whitenoise==6.12.0",
```

Do not use `uvicorn.workers.UvicornWorker`; the Uvicorn docs mark that module
deprecated and direct users to the separate `uvicorn-worker` package. Keep the
list alphabetized where dependency order does not matter, following the repo's
style.

**Verify**: bake a project and run `cd /tmp/plan011/my-project && rtk uv lock`
→ exit 0 and `uv.lock` includes `uvicorn-worker`.

### Step 2: Create the ASGI entrypoint and switch Django settings

Create `{{cookiecutter.project_slug}}/src/config/asgi.py`:

```python
from django.core.asgi import get_asgi_application

application = get_asgi_application()
```

In `settings/components/core.py`, replace:

```python
WSGI_APPLICATION = "config.wsgi.application"
```

with:

```python
ASGI_APPLICATION = "config.asgi.application"
```

Delete `src/config/wsgi.py` if no in-scope or generated file still imports it.
If keeping it for compatibility, add a short maintenance comment in this plan's
status update explaining why; otherwise the intended final state is ASGI-only.

Update `src/config/__init__.py` comments from `config.wsgi` to `config.asgi`
and keep the Celery import ordering comment accurate.

**Verify**:

```shell
rtk grep -R "config.wsgi\\|WSGI_APPLICATION\\|from_wsgi" '{{cookiecutter.project_slug}}'
```

→ no matches outside this plan file and any deliberately kept compatibility
comment. If `grep` finds generated docs/tests/scripts, update them before
continuing.

### Step 3: Serve ASGI through Gunicorn's Uvicorn worker

Update `{{cookiecutter.project_slug}}/.docker/scripts/gunicorn.sh` so Gunicorn
continues to be the process manager but uses the ASGI worker and ASGI app:

```sh
exec gunicorn \
    --access-logfile=- \
    --bind=0.0.0.0:8000 \
    --graceful-timeout="$GUNICORN_GRACEFUL_TIMEOUT" \
    --no-control-socket \
    --pythonpath=src \
    --timeout="$GUNICORN_TIMEOUT" \
    --worker-class=uvicorn_worker.UvicornWorker \
    --workers="$GUNICORN_WORKERS" \
    config.asgi:application
```

Keep `--no-control-socket`, timeouts, binding, access logs, and worker count
unchanged. This plan changes the protocol boundary, not the process-management
contract that plans 004 and 005 are validating.

For `{{cookiecutter.project_slug}}/.docker/scripts/dev.sh`, choose one of two
paths and document the choice in the generated README:

- Preferred: run Uvicorn in reload mode against `config.asgi:application`, but
  only if the dev dependency set has the required Uvicorn command available via
  `uvicorn-worker`'s dependencies after `uv sync`.
- Conservative: keep `runserver_plus` for local development, but explicitly
  document that production serves ASGI. If you choose this, add a follow-up note
  in `plans/README.md` because dev/prod runtimes differ.

**Verify**: `rtk grep -R "config.wsgi" '{{cookiecutter.project_slug}}/.docker'`
→ no matches.

### Step 4: Move API contract tests to ASGI

Update `tests/integration/api/schema_test.py` to import the ASGI application
and load schemas through Schemathesis' ASGI loader:

```python
from config.asgi import application


@pytest.fixture
def api_schema() -> object:
    return schemathesis.openapi.from_asgi(
        "/api/openapi.json",
        application,
    )
```

If plan 008 has already landed and parametrized both `/api/openapi.json` and
`/api/v1/openapi.json`, preserve that parametrization and only change the app
import plus loader from WSGI to ASGI.

**Verify**: bake and run `cd /tmp/plan011/my-project && rtk uv run pytest tests/integration/api/schema_test.py`
→ exit 0.

### Step 5: Update generated and root documentation

In `{{cookiecutter.project_slug}}/README.md`, replace "WSGI entrypoint" with
"ASGI entrypoint" in the architecture block. Add a short note in the API usage
or Architecture section:

```markdown
Production serves Django through ASGI (`config.asgi`) using Gunicorn with
Uvicorn workers. Sync and async Django Ninja operations can coexist; use async
handlers only with async-safe libraries or Django's async ORM APIs.
```

Update root `README.md` only if any line still implies the template is WSGI
based. Keep the wording brief; this is not a tutorial.

**Verify**:

```shell
rtk grep -R "WSGI\\|wsgi" README.md '{{cookiecutter.project_slug}}/README.md' '{{cookiecutter.project_slug}}/src/config'
```

→ no matches unless a deliberately retained compatibility note exists.

### Step 6: Bake matrix and runtime verification

Bake at least:

1. Default: `rtk uvx cookiecutter . --no-input -o /tmp/plan011-default`
2. Minimal: `rtk uvx cookiecutter . --no-input -o /tmp/plan011-minimal use_celery=none email_provider=none use_sentry=no use_s3_media=no use_traefik=no`

For each bake:

```shell
cd /tmp/plan011-*/my-project
rtk uv sync --locked
rtk uv run pytest
rtk git add -A
rtk uv run pre-commit run --all-files
```

Then run the Docker build and dev-stack smoke command from the commands table
on the default bake. If plan 005 has landed, also run the prod compose smoke
command it documents so the ASGI server is exercised in production mode.

**Verify**: all commands exit 0, `/api/health` and `/api/ready` return 200, and
container logs identify Gunicorn using the Uvicorn worker class.

## Test plan

- Update `tests/integration/api/schema_test.py` from
  `schemathesis.openapi.from_wsgi` to `schemathesis.openapi.from_asgi`.
- Preserve any plan-008 parametrization of internal and v1 schema URLs.
- Do not add fake async endpoints just to prove ASGI; plan 009 owns example API
  resources, and endpoint-level async examples should be deliberate.
- Verification: `uv run pytest` in default and minimal bakes; Docker smoke
  confirms the ASGI runtime imports and serves the app.

## Done criteria

All must hold:

- [ ] Generated project has `src/config/asgi.py`.
- [ ] Generated project uses `ASGI_APPLICATION = "config.asgi.application"`.
- [ ] Runtime command serves `config.asgi:application` with
  `uvicorn_worker.UvicornWorker`.
- [ ] `schemathesis.openapi.from_asgi` is used in API schema tests.
- [ ] `grep -R "config.wsgi\\|WSGI_APPLICATION\\|from_wsgi" '{{cookiecutter.project_slug}}'`
  returns no stale generated references.
- [ ] Default and minimal bakes pass `uv run pytest`.
- [ ] Baked pre-commit passes after `git add -A`.
- [ ] Docker build succeeds.
- [ ] At least one Compose smoke test reaches `/api/ready`.
- [ ] `plans/README.md` row for plan 011 is updated when complete.

## STOP conditions

Stop and report back (do not improvise) if:

- A current in-scope file no longer matches the excerpts above.
- `uvicorn-worker==0.4.0` is incompatible with Python 3.14 or the pinned
  Gunicorn version during `uv lock`.
- Schemathesis' ASGI loader fails against Django's ASGI application and the
  failure is not a simple import/configuration mistake.
- Moving dev from `runserver_plus` to Uvicorn breaks an existing documented
  development behavior and the conservative path is not acceptable.
- The change requires introducing Channels or any non-HTTP ASGI feature.

## Maintenance notes

Reviewers should scrutinize that this is an ASGI runtime migration, not a broad
async rewrite. Sync Django views and ORM calls are still valid under the
Uvicorn worker; async views must use async-safe code paths. Future plans that
add endpoints may now choose `async def` where the work is IO-bound, but should
avoid wrapping lazy QuerySets incorrectly — evaluate them before crossing the
async boundary or use Django's async ORM APIs.
