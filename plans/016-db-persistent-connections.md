# Plan 016: Enable persistent database connections (CONN_MAX_AGE + CONN_HEALTH_CHECKS)

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving to the
> next step. If anything in the "STOP conditions" section occurs, stop and
> report — do not improvise. When done, update the status row for this plan
> in `plans/README.md` — unless a reviewer dispatched you and told you they
> maintain the index.
>
> **Drift check (run first)**: `git diff --stat 2849304..HEAD -- '{{cookiecutter.project_slug}}/src/config/settings/components/database.py' '{{cookiecutter.project_slug}}/.env.example' '{{cookiecutter.project_slug}}/README.md'`
> `.env.example` and README legitimately drift via plans 002/007/009; on any
> `database.py` mismatch with the excerpt below, STOP.

## Status

- **Priority**: P2
- **Effort**: S
- **Risk**: LOW (standard production posture; env escape hatch for poolers)
- **Depends on**: none (edits `.env.example` — run sequentially with 002/007/009, never in a parallel worktree)
- **Category**: perf
- **Planned at**: commit `2849304`, 2026-07-04

## Why this matters

`DATABASES = {"default": env.db("DATABASE_URL")}` leaves Django's default
`CONN_MAX_AGE=0`: with the sync gunicorn workers the template ships, **every
HTTP request opens and tears down a fresh Postgres TCP connection + auth
handshake**, and every readiness probe does the same. Pure added latency and
DB-side churn, inherited silently by every baked project. Persistent
connections (`CONN_MAX_AGE`) with `CONN_HEALTH_CHECKS=True` (so a worker
never reuses a dead connection after a DB restart) are the standard Django
production posture. Total open connections stay bounded by worker count
(`GUNICORN_WORKERS=5` default + celery concurrency), far below Postgres's
default `max_connections=100`. An env knob matters for one real case:
projects fronting PgBouncer in transaction mode must set `CONN_MAX_AGE=0`.

## Important context: this is a cookiecutter template

- Project code lives under the literal `{{cookiecutter.project_slug}}/` dir —
  quote it in shell. Preserve Jinja placeholders verbatim.
- Verification = bake (`uvx cookiecutter . --no-input -o <dir>`) + baked
  suite (`uv run pytest`, 100% coverage) + baked pre-commit.

## Current state

- `{{cookiecutter.project_slug}}/src/config/settings/components/database.py`
  (whole file):

  ```python
  from config.settings import env

  DATABASES = {"default": env.db("DATABASE_URL")}
  ```

- `{{cookiecutter.project_slug}}/.env.example` — byte-sorted (enforced by the
  `file-contents-sorter` pre-commit hook); optional vars with code defaults
  are commented (`# AWS_ACCESS_KEY_ID=` pattern); AGENTS.md: env vars only
  for "secrets, deployment topology, or resource sizing" — connection reuse
  is resource sizing, so an env knob is in-policy.
- Tests run on `DATABASE_URL=sqlite:///:memory:` (pyproject pytest env) —
  Django's sqlite in-memory test databases keep a shared connection during
  tests regardless of `CONN_MAX_AGE`; the suite is the regression check.
- README "Local Setup" documents `.env.example` variables; the Production
  section exists after Plan 002.

## Commands you will need

| Purpose | Command | Expected on success |
|---------|---------|---------------------|
| Bake | `uvx cookiecutter . --no-input -o $BAKE` | exit 0 |
| Tests | `cd $BAKE/my-project && uv run pytest` | all pass, 100% |
| Hooks | `cd $BAKE/my-project && git add -A && uv run pre-commit run --all-files` | all pass |
| Settings probe (inside bake) | Step 2 command | prints `60 True`, then `0 True` |

## Scope

**In scope**:
- `{{cookiecutter.project_slug}}/src/config/settings/components/database.py`
- `{{cookiecutter.project_slug}}/.env.example`
- `{{cookiecutter.project_slug}}/README.md` (one bullet)

**Out of scope**:
- Adding a pooler (PgBouncer) service or Django 5+ `"pool"` options for
  psycopg — bigger decisions; the README bullet records the tradeoff.
- Any change to `DATABASE_URL` parsing or the cache config.

## Git workflow

- Branch: `advisor/016-db-persistent-connections`
- Conventional commit, e.g. `perf: enable persistent database connections`
- Do NOT push or open a PR unless the operator instructed it.

## Steps

### Step 1: Set the connection options

Replace `database.py` with:

```python
from config.settings import env

DATABASES = {"default": env.db("DATABASE_URL")}
DATABASES["default"]["CONN_HEALTH_CHECKS"] = True
DATABASES["default"]["CONN_MAX_AGE"] = env.int("CONN_MAX_AGE", default=60)
```

### Step 2: Prove both the default and the override

Inside a fresh bake, run with the suite's env
(`DJANGO_ENV=ci ALLOWED_HOSTS=x CACHE_URL=locmemcache://
DATABASE_URL=sqlite:///:memory: SECRET_KEY=s` — plus any vars later plans
made mandatory for ci; copy the pyproject `[tool.pytest.ini_options] env`
list):

```
uv run python -c "
import django, os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()
from django.conf import settings
db = settings.DATABASES['default']
print(db['CONN_MAX_AGE'], db['CONN_HEALTH_CHECKS'])
"
```

→ prints `60 True`. Re-run with `CONN_MAX_AGE=0` in the env → prints
`0 True`.

### Step 3: Document

- `.env.example`: add the commented optional line `# CONN_MAX_AGE=` in
  byte-sorted position (comment lines sort before the uncommented block —
  match the existing `# AWS_*` cluster placement; run the pre-commit sorter
  to confirm it doesn't move).
- README (Production section if present, otherwise Local Setup): one bullet —
  persistent DB connections default to 60s with health checks; set
  `CONN_MAX_AGE=0` when running behind PgBouncer in transaction mode.

### Step 4: Full verification loop

**Verify**: fresh bake → `uv run pytest` → all pass, 100%;
`git add -A && uv run pre-commit run --all-files` → all pass (the sorter
validates the `.env.example` placement).

## Test plan

No new pytest tests: asserting the two settings values would be exactly the
"configuration-value-only test" AGENTS.md forbids. The executable checks are
Step 2 (both branches of the env knob) and the untouched full suite (proves
the sqlite test path tolerates the options).

## Done criteria

- [ ] `database.py` matches Step 1 (three lines of config)
- [ ] Step 2 prints `60 True` by default and `0 True` with the override
- [ ] `.env.example` has the commented `# CONN_MAX_AGE=` line; sorter hook leaves it in place
- [ ] Baked project: `uv run pytest` → all pass, 100%
- [ ] Baked project: `uv run pre-commit run --all-files` → all pass
- [ ] No files outside the in-scope list modified (`git status`)
- [ ] `plans/README.md` status row updated

## STOP conditions

- The baked suite fails or hangs after Step 1 (would indicate the sqlite
  test path reacting to persistent connections — unexpected; report before
  making the options engine-conditional).
- `env.int("CONN_MAX_AGE", ...)` conflicts with a same-named variable already
  introduced by another plan (grep `.env.example` first).

## Maintenance notes

- If the maintainer later adopts psycopg connection pooling (Django `"pool"`
  option) or a PgBouncer sidecar, revisit: pooling and `CONN_MAX_AGE > 0`
  should not be combined.
- Reviewers: any future plan raising `GUNICORN_WORKERS`/celery concurrency
  defaults should sanity-check total connections vs Postgres
  `max_connections`.
