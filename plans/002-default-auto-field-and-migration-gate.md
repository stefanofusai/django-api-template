# Plan 002: Set DEFAULT_AUTO_FIELD and gate CI on migration drift

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving to the
> next step. If anything in the "STOP conditions" section occurs, stop and
> report — do not improvise. When done, update the status row for this plan
> in `plans/README.md` — unless a reviewer dispatched you and told you they
> maintain the index.
>
> **Drift check (run first)**:
> `git diff --stat d333a73..HEAD -- '{{cookiecutter.project_slug}}/src/config/settings/components/core.py' '{{cookiecutter.project_slug}}/.github' .github/workflows/ci.yaml`
> If any in-scope file changed since this plan was written, compare the
> "Current state" excerpts against the live code before proceeding; on a
> mismatch, treat it as a STOP condition. (Plan 001 legitimately edits
> `tests.yaml` and `ci.yaml` — that drift is expected; re-read those files
> and integrate.)

## Status

- **Priority**: P1
- **Effort**: S
- **Risk**: LOW
- **Depends on**: 001 (ordering only — both edit `tests.yaml`/`ci.yaml`;
  this plan is correct with or without 001)
- **Category**: bug
- **Planned at**: commit `d333a73`, 2026-07-05

## Why this matters

No settings module sets `DEFAULT_AUTO_FIELD`, so Django falls back to
`AutoField` for implicit primary keys — but the committed initial
migration freezes `core.User.id` as `BigAutoField`. The runtime model and
the migration state disagree: `manage.py makemigrations` on a fresh baked
project wants to generate an `AlterField` back to `AutoField`, and Django
emits the `models.W042` warning. Nothing catches this because CI never
asks "are migrations in sync with models?". This plan fixes the setting
to match the migration and adds the missing CI gate so model/migration
drift can never ship silently again.

## Current state

Cookiecutter template; generated project under the literal directory
`{{cookiecutter.project_slug}}/` (quote in shell). `.github/workflows/*`
inside it are copied without rendering (no Jinja allowed there).

- `{{cookiecutter.project_slug}}/src/config/settings/components/core.py`
  — full current content:

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

  Settings in components are alphabetized.

- `{{cookiecutter.project_slug}}/src/apps/core/migrations/0001_initial.py:22-30`
  — the frozen PK:

  ```python
  (
      "id",
      models.BigAutoField(
          auto_created=True,
          primary_key=True,
          serialize=False,
          verbose_name="ID",
      ),
  ),
  ```

- `grep -rn "DEFAULT_AUTO_FIELD" '{{cookiecutter.project_slug}}/src'` →
  no matches (verified at planning time).

