# Plan 020: Restructure .env.example into documented blocks and rationalize dependency groups

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving to the
> next step. If anything in the "STOP conditions" section occurs, stop and
> report — do not improvise. When done, update the status row for this plan
> in `plans/README.md` — unless a reviewer dispatched you and told you they
> maintain the index.
>
> **Drift check (run first)**: `git diff --stat e41a9be..HEAD -- '{{cookiecutter.project_slug}}/.env.example' '{{cookiecutter.project_slug}}/pyproject.toml' '{{cookiecutter.project_slug}}/.pre-commit-config.yaml' '{{cookiecutter.project_slug}}/AGENTS.md' '{{cookiecutter.project_slug}}/src/config/settings/'`
> Plans 008/009/016/018 legitimately add env vars and dependencies. Fold any
> new keys/pins into the target layouts below by their classification rules.
> On a mismatch in the mechanism excerpts (sorter hook, settings imports),
> STOP and report instead of improvising.

## Status

- **Priority**: P2
- **Effort**: S–M
- **Risk**: MED (touches the env contract every service reads and the dependency graph every install resolves)
- **Depends on**: none strictly; supersedes plan 010's Step 1 (whitenoise/storages group move). Serialize with 008/009/013/016/018 because they share `.env.example` and/or `pyproject.toml`.
- **Category**: dx / dependencies
- **Planned at**: commit `e41a9be`, 2026-07-05

## Why this matters

Two contracts every baked project inherits are currently organized by accident
rather than by design.

First, `.env.example` is a flat byte-sorted list with no documentation. The
`file-contents-sorter` hook forces global alphabetical order, so related keys
are scattered, nothing distinguishes "required in production" from "optional
override", and no key says what it does or what a valid value looks like. The
maintainer has decided to switch to semantic blocks with per-key
documentation: keys are grouped by concern, and alphabetical order applies
only within each block.

Second, dependency groups contain duplication and one real misclassification.
`src/config/settings/__init__.py` imports `django_stubs_ext` unconditionally,
but the pin lives only in the `prod` group. Dev/ci work by transitive accident
because `django-stubs` pulls it in; a main-deps-only install is broken today.
Also, `dev` duplicates the `ci` group pins by hand, and `whitenoise` plus
`django-storages[s3]` install everywhere even though only prod settings
reference them.

The deliverable is the reorganized files plus the classification rules in
`AGENTS.md` so future env vars and dependencies land in the right place.

## Important context: this is a cookiecutter template

- Project code lives under the literal `{{cookiecutter.project_slug}}/` dir.
  Quote it in shell and preserve every `{{ cookiecutter.* }}` Jinja
  placeholder verbatim.
- Verification means bake (`uvx cookiecutter . --no-input -o <dir>`) and run
  the baked suite (`uv run pytest`, 100% coverage) plus baked pre-commit.
- Comments in `.env.example` must sit on their own line. Do not put inline
  comments after values: Compose `env_file:` and `django-environ` do not
  reliably strip trailing `#` comments, so an inline comment can silently
  become part of the value.

## Current state

- `.env.example` is byte-sorted and includes commented optional AWS keys, an
  uncommented `AWS_STORAGE_BUCKET_NAME=`, service URLs, process sizing,
  `SECRET_KEY=django-insecure-change-me-in-production`, `SENTRY_DSN=`, and
  optional Sentry knobs as uncommented values.
- `.pre-commit-config.yaml` sorts both `.docker/Dockerfile.dockerignore` and
  `.env.example`:

  ```yaml
      - id: file-contents-sorter
        files: ^(\.docker/Dockerfile\.dockerignore|\.env\.example)$
  ```

- `src/config/settings/__init__.py` imports `django_stubs_ext`
  unconditionally and appends `components/sentry.py` only when
  `DJANGO_ENV == "prod"`.
- `sentry-sdk` must stay in main dependencies because the CI deploy check
  loads prod settings with the `ci` group.

## Scope

**In scope**:
- `{{cookiecutter.project_slug}}/.env.example`
- `{{cookiecutter.project_slug}}/.pre-commit-config.yaml`
- `{{cookiecutter.project_slug}}/pyproject.toml`
- `{{cookiecutter.project_slug}}/AGENTS.md`
- `plans/README.md` only for the plan 010 supersession note if not already present

