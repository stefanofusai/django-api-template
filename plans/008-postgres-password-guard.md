# Plan 008: Reject the default (slug-derived) database password in production, mirroring the `SECRET_KEY` boot guard

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving on.
> **Read the "Design decision" note before writing code.** If anything in "STOP
> conditions" occurs, stop and report — do not improvise. When done, update this
> plan's status row in `plans/README.md` — unless a reviewer dispatched you and
> told you they maintain the index.
>
> **Drift check (run first)**:
> `git diff --stat ae42991..HEAD -- "{{cookiecutter.project_slug}}/src/config/settings/environments/prod.py" "{{cookiecutter.project_slug}}/src/config/settings/components/database.py" "{{cookiecutter.project_slug}}/.env.example" "{{cookiecutter.project_slug}}/README.md"`
> If any changed since this plan was written, compare "Current state" against the
> live files before proceeding; on a mismatch, STOP.

## Status

- **Priority**: P2
- **Effort**: S
- **Risk**: LOW
- **Depends on**: none (coordinates with plan 007 — both edit `prod.py`; land one, then re-check the other's excerpt)
- **Category**: security
- **Planned at**: commit `ae42991`, 2026-07-07

## Repository context (read before anything else)

This is a **Cookiecutter template**. Source is under `{{cookiecutter.project_slug}}/`
— **quote it in shell**. Files contain Jinja that must stay valid.

- Settings use `django-split-settings`: components define names into one shared
  namespace, then the `environments/{ci,dev,prod}.py` overlay mutates them. Names
  referenced in `prod.py` but defined in a component need
  `# noqa: F821  # ty: ignore[unresolved-reference]` markers (this is why the
  existing `SECRET_KEY` guard carries them).
- `prod.py` is **coverage-omitted** (`pyproject.toml` omit list) and only loaded
  when `DJANGO_ENV=prod`; the test suite runs under `DJANGO_ENV=ci`. So this
  guard is verified by *booting a prod-configured app*, not by pytest.
- Verification means baking: `uvx cookiecutter . --no-input -o /tmp/bake`.

## Why this matters

`SECRET_KEY` has a production boot guard that refuses to start if the shipped
`django-insecure-` placeholder was not replaced (`prod.py:5-7`). The bundled
Postgres credential has no such guard, and its shipped default is worse than a
placeholder: `.env.example` defaults `POSTGRES_PASSWORD`, `POSTGRES_USER`, and
the `DATABASE_URL` password to the **project slug** (with hyphens → underscores)
— a value that is public (it is the repository/package name). Because the
default is *non-empty*, the `.env.example` "empty uncommented values are required
in production" convention does not flag it, so an operator can deploy prod with a
publicly-guessable database password and nothing complains.

The bundled Postgres publishes no host port (reachable only on the Compose
network), so this is defense-in-depth, not an internet-facing hole. But a
predictable production DB password is exactly the kind of mistake a template
should make impossible to ship silently — and the fix mirrors an idiom the
template already endorses.

## Current state

`{{cookiecutter.project_slug}}/src/config/settings/environments/prod.py` (top):

```python
from django.core.exceptions import ImproperlyConfigured

from config.settings import env

if SECRET_KEY.startswith("django-insecure-"):  # noqa: F821  # ty: ignore[unresolved-reference]
    msg = "SECRET_KEY must be replaced with a securely generated value in production."
    raise ImproperlyConfigured(msg)
```

`{{cookiecutter.project_slug}}/src/config/settings/components/database.py` (full):

```python
from config.settings import env

DATABASES = {"default": env.db("DATABASE_URL")}
DATABASES["default"]["CONN_HEALTH_CHECKS"] = True
DATABASES["default"]["CONN_MAX_AGE"] = env.int("CONN_MAX_AGE", default=60)
```

`env.db("DATABASE_URL")` (django-environ) returns a dict whose password lives
under the `"PASSWORD"` key. Confirm this in the baked venv before relying on it:
`uv run python -c "import environ; print(environ.Env().db_url_config('postgres://u:p@h:5432/db'))"`
→ shows a `PASSWORD` key.

`{{cookiecutter.project_slug}}/.env.example` (the DB block):

```
# Django database URL used by the app.
DATABASE_URL=postgres://{{ cookiecutter.project_slug.replace('-', '_') }}:{{ cookiecutter.project_slug.replace('-', '_') }}@postgres:5432/{{ cookiecutter.project_slug.replace('-', '_') }}
# PostgreSQL database created by the Compose service.
POSTGRES_DB={{ cookiecutter.project_slug.replace('-', '_') }}
# PostgreSQL password used by the Compose service.
POSTGRES_PASSWORD={{ cookiecutter.project_slug.replace('-', '_') }}
# PostgreSQL user used by the Compose service.
POSTGRES_USER={{ cookiecutter.project_slug.replace('-', '_') }}
```

The default DB password, at render time, is
`{{ cookiecutter.project_slug.replace('-', '_') }}`.

**Conventions**: keep the existing `noqa/ty` marker style; `AGENTS.md` says
add env vars only for secrets/topology/sizing and keep operational constants in
code — this guard adds *no* env var (the "known insecure default" is baked into
`prod.py` as a Jinja literal). Do not add a test that only asserts config values.

## Design decision (confirm intent before coding)

This plan adds a **prod boot guard** that refuses to start if the DB password is
still the slug default. It deliberately does NOT ship the password empty in
`.env.example`, because dev uses the same file (`cp .env.example .env` →
`docker compose -f .docker/compose/dev.yaml up`) and an empty `POSTGRES_PASSWORD`
breaks the bundled Postgres init. The guard keeps dev working while blocking an
insecure prod boot.

If the maintainer would rather treat the slug default as acceptable
(compose-network-only DB, documented replace-before-deploy) and close this with
docs only, then this guard is unwanted — **surface that as the decision** and do
not add the guard. Otherwise proceed.

## Commands you will need

| Purpose | Command | Expected |
|---------|---------|----------|
| Bake default | `uvx cookiecutter . --no-input -o /tmp/bake` | `/tmp/bake/my-project/` |
| Confirm env.db PASSWORD key | (in bake) `uv run python -c "import environ; print('PASSWORD' in environ.Env().db_url_config('postgres://u:p@h:5432/db'))"` | `True` |
| Boot guard fires (slug default) | see Step 3 | `ImproperlyConfigured` raised |
| Boot guard silent (real password) | see Step 3 | app config loads, no raise |
| Baked tests | `cd /tmp/bake/my-project && DATABASE_URL=postgres://postgres:postgres@localhost:5432/postgres uv run pytest` | 100% cov, all pass (unaffected — runs under ci) |
| Deploy check | `cd /tmp/bake/my-project && ./.github/scripts/deploy-check.sh` (read it for the env prefix) | exit 0 |
| Baked pre-commit | `cd /tmp/bake/my-project && git add -A && uv run pre-commit run --all-files` | exit 0 |
| Root pre-commit | (repo root) `uvx pre-commit run --all-files` | exit 0 |

## Scope

**In scope**:
- `{{cookiecutter.project_slug}}/src/config/settings/environments/prod.py` — add
  the DB-password boot guard next to the `SECRET_KEY` guard.
- `{{cookiecutter.project_slug}}/README.md` — update the `## Production`
  section's password prose (see Step 5) so it states the DB-password
  replacement is now enforced at boot.
- `{{cookiecutter.project_slug}}/.env.example` — optionally strengthen the
  `POSTGRES_PASSWORD` comment to say it is required in production (do NOT empty
  it — see Design decision).

**Out of scope**:
- `components/database.py` — no change; the guard reads `DATABASES` in `prod.py`.
- `dev.py`/`ci.py` — dev/CI legitimately use the default/throwaway password.
- Any change that empties the password in `.env.example` (breaks dev).

## Git workflow

- Work directly on `main`. Do NOT branch/commit/push/PR unless told. If asked to
  commit: Conventional Commits, e.g. `feat: reject the default database password in production`.

## Steps

### Step 1: Add the boot guard to `prod.py`

Immediately after the `SECRET_KEY` guard, add a guard comparing the runtime DB
password to the baked-in insecure default. The default value is emitted as a
Jinja literal so each generated project checks against *its own* slug default:

```python
_INSECURE_DB_PASSWORD = "{{ cookiecutter.project_slug.replace('-', '_') }}"
if DATABASES["default"].get("PASSWORD") == _INSECURE_DB_PASSWORD:  # noqa: F821  # ty: ignore[unresolved-reference]
    msg = "The default database password must be replaced with a securely generated value in production."
    raise ImproperlyConfigured(msg)
```

Notes:
- `DATABASES` is defined in `components/database.py` and IS in scope here:
  `src/config/settings/__init__.py` `include()`s all components first and the
  `environments/{DJANGO_ENV}.py` overlay LAST, in one shared namespace — the
  same mechanism that lets the existing lines reference `LOGGING`/`MIDDLEWARE`/
  `STORAGES`. Keep the `noqa/ty` markers (same reason as those lines).
- Use `.get("PASSWORD")` so a `DATABASE_URL` without a password (edge case)
  yields `None`, which never equals the slug default — the guard won't
  false-positive.
- Place it before the other assignments, grouped with the `SECRET_KEY` guard, so
  the two "refuse to boot" checks sit together at the top.

**Verify**: `grep -c "_INSECURE_DB_PASSWORD" /tmp/bake/my-project/src/config/settings/environments/prod.py` → 2 (definition + use) after a default bake.

### Step 2: Confirm the render is correct for hyphenated slugs

Bake a hyphenated project and confirm the literal matches the underscored slug
used in `.env.example`:

```
uvx cookiecutter . --no-input -o /tmp/bake-hy project_name="My API Server 2"
grep "_INSECURE_DB_PASSWORD =" /tmp/bake-hy/my-api-server-2/src/config/settings/environments/prod.py
grep "^POSTGRES_PASSWORD=" /tmp/bake-hy/my-api-server-2/.env.example
```

**Verify**: both show `my_api_server_2` (hyphens converted to underscores,
matching `.env.example`). If they differ, the guard would never fire — STOP.

### Step 3: Prove the guard fires and stays silent appropriately

The guard runs at settings import under `DJANGO_ENV=prod`. Drive it with a
minimal env (read `.github/scripts/deploy-check.sh` for the full prod-safe env
prefix; you need a non-insecure `SECRET_KEY`, `ALLOWED_HOSTS`,
`CSRF_TRUSTED_ORIGINS`, `CACHE_URL`, and — for `use_sentry=yes` bakes — a
`SENTRY_DSN`, etc., so that the *only* thing that can fail is the DB password):

- **Fires** — `DATABASE_URL` password == slug default:
  ```
  cd /tmp/bake/my-project
  <prod-safe env> DATABASE_URL=postgres://my_project:my_project@localhost:5432/my_project \
    uv run python -c "import django; django.setup()"
  ```
  **Verify**: raises `ImproperlyConfigured: The default database password must be replaced...`.

- **Silent** — real password:
  ```
  <prod-safe env> DATABASE_URL=postgres://my_project:$(uuidgen)@localhost:5432/my_project \
    uv run python -c "import django; django.setup()"
  ```
  **Verify**: no `ImproperlyConfigured` about the DB password (it may fail later
  trying to *connect*, which is fine — the guard passed; use `django.setup()`
  which loads settings without opening a DB connection, or scope the assertion to
  the specific exception type/message).

### Step 4: Confirm nothing else broke

```
cd /tmp/bake/my-project
DATABASE_URL=postgres://postgres:postgres@localhost:5432/postgres uv run pytest   # runs under ci, guard not active
./.github/scripts/deploy-check.sh
git add -A && uv run pre-commit run --all-files
```
**Verify**: tests 100% pass; deploy check exits 0; pre-commit exit 0. Then root
`uvx pre-commit run --all-files` exits 0.

### Step 5: Document it

In `{{cookiecutter.project_slug}}/README.md`, the anchor is the `## Production`
section — there is no "Required Configuration" heading. Near lines 280-282 the
prose already says "Use the generated value for `SECRET_KEY`, and set a strong
`POSTGRES_PASSWORD`. … production boot refuses `django-insecure-` keys."
Update that passage so it also states the new enforcement: production now
refuses to boot while the DB password (in `DATABASE_URL` / `POSTGRES_PASSWORD`)
is still the shipped slug default. Keep the prose style of the existing
sentences.

Optionally tighten the `.env.example` `POSTGRES_PASSWORD` comment to note it is
required in production (do not empty the value).

**Verify**: root `uvx pre-commit run markdownlint --all-files` exits 0.

## Test plan

- No pytest test — `prod.py` is coverage-omitted and the suite runs under `ci`;
  `AGENTS.md` forbids config-only assertion tests. Verification is the boot-guard
  drive in Step 3 (fires / silent) plus the unchanged suite + deploy check.
- Confirm across knobs that the guard renders correctly: default and hyphenated
  (Step 2). Note the `.env.example` DB block is **unconditional** (no
  `postgres` knob gate), so a `postgres=external` bake also ships the
  slug-default `DATABASE_URL` — the guard renders there too and *would* fire if
  the operator kept that default, which is desirable (an external DB with the
  slug password is just as guessable). Confirm a `postgres=external` bake boots
  with a real password.

## Done criteria

ALL must hold:

- [ ] Default bake `prod.py` contains `_INSECURE_DB_PASSWORD` (2 occurrences) and an `ImproperlyConfigured` guard on it.
- [ ] Hyphenated bake: the literal equals the underscored slug and matches `.env.example`.
- [ ] Booting prod with the slug-default DB password raises `ImproperlyConfigured`; booting with a real password does not raise the DB-password error.
- [ ] Baked `uv run pytest` still passes at 100% (unaffected); deploy check exits 0.
- [ ] `postgres=external` bake boots with a real password (guard renders there too and fires only on the slug default).
- [ ] README documents the enforced DB-password replacement; `.env.example` password is NOT emptied.
- [ ] Baked + root pre-commit exit 0; no out-of-scope files modified (`git status`).
- [ ] `plans/README.md` status row updated.

## STOP conditions

Stop and report (do not improvise) if:

- The maintainer's intent (guard vs docs-only) cannot be confirmed (see Design
  decision).
- `env.db("DATABASE_URL")` does not expose the password under `"PASSWORD"` in the
  installed django-environ (report the real key).
- The rendered `_INSECURE_DB_PASSWORD` literal does not match the `.env.example`
  default for some slug (the guard would never fire).
- Adding the guard makes the standard deploy check or the test suite fail
  (it should not — the suite runs under `ci`).

## Maintenance notes

- If the DB credential ever moves entirely out of `.env.example` (e.g. always
  externally provisioned), revisit whether this guard still applies.
- A reviewer should confirm the guard reads the *runtime* password (from
  `DATABASE_URL`) and compares to the *baked* slug default — not a hardcoded
  string that drifts if the slug-derivation logic in `.env.example` changes.
- This is the same idiom as the `SECRET_KEY` guard; keep them adjacent so future
  readers see the pattern.