- `{{cookiecutter.project_slug}}/.github/scripts/deploy-check.sh` — the
  existing pattern for running `manage.py` in CI with throwaway env vars
  (own-line env assignments, `\` continuations, Jinja conditionals per
  knob, `uv run --group=ci --locked --no-default-groups`). Model the new
  script on it. Note it uses `DJANGO_ENV=prod`; the new script uses
  `DJANGO_ENV=ci`, which needs only `ALLOWED_HOSTS`, `CACHE_URL`,
  `DATABASE_URL`, `SECRET_KEY` (the `ci` overlay adds no required vars)
  and therefore needs NO Jinja conditionals at all.

- `{{cookiecutter.project_slug}}/.github/workflows/tests.yaml` — steps:
  checkout, setup-python, setup-uv, `uv sync`, "Run deploy checks"
  (`./.github/scripts/deploy-check.sh`), "Run tests" (pytest).

- `.github/workflows/ci.yaml` `bake` job — steps: bake, assert lockfile,
  `uv sync --locked`, "Run tests" (`uv run pytest`), "Run pre-commit".

- `makemigrations --check --dry-run` does not connect to the database, so
  a parse-only `DATABASE_URL` works.

## Commands you will need

| Purpose | Command | Expected on success |
|---------|---------|---------------------|
| Bake | `uvx cookiecutter . --no-input -o /tmp/plan002` | project baked |
| Install | `cd /tmp/plan002/my-project && uv sync --locked` | exit 0 |
| Drift check (manual) | see Step 2 | exit 0, "No changes detected" |
| Baked tests | Postgres running per plan 001 docs, then `uv run pytest` | pass |
| Baked pre-commit | `git add -A && uv run pre-commit run --all-files` | exit 0 |
| actionlint | `uvx --from actionlint actionlint <file>` | exit 0 |
| Root pre-commit | `pre-commit run --all-files` | exit 0 |

## Scope

**In scope**:

- `{{cookiecutter.project_slug}}/src/config/settings/components/core.py`
- `{{cookiecutter.project_slug}}/.github/scripts/migrations-check.sh`
  (create)
- `{{cookiecutter.project_slug}}/.github/workflows/tests.yaml` (one step)
- `.github/workflows/ci.yaml` (one step in the `bake` job)

**Out of scope** (do NOT touch):

- `src/apps/core/migrations/0001_initial.py` — the point is to make the
  runtime match the migration, never the reverse.
- `deploy-check.sh` — separate concern (security checks).
- Any model file; `apps.py` files (`default_auto_field` per-app is NOT
  the chosen mechanism — one global setting is).

## Git workflow

- Work directly on `main`; do not create or switch to a plan branch unless the
  operator explicitly asks.
- Do NOT commit, push, or open a PR unless the operator explicitly instructs it.
- If asked to commit, use a conventional commit such as
  `fix: set DEFAULT_AUTO_FIELD and gate CI on migration drift`.

## Steps

### Step 1: Set DEFAULT_AUTO_FIELD

In `core.py`, insert alphabetically (after `DEBUG`, before
`ROOT_URLCONF`):

```python
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
```

`BigAutoField` is what `0001_initial.py` already froze, so no new
migration is needed or expected.

**Verify**: `grep -n "DEFAULT_AUTO_FIELD" '{{cookiecutter.project_slug}}/src/config/settings/components/core.py'`
→ one match, in alphabetical position.

### Step 2: Prove the drift is gone in a baked project

```shell
uvx cookiecutter . --no-input -o /tmp/plan002
cd /tmp/plan002/my-project && uv sync --locked
ALLOWED_HOSTS=localhost \
CACHE_URL=locmemcache:// \
DATABASE_URL=postgres://postgres:postgres@localhost:5432/postgres \
DJANGO_ENV=ci \
SECRET_KEY=plan002-check-secret-0123456789 \
uv run python manage.py makemigrations --check --dry-run
```

**Verify**: exit 0 with "No changes detected". Sanity-check the fix is
what removed the drift: temporarily comment the new setting out, rerun —
it must exit 1 proposing an `id` AlterField for `core.user` — then
restore the setting and rerun to exit 0. Also run the same env-prefixed
`manage.py check` and confirm no `models.W042` in the output.

### Step 3: Create `migrations-check.sh`

Create `{{cookiecutter.project_slug}}/.github/scripts/migrations-check.sh`
(mode 755, `git update-index --chmod=+x` if needed), modeled on
`deploy-check.sh`'s style but Jinja-free:

```sh
#!/bin/sh
set -eu

# DATABASE_URL is parse-only: makemigrations --check never connects.
ALLOWED_HOSTS=localhost \
CACHE_URL=locmemcache:// \
DATABASE_URL=postgres://postgres:postgres@localhost:5432/postgres \
DJANGO_ENV=ci \
SECRET_KEY=$(uuidgen)$(uuidgen) \
uv run --group=ci --locked --no-default-groups \
    python manage.py makemigrations --check --dry-run
```

**Verify**: run it inside the baked project
(`./.github/scripts/migrations-check.sh` after copying the file in, or
re-bake) → exit 0.

### Step 4: Wire it into both CI surfaces

- In `{{cookiecutter.project_slug}}/.github/workflows/tests.yaml`, add
  between "Run deploy checks" and "Run tests":

  ```yaml
        - name: Run migrations check
          run: ./.github/scripts/migrations-check.sh
  ```

- In `.github/workflows/ci.yaml` `bake` job, add the equivalent step
  (with the job's `working-directory: /tmp/bake/${{ matrix.slug }}`
  pattern) between "Run tests" and "Run pre-commit".

**Verify**: `uvx --from actionlint actionlint` on both files → exit 0.

### Step 5: Full verification

Re-bake fresh; run the baked suite (Postgres per plan 001 — if plan 001
is not yet merged, tests still run on SQLite; either way they must pass),
`git add -A && uv run pre-commit run --all-files` in the baked project,
and `pre-commit run --all-files` at the root.

**Verify**: all exit 0. Also bake the minimal knob case
(`use_celery=none email_provider=none use_sentry=no use_s3_media=no
use_traefik=no`) and run `./.github/scripts/migrations-check.sh` there →
exit 0 (proves the script needs no knob conditionals).

## Test plan

No new pytest tests: the behavior is enforced by the new CI gate itself.
The negative check in Step 2 (comment out → exit 1 → restore) is the
regression demonstration.

## Done criteria

- [ ] `DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"` present in
      `core.py`, alphabetized
- [ ] Baked `migrations-check.sh` exits 0 on default AND minimal bakes
- [ ] With the setting removed, the script exits 1 (verified once, then
      restored)
- [ ] `git status` in the baked project after the full suite shows no
      generated migration files
- [ ] Both workflows pass actionlint; root + baked pre-commit exit 0
- [ ] `plans/README.md` status row updated

## STOP conditions

- Step 2 still reports changes AFTER adding the setting — the drift is
  different from the analysis (e.g. another model/field involved).
  Report the proposed migration diff verbatim.
- Step 2's negative check does NOT report drift with the setting absent —
  the premise of this plan is wrong; report.
- `makemigrations --check` tries to connect to the database (unexpected
  in Django 6) — report rather than adding a real DB dependency.

## Maintenance notes

- Any new app must rely on the global `DEFAULT_AUTO_FIELD`; do not add
  per-app `default_auto_field` values.
- The CI gate means every future model change must ship its migration in
  the same commit — this is the desired discipline.
- Plan 009 (example resource app) generates a new migration; this gate
  will verify it.