**Out of scope**:
- Any `src/` code change.
- Version bumps. Copy every pin at its live version from disk.
- Plan 010's remaining items: pyupgrade hook removal, skills-lock reconcile,
  and Dockerfile apt-stage split.
- Env keys owned by unexecuted plans (`RESEND_API_KEY`, `CONN_MAX_AGE`,
  `TRAEFIK_*`). Do not pre-add them.

## Git workflow

- Branch: `advisor/020-env-and-dependency-groups`
- Conventional commit, e.g. `build: restructure env example and dependency groups`
- Do NOT push or open a PR unless the operator instructed it.

## Steps

### Step 1: Release .env.example from the sorter

In `.pre-commit-config.yaml`, narrow the `file-contents-sorter` pattern:

```yaml
      - id: file-contents-sorter
        files: ^\.docker/Dockerfile\.dockerignore$
```

Without this, the hook flattens the block structure on the next commit.

### Step 2: Rewrite .env.example into semantic blocks

Replace `.env.example` with this target layout, preserving Jinja expressions
exactly and folding in any keys that landed after `e41a9be` by the same rules.

```dotenv
# Copy to .env for local development (cp .env.example .env). Values below are
# working defaults for the Compose dev stack. Conventions: comments sit on
# their own line, never inline after a value; an empty value is required in
# production and rejected at boot; a commented-out key is an optional override
# shown with its code default; keys are grouped by concern and alphabetical
# within each block.

# --- Django ---
# Keep 127.0.0.1 in the list: the container healthcheck probes localhost.
ALLOWED_HOSTS=localhost,127.0.0.1
# Required in production: the scheme://host origins your clients use.
CSRF_TRUSTED_ORIGINS=https://example.com,https://www.example.com
# Selects the settings overlay (dev | ci | prod). The Compose files override
# this per service; this value applies to bare manage.py runs.
DJANGO_ENV=dev
LOG_LEVEL=INFO
# Production boot rejects the django-insecure- prefix; generate a real key:
# uv run python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'
SECRET_KEY=django-insecure-change-me-in-production

# --- Database (PostgreSQL) ---
DATABASE_URL=postgres://{{ cookiecutter.project_slug.replace('-', '_') }}:{{ cookiecutter.project_slug.replace('-', '_') }}@postgres:5432/{{ cookiecutter.project_slug.replace('-', '_') }}
POSTGRES_DB={{ cookiecutter.project_slug.replace('-', '_') }}
# Generate a strong password before deploying; production reuses this file.
POSTGRES_PASSWORD={{ cookiecutter.project_slug.replace('-', '_') }}
POSTGRES_USER={{ cookiecutter.project_slug.replace('-', '_') }}

# --- Cache and broker (Redis) ---
CACHE_URL=rediscache://redis:6379/0
CELERY_BROKER_URL=redis://redis:6379/1

# --- Process sizing ---
CELERY_WORKER_CONCURRENCY=2
CELERY_WORKER_MAX_TASKS_PER_CHILD=100
GUNICORN_GRACEFUL_TIMEOUT=30
GUNICORN_TIMEOUT=60
GUNICORN_WORKERS=5

# --- Reverse proxy ---
# Address(es) Gunicorn trusts to set X-Forwarded-* headers.
# FORWARDED_ALLOW_IPS=

# --- Observability (Sentry) ---
# Required in production; boot fails while empty.
SENTRY_DSN=
# SENTRY_ENABLE_LOGS=False
# SENTRY_PROFILE_SESSION_SAMPLE_RATE=1.0
# SENTRY_TRACES_SAMPLE_RATE=1.0

# --- Object storage (S3-compatible) ---
# Required in production; static/media storage reads this value.
AWS_STORAGE_BUCKET_NAME=
# AWS_ACCESS_KEY_ID=
# AWS_S3_CUSTOM_DOMAIN=
# AWS_S3_ENDPOINT_URL=
# AWS_S3_REGION_NAME=
# AWS_SECRET_ACCESS_KEY=
```

If plan 008 has landed, no additional env keys are required. If a later plan
has already landed, classify its keys by concern and keep alphabetical order
inside that block.

### Step 3: Add the env/dependency conventions to AGENTS.md

