# Plan 007: Wire Sentry error tracking, required in production

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving to the
> next step. If anything in the "STOP conditions" section occurs, stop and
> report — do not improvise. When done, update the status row for this plan
> in `plans/README.md` — unless a reviewer dispatched you and told you they
> maintain the index.
>
> **Drift check (run first)**: `git diff --stat 924bfba..HEAD -- '{{cookiecutter.project_slug}}/src/config/settings/environments/prod.py' '{{cookiecutter.project_slug}}/pyproject.toml' '{{cookiecutter.project_slug}}/.env.example' '{{cookiecutter.project_slug}}/.docker/Dockerfile' '{{cookiecutter.project_slug}}/.github/workflows/tests.yaml' '{{cookiecutter.project_slug}}/README.md'`
> On any change, compare "Current state" excerpts against the live code; on a
> mismatch, treat it as a STOP condition. (Plan 002 legitimately edits
> `prod.py`, `.env.example`, and README — expect those diffs; verify the
> excerpts' *shape* still matches.)

## Status

- **Priority**: P2
- **Effort**: S–M
- **Risk**: MED (adds a required prod env var — every prod-settings loading context must be updated in the same change)
- **Depends on**: 002 (README Production section to extend; not blocking if 002 skipped — see Step 6)
- **Category**: direction / dx
- **Planned at**: commit `924bfba`, 2026-07-04

## Why this matters

The template has excellent structured logging but no error tracking — the
single most-expected production integration for a Django service. The
maintainer decided Sentry should be **required in production**, not an
optional no-op: a missing `SENTRY_DSN` must fail the prod boot loudly rather
than silently ship a service with no error visibility.

The tricky part is not the `sentry_sdk.init` call — it is that **three other
contexts load prod settings** and must keep working:

1. the Docker build's `collectstatic` step (runs with `DJANGO_ENV=prod` and
   dummy env values),
2. the CI deploy check (`manage.py check --deploy` with `DJANGO_ENV=prod`),
3. Plan 013's compose smoke test (if present).

Each needs a syntactically valid dummy DSN. `sentry_sdk.init` performs no
network I/O at init (transport is lazy), so a dummy DSN is safe there.

## Important context: this is a cookiecutter template

- Project code lives under the literal `{{cookiecutter.project_slug}}/` dir —
  quote it in shell. Preserve Jinja placeholders verbatim.
- Verification = bake + run the baked suite; prod boot behavior is verified
  with explicit env vars against the baked project.

## Current state

- `{{cookiecutter.project_slug}}/src/config/settings/environments/prod.py`
  starts:

  ```python
  from config.settings import env

  CSRF_COOKIE_SECURE = True
  ...
  ```

  (After Plan 002 it also contains the SECRET_KEY guard and an
  `ImproperlyConfigured` import.)
- `{{cookiecutter.project_slug}}/pyproject.toml` `[project].dependencies` is
  an alphabetized, exact-pinned list (`celery[redis]==5.6.3`, …).
- `{{cookiecutter.project_slug}}/.env.example` is byte-sorted (enforced by the
  `file-contents-sorter` pre-commit hook); required-in-prod vars follow the
  `AWS_STORAGE_BUCKET_NAME=` pattern (present, empty); optional vars are
  commented (`# AWS_ACCESS_KEY_ID=`).
- `{{cookiecutter.project_slug}}/.docker/Dockerfile:31-38` — the collectstatic
  step, an alphabetized env list:

  ```dockerfile
  RUN ALLOWED_HOSTS=localhost \
      AWS_STORAGE_BUCKET_NAME=$(uuidgen) \
      CACHE_URL=locmemcache:// \
      CSRF_TRUSTED_ORIGINS=https://localhost \
      DATABASE_URL=sqlite:///:memory: \
      DJANGO_ENV=prod \
      SECRET_KEY=$(uuidgen) \
      .venv/bin/python manage.py collectstatic --no-input
  ```

