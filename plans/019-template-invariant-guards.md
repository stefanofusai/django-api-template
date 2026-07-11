# Plan 019: Guard Redis image pins and complex Compose predicates

> **Executor instructions**: Add narrow, fail-closed invariants. Do not attempt
> broad Jinja parsing or deduplicate separate root/generated configurations.
>
> **Drift check (run first)**: `rtk git diff --stat b367191..HEAD -- 'scripts/check_postgres_image.py' 'tests/check_postgres_image_test.py' '{{cookiecutter.project_slug}}/.docker/compose/' '.pre-commit-config.yaml'`

## Status

- **Priority**: P2
- **Effort**: S
- **Risk**: LOW
- **Depends on**: none
- **Category**: tech-debt, tests
- **Planned at**: commit `b367191`, 2026-07-10

## Why this matters

PostgreSQL image drift is guarded, but Redis is pinned independently in dev,
production, and CI-service Compose files with no agreement check. The
production volume-section predicate also mixes four `and`/`or` clauses without
parentheses. It is correct today but hard to review and weakly protected
against option changes.

## Current state

- `scripts/check_postgres_image.py` has a pure `check()` plus root unit tests.
- Redis `8.8.0` appears in three generated Compose files.
- `prod.yaml:237` controls whether a top-level `volumes:` mapping is rendered.
- Root/generated `zizmor.yaml` duplication is deliberate and out of scope.

## Commands you will need

| Purpose | Command | Expected |
|---|---|---|
| Root tests | `rtk uvx pytest tests -q` or locked equivalent after plan 012 | pass |
| Compose render | `rtk docker compose -f .docker/compose/prod.yaml --env-file=.env config` | valid |
| Root pre-commit | `rtk uvx pre-commit run --all-files` or locked equivalent | pass |

## Scope

**In scope**:
- rename/generalize `scripts/check_postgres_image.py` and its tests, or add a
  parallel Redis checker
- `.pre-commit-config.yaml`
- `{{cookiecutter.project_slug}}/.docker/compose/*.yaml`
- root tests for volume predicates

**Out of scope**:
- YAML anchors/Compose `extends` deduplication.
- Root/generated zizmor consolidation.
- A generic parser for every Jinja conditional file.

## Git workflow

Do not commit or push unless explicitly requested.

## Steps

### Step 1: Add Redis drift tests

Extend the existing pure-check pattern to require one Redis tag and agreement
across dev, prod, and CI-service Compose. Test missing canonical tag, missing
file tag, and mismatch with path-specific messages. Keep PostgreSQL behavior
unchanged.

**Verify**: a deliberately changed Redis fixture fails.

### Step 2: Wire the fail-closed pre-commit check

Rename the checker to a service-image name only if every entry point/test is
updated atomically; otherwise add a sibling checker. Keep `always_run` because
template files are globally excluded from ordinary root hooks.

**Verify**: root pre-commit reports the exact drifted file in a negative test.

### Step 3: Clarify and test the volume predicate

Parenthesize the Jinja expression at `prod.yaml:237` to make precedence
explicit without changing truth values. Add a root rendering test covering the
minimal cases that should and should not emit top-level volumes: all external
with S3/no Traefik, local media only, Postgres only, Redis only, and ACME only.

**Verify**: rendered YAML is valid and expected named volumes exist exactly.

## Test plan

Pure unit tests for tag extraction/agreement plus Cookiecutter render tests for
the volume truth table.

## Done criteria

- [ ] Redis pin drift fails root pre-commit.
- [ ] Existing PostgreSQL guard remains green.
- [ ] Volume predicate is parenthesized and truth-table tested.
- [ ] Representative Compose configs validate.

## STOP conditions

- Generalizing the checker obscures existing PostgreSQL error messages.
- Parenthesizing changes any rendered combination.
- A volume case requires a full Cartesian option matrix.

## Maintenance notes

Every newly repeated service image must join an agreement checker in the same
change.
