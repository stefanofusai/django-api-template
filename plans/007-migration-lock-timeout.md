# Plan 007: Bound production migration lock acquisition

> **Executor instructions**: Execute in order, run all gates, and update the
> index. Stop on unexpected PostgreSQL behavior.
>
> **Drift check (run first)**: `rtk git diff --stat 20ec7c5..HEAD -- '{{cookiecutter.project_slug}}/.docker/scripts/migrations.sh' '{{cookiecutter.project_slug}}/src/config/settings/components/database.py' '{{cookiecutter.project_slug}}/tests/config/unit/' '{{cookiecutter.project_slug}}/README.md'`

## Status

- **Priority**: P1
- **Effort**: M
- **Risk**: MED
- **Depends on**: none
- **Category**: migration
- **Planned at**: commit `20ec7c5`, 2026-07-10

## Why this matters

The migration entrypoint disables `statement_timeout` and sets no PostgreSQL
`lock_timeout`. A migration blocked behind application traffic can therefore
wait forever and prevent a replacement API container from starting. Lock
acquisition should fail boundedly so deployment can abort and retry without
interrupting the old release.

## Current state

- `migrations.sh:4` exports `DATABASE_STATEMENT_TIMEOUT=0`.
- `database.py:12-14` sets only PostgreSQL `statement_timeout` in connection
  options.
- API `pre_start` invokes the migration script on every production start.
- The repository already tests production settings through subprocesses in
  `prod_settings_test.py`.

## Commands you will need

| Purpose | Command | Expected |
|---|---|---|
| Settings tests | `rtk uv run pytest tests/config/unit/prod_settings_test.py -q` | pass |
| Migration checks | `rtk ./.github/scripts/migrations-check.sh` | exit 0 |
| Full suite | `rtk uv run pytest` | pass, coverage 100% |

## Scope

**In scope**:
- `{{cookiecutter.project_slug}}/.docker/scripts/migrations.sh`
- `{{cookiecutter.project_slug}}/src/config/settings/components/database.py`
- `{{cookiecutter.project_slug}}/tests/config/unit/prod_settings_test.py`
- a focused migration shell test if needed
- `{{cookiecutter.project_slug}}/.env.example`
- `{{cookiecutter.project_slug}}/README.md`

**Out of scope**:
- Bounding total migration execution time.
- Concurrent multi-replica migration orchestration.
- Rewriting existing migrations.

## Git workflow

Do not commit or push unless explicitly requested.

## Steps

### Step 1: Add failing settings/entrypoint assertions

Assert database options contain both statement and lock timeout clauses, the
normal default is bounded, and the migration script sets statement timeout to
zero plus a conservative migration-specific lock timeout. Assert an explicit
override is forwarded.

**Verify**: lock-timeout assertions fail before implementation.

### Step 2: Add an independent lock timeout

Have `database.py` read `DATABASE_LOCK_TIMEOUT` with a fixed safe default and
compose both `-c lock_timeout=...` and `-c statement_timeout=...` in the options
string. In `migrations.sh`, export a bounded value from
`MIGRATION_DATABASE_LOCK_TIMEOUT` with a documented default such as 5000 ms.
Keep total migration statement timeout disabled.

**Verify**: settings tests pass and rendered shell remains POSIX-compliant.

### Step 3: Document failure and override behavior

Add the optional migration override as an operational timeout, explain that a
lock-timeout failure should abort and be retried, and warn against setting it
to zero outside planned maintenance.

**Verify**: README and `.env.example` remain aligned; optional values are
commented, not empty active assignments.

### Step 4: Exercise a real lock conflict

In a temporary baked project, hold a conflicting PostgreSQL table lock in one
connection and run a migration/query using the migration settings in another.
Assert failure occurs within the configured bound and the lock holder remains
unaffected.

**Verify**: bounded failure, then success after releasing the lock.

## Test plan

Cover defaults, override, zero/negative validation if implemented, the exact
connection options string, script exports, and one real PostgreSQL lock wait.

## Done criteria

- [ ] Production migrations cannot wait indefinitely for a lock by default.
- [ ] Total migration statement execution remains unbounded intentionally.
- [ ] Retry/override operations are documented.
- [ ] Settings, migration, pytest, and pre-commit gates pass.

## STOP conditions

- psycopg/Django rejects multiple `-c` options in the rendered connection.
- The real lock test requires a destructive schema change.
- Existing production deployments rely on an undocumented zero lock timeout.

## Maintenance notes

Review lock timeout independently from statement timeout. A migration may be
long-running yet safe once it has acquired its lock.