- `{{cookiecutter.project_slug}}/.github/workflows/tests.yaml:25-35` — the
  deploy-check step with an equivalent alphabetized env list ending in
  `SECRET_KEY=ci-secret-for-deploy-checks-...`.
- Coverage: `prod.py` is coverage-omitted (Plan 001) — the deploy check and
  the Step 5 boot checks are its executable verification.
- sentry-sdk latest release verified on PyPI at planning time: **2.64.0**.
  Per AGENTS.md, pin the latest release at execution time — check
  `https://pypi.org/pypi/sentry-sdk/json` and use the newer version if one
  exists.
- Dummy DSN format that parses (public key + host + project id, never
  contacted): `https://00000000000000000000000000000000@sentry.example.com/1`

## Commands you will need

| Purpose | Command | Expected on success |
|---------|---------|---------------------|
| Bake | `uvx cookiecutter . --no-input -o $BAKE` | exit 0 |
| Tests | `cd $BAKE/my-project && uv run pytest` | all pass, 100% |
| Hooks | `cd $BAKE/my-project && git add -A && uv run pre-commit run --all-files` | all pass |
| Prod boot check (inside bake) | see Step 5 | as stated there |
| Docker build (optional, needs Docker) | `cd $BAKE/my-project && docker build -f .docker/Dockerfile --build-arg UV_DEPENDENCY_GROUP=prod .` | exit 0 |

## Scope

**In scope**:
- `{{cookiecutter.project_slug}}/pyproject.toml` (add dependency)
- `{{cookiecutter.project_slug}}/src/config/settings/environments/prod.py`
- `{{cookiecutter.project_slug}}/.env.example`
- `{{cookiecutter.project_slug}}/.docker/Dockerfile`
- `{{cookiecutter.project_slug}}/.github/workflows/tests.yaml`
- `{{cookiecutter.project_slug}}/README.md` (one bullet)

**Out of scope**:
- Sentry in dev/ci overlays — required in prod only; other envs never init it.
- Tracing/profiling configuration (`traces_sample_rate` etc.) — omit; error
  tracking is the deliverable, performance products are a project decision.
- structlog→Sentry breadcrumb integration — the SDK's default logging
  integration captures stdlib logging, which structlog feeds; good enough.

## Git workflow

- Branch: `advisor/007-sentry-required-in-prod`
- Conventional commit, e.g. `feat: require Sentry error tracking in production`
- Do NOT push or open a PR unless the operator instructed it.

## Steps

### Step 1: Add the dependency

In `pyproject.toml` `[project].dependencies`, add (alphabetical position —
after `pyproject-parser` if still present, before `structlog`; if Plan 005
removed pyproject-parser, after `psycopg[binary]`):

```toml
"sentry-sdk==2.64.0",
```

(Bump to the latest release if PyPI shows newer; keep exact pin.)

Rationale for main dependencies rather than the prod group: `prod.py` does a
real `import sentry_sdk`, and prod settings are loaded by the CI deploy check
(ci group) and any local `DJANGO_ENV=prod` run — the import must resolve in
every group that can load prod settings. sentry-sdk's own dependency
footprint is small (urllib3 + certifi).

### Step 2: Init in prod.py, required and non-empty

