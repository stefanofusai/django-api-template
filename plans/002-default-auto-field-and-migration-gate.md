# Plan 002: Catch migration drift with a dedicated CI workflow

> **Status: DONE** (implemented directly on 2026-07-06, brought to `main`
> uncommitted per operator request). This file is the record of what
> shipped and why; earlier revisions are summarized under "History".

## Status

- **Priority**: P1
- **Effort**: S
- **Risk**: LOW
- **Depends on**: 001 (DONE)
- **Category**: bug (prevention)
- **Planned at**: commit `46ef781`, 2026-07-06

## History (why the approach changed 3×)

1. Original: set `DEFAULT_AUTO_FIELD` + add a migration gate. **Dropped the
   `DEFAULT_AUTO_FIELD` half** — moot on Django 6 (defaults to
   `BigAutoField`; no drift with or without it).
2. Then: a shell `migrations-check.sh` wired into both CI surfaces
   (committed to a worktree as `7ecbc04`, reverted).
3. Then: a pytest test in the suite.
4. **Final (shipped): a dedicated CI workflow** in the baked project,
   `.github/workflows/migrations.yaml` — per the operator's explicit
   preference: CI-only, no pytest, no pre-commit, no shell script, no new
   dependency, no `DEFAULT_AUTO_FIELD`.

## Why this matters

Nothing verified that committed migrations stay in sync with the models.
If someone edits a model and forgets to generate/commit the migration,
the mismatch ships silently — the app boots, most tests pass, and it
surfaces only in production (`column does not exist`) or as a surprise
`makemigrations` prompt on the next developer's machine.
`makemigrations --check --dry-run` exits non-zero if any model change
lacks its migration; a dedicated workflow runs it on every push/PR of a
generated project.

## What shipped

`{{cookiecutter.project_slug}}/.github/workflows/migrations.yaml` — a new
workflow (copied WITHOUT rendering, so Jinja-free), mirroring the baked
`tests.yaml` structure:

- `name: Migrations` (Title-case noun, matching the repo convention:
  `tests.yaml`→"Tests", `dependency-audit.yaml`→"Dependency Audit"; no
  verb prefix — hence the filename is `migrations.yaml`, not
  `check-migrations.yaml`).
- Triggers: `pull_request` and `push` to `main`; standard `concurrency`
  block.
- A `postgres: image: postgres:18.4` service (same as `tests.yaml`, with
  the single-line `options:` health-check form that yamlfmt accepts) so
  `makemigrations --check`'s migration-history consistency probe connects
  cleanly instead of emitting a `RuntimeWarning` (the exit code is correct
  either way, but the service keeps CI logs clean).
- Steps: Checkout → Set up Python (`python-version-file: pyproject.toml`)
  → Set up uv → Install dependencies
  (`uv sync --group=ci --locked --no-default-groups`) → "Check for missing
  migrations": a static `env:` block (`ALLOWED_HOSTS`, `CACHE_URL`,
  `DATABASE_URL`, `DEFAULT_FROM_EMAIL`, `DJANGO_ENV: ci`, and a
  clearly-fake `SECRET_KEY: ci-migration-check-not-a-real-secret` — safe
  because `DJANGO_ENV=ci` does not enforce the `django-insecure-` check;
  matches how `tests.yaml`/`ci.yaml` already hardcode a throwaway
  `DATABASE_URL` in `env:`), with a single-line
  `run: uv run --group=ci --locked --no-default-groups manage.py
  makemigrations --check --dry-run` (no redundant `python` — `uv run`
  executes the `manage.py` script directly).

`DEFAULT_FROM_EMAIL` is set unconditionally (the workflow can't use Jinja,
and `components/email.py` requires it when `email_provider != "none"`;
it's harmless when email is off). No knob conditionals are needed —
verified the file is byte-identical across bakes.

## Scope

**In scope**: `{{cookiecutter.project_slug}}/.github/workflows/migrations.yaml`
(create) — ONE file.

**Out of scope / explicitly NOT done**: no `DEFAULT_AUTO_FIELD`; no pytest
test; no pre-commit hook; no `.github/scripts/*` shell script; no
third-party package (`django-test-migrations` tests migration *behaviour*,
a different concern with nothing to exercise here — deferred).

Also added (follow-up): a matching "Check for missing migrations" step in
the template repo's own `.github/workflows/ci.yaml` `bake` job, so
template-level migration drift (e.g. a future app's missing migration) is
caught on EVERY bake variant in the template's own CI — not only in a
generated project's CI. Same command/env as the baked workflow.

## Verification (done)

- Baked default project; `migrations.yaml` passes `yamlfmt`, `yamllint`,
  "Lint GitHub Actions workflow files" (actionlint), and "Validate GitHub
  Workflows" (check-jsonschema) with no rewrite.
- Positive: with a matching Postgres running, the check command exits 0,
  prints "No changes detected", no warning.
- Negative: inserting a throwaway field on `core.User` makes the command
  detect a missing migration (`0002_user_scratch.py`, "Add field scratch
  to user"); reverted → clean again.

## Done criteria

- [x] `migrations.yaml` created (Jinja-free), runs `makemigrations
      --check --dry-run` under `DJANGO_ENV=ci` with a postgres service
- [x] Passes yamlfmt/yamllint/actionlint/workflow-schema hooks
- [x] Positive run exit 0 "No changes detected"; negative run detects the
      missing migration
- [x] No pytest, no pre-commit, no shell script, no dependency, no
      `DEFAULT_AUTO_FIELD`
- [x] `plans/README.md` status row updated

## Maintenance notes

- The baked `migrations.yaml` enforces migration discipline in each
  **generated project's** CI. Separately, the template repo's own
  `ci.yaml` `bake` job runs the same `makemigrations --check --dry-run`
  step on every bake variant, so template-level migration drift is caught
  in the template's own CI too (a baked workflow in `/tmp/bake` never
  triggers on GitHub, hence the explicit bake-job step).
- **Plan 009** (example `notes` resource) generates a new migration. Its
  original Step 4 referenced a `migrations-check.sh` that no longer
  exists; when executing 009, verify its migration by running
  `manage.py makemigrations --check --dry-run` directly (the command this
  workflow runs) — the generated project also gains `migrations.yaml`
  automatically.
- `django-test-migrations` (data-migration/reversibility testing) remains
  deferred: no data migrations to exercise yet; Django 6 support
  unconfirmed.