Replace the old `.env.example` guidance with rules equivalent to:

- `.env.example` is grouped by concern, not globally byte-sorted.
- Comments are own-line only; never inline after a value.
- Empty uncommented values mean required in production and must have a boot
  guard or a prod-only consumer that fails loudly.
- Commented-out values are optional overrides with safe code defaults.
- Dependency placement rule: anything imported by settings loaded outside
  prod must be in main dependencies. A prod-only dependency can live in
  `prod` only when non-prod settings never import it.

Keep the existing Sentry init ordering rule.

### Step 4: Rationalize dependency groups

In `pyproject.toml`, preserving live versions:

1. Move `django-stubs-ext` from the `prod` group to main dependencies because
   `settings/__init__.py` imports it unconditionally.
2. Move `whitenoise` and `django-storages[s3]` from main dependencies to the
   `prod` group. They are referenced by prod settings as backend strings and
   should still be installed for prod image/deploy checks.
3. Make `dev` include `ci` via PEP 735 group inclusion, then keep only
   dev-only tools there (`django-extensions`, `pre-commit`, `werkzeug`).
4. Drop the explicit `hypothesis` pin if no project code imports it directly;
   `schemathesis` carries it transitively. If the maintainer wants visible
   ownership of the pin, leave it and record that choice.

Do not move `sentry-sdk`: `components/sentry.py` is prod-only, but CI deploy
checks load prod settings with the `ci` group.

### Step 5: Empirical gates

In a fresh bake:

1. `uv sync --locked --no-default-groups`
2. `DJANGO_ENV=ci ALLOWED_HOSTS=localhost CACHE_URL=locmemcache:// DATABASE_URL=sqlite:///:memory: SECRET_KEY=test-secret-key uv run --no-default-groups python - <<'PY'
import config.settings
print("SETTINGS OK")
PY`

Expected: prints `SETTINGS OK`. This proves `django_stubs_ext` is no longer a
transitive accident.

Then run deploy-check parity:

```shell
DJANGO_ENV=prod \
ALLOWED_HOSTS=example.com \
AWS_STORAGE_BUCKET_NAME=ci \
CACHE_URL=locmemcache:// \
CSRF_TRUSTED_ORIGINS=https://example.com \
DATABASE_URL=sqlite:///:memory: \
SECRET_KEY=ci-secret-for-deploy-checks-0123456789-abcdefghijklmnopqrstuvwxyz \
SENTRY_DSN=https://00000000000000000000000000000000@sentry.example.com/1 \
uv run --group=ci --locked --no-default-groups \
python manage.py check --deploy --fail-level=WARNING --tag=security
```

Expected: exit 0. If moving `whitenoise`/`django-storages` breaks this, STOP
and report; do not paper over it by importing prod-only dependencies in ci.

### Step 6: Full verification

In a fresh bake:

- `uv run pytest` → all pass, 100%.
- `git add -A && uv run pre-commit run --all-files` → all pass and the sorter
  does not rewrite `.env.example`.
- If Docker socket is available, run:
  `docker build -f .docker/Dockerfile --build-arg UV_DEPENDENCY_GROUP=prod .`
  → exit 0. If Docker is denied, report the permission error.

## Done criteria

- `.env.example` has documented semantic blocks and no inline comments after
  values.
- `file-contents-sorter` no longer targets `.env.example`.
- `django-stubs-ext` is in main dependencies.
- `whitenoise` and `django-storages[s3]` are in the `prod` group.
- `dev` includes `ci` instead of duplicating its pins.
- Main-deps-only settings import prints `SETTINGS OK`.
- Deploy-check parity command exits 0.
- Fresh baked tests and pre-commit pass.
- `plans/README.md` records that plan 020 supersedes plan 010 Step 1.

## STOP conditions

- Any `src/` code change appears necessary.
- `uv` does not support the intended dependency-group include syntax in the
  pinned version.
- Moving `whitenoise`/`django-storages[s3]` breaks CI deploy-check parity or
  prod image dependency resolution.
- `.env.example` block layout cannot coexist with existing hooks without
  weakening unrelated checks.

## Maintenance notes

After this lands, new env vars go into semantic blocks, alphabetized within
their block. Plans 009, 016, and 018 must classify their keys instead of
appending to a flat byte-sorted list.