In `src/config/settings/environments/prod.py`, add near the top (after the
`env` import; alongside Plan 002's guard if present):

```python
import sentry_sdk

SENTRY_DSN = env("SENTRY_DSN")

if not SENTRY_DSN:
    msg = "SENTRY_DSN must be set in production."
    raise ImproperlyConfigured(msg)

sentry_sdk.init(dsn=SENTRY_DSN, environment="prod", send_default_pii=False)
```

`env("SENTRY_DSN")` with no default raises `ImproperlyConfigured` when the
variable is absent; the explicit empty-string check closes the
`SENTRY_DSN=`-left-blank hole (the `.env.example` ships it blank). Import
`ImproperlyConfigured` from `django.core.exceptions` if Plan 002 hasn't
already. The Django and Celery integrations are enabled automatically by the
SDK when those packages are importable — no explicit integrations list.

### Step 3: .env.example

Add `SENTRY_DSN=` in byte-sorted position (between `SECRET_KEY=...` and any
later line; `SEC` < `SEN`). Required-in-prod empty-value style mirrors
`AWS_STORAGE_BUCKET_NAME=`.

### Step 4: Dummy DSN for the build and the deploy check

- Dockerfile collectstatic `RUN`: add
  `SENTRY_DSN=https://00000000000000000000000000000000@sentry.example.com/1 \`
  in alphabetical position (after `SECRET_KEY=$(uuidgen)`).
- `tests.yaml` deploy-check env block: add the same
  `SENTRY_DSN=https://00000000000000000000000000000000@sentry.example.com/1 \`
  after the `SECRET_KEY=...` line.
- If Plan 013's smoke-test workflow exists already, add the same value to its
  generated `.env` (see that workflow's env-preparation step).

### Step 5: Prove the boot contract

In a fresh bake, with the common prod env
(`DJANGO_ENV=prod ALLOWED_HOSTS=example.com AWS_STORAGE_BUCKET_NAME=b
CACHE_URL=locmemcache:// CSRF_TRUSTED_ORIGINS=https://example.com
DATABASE_URL=sqlite:///:memory: SECRET_KEY=<long-random>`):

1. WITHOUT `SENTRY_DSN` → `uv run python manage.py check` → fails with
   `ImproperlyConfigured` mentioning SENTRY_DSN.
2. With `SENTRY_DSN=` (empty) → fails the same way.
3. With the dummy DSN → `uv run python manage.py check` → exits 0.

### Step 6: Document

Add to the README Production section (created by Plan 002): a bullet stating
`SENTRY_DSN` is required in production, that boot fails without it, and where
to find the DSN (Sentry project settings). If Plan 002 has not run, add a
short "### Error tracking" subsection under Local Setup instead — do not
create the full Production section here.

### Step 7: Full verification loop

**Verify**: fresh bake → `uv run pytest` → all pass, 100% (prod.py is
coverage-omitted; nothing new needs unit tests);
`git add -A && uv run pre-commit run --all-files` → all pass; optionally the
Docker build command → exit 0 (proves the collectstatic dummy works).

## Test plan

No pytest additions (prod.py is omitted from coverage; AGENTS.md forbids
config-value assertions). The executable verification is Step 5's three boot
checks plus the CI deploy check, which now exercises `sentry_sdk.init` with
the dummy DSN on every push.

## Done criteria

- [ ] `grep -n "sentry-sdk" '{{cookiecutter.project_slug}}/pyproject.toml'` → one exact-pinned entry
- [ ] Step 5's three checks behave exactly as stated (fail / fail / pass)
- [ ] `grep -c SENTRY_DSN` across `.env.example`, `Dockerfile`, `tests.yaml` → present in all three
- [ ] Baked project: `uv run pytest` → all pass, 100%
- [ ] Baked project: `uv run pre-commit run --all-files` → all pass
- [ ] No files outside the in-scope list modified (`git status`)
- [ ] `plans/README.md` status row updated

## STOP conditions

- `sentry_sdk.init` with the dummy DSN raises (e.g. DSN parse change in a
  newer SDK) — report the SDK version and error; do not switch to a real DSN
  or an empty-string init.
- The pinned sentry-sdk pulls in a dependency that conflicts with the lock —
  report the resolver error.
- You find yourself adding `SENTRY_DSN` handling to `dev.py`/`ci.py` — the
  requirement is prod-only; stop and re-read the scope.

## Maintenance notes

- Anyone adding a new prod-settings-loading context (another workflow, another
  compose file, a k8s manifest) must provide `SENTRY_DSN` there too — the
  boot guard makes forgetting loud, which is the point.
- If the maintainer later wants tracing, add `traces_sample_rate` env-driven
  in the same `init` call; keep error tracking required, tracing optional.
