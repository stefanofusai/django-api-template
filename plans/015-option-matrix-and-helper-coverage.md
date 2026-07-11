# Plan 015: Cover supported option interactions through rendered helpers

> **Executor instructions**: Preserve existing check names and status-check
> documentation. Run every matrix-related gate and update the index.
>
> **Drift check (run first)**: `rtk git diff --stat b367191..HEAD -- '.github/workflows/ci.yaml' '{{cookiecutter.project_slug}}/.github/scripts/docker-smoke.sh' '{{cookiecutter.project_slug}}/.github/workflows/' 'tests/'`

## Status

- **Priority**: P2
- **Effort**: M
- **Risk**: LOW
- **Depends on**: plan 012
- **Category**: tests
- **Planned at**: commit `b367191`, 2026-07-10

## Why this matters

Root production smoke duplicates environment preparation instead of invoking
the rendered `docker-smoke.sh` that generated repositories use. The supported
`postgres=compose redis=external` topology is never baked or booted, and CSP
plus the example API is never pytest-tested together. These are real Jinja and
Compose interactions, not theoretical combinations.

## Current state

- `ci.yaml:272-320` contains three hand-written environment rewrite blocks.
- Generated Docker checks call `.github/scripts/docker-smoke.sh`.
- Matrix covers both external, external Postgres only, and both Compose, but
  not external Redis only.
- `csp` and `example-api` are separate bake cases.

## Commands you will need

| Purpose | Command | Expected |
|---|---|---|
| Root tests | `rtk uv run --locked pytest tests` | pass |
| Workflow checks | `rtk uv run --locked pre-commit run check-github-workflows --all-files` | pass |
| Compose config | `rtk docker compose -f .docker/compose/prod.yaml -f .docker/compose/ci-services.yaml --env-file=.env config` | valid |

## Scope

**In scope**:
- `.github/workflows/ci.yaml`
- `{{cookiecutter.project_slug}}/.github/scripts/docker-smoke.sh`
- generated deployment/Docker helper tests if needed
- a root CI-matrix invariant test (create)

**Out of scope**:
- External TLS boot testing; prior audit accepted that real-certificate gap.
- Exhaustive Cartesian product of all knobs.
- Reducing the full-suite subset (plan 018).

## Git workflow

Do not commit or push unless explicitly requested.

## Steps

### Step 1: Pin the matrix contract with root tests

Add a root test that reads `ci.yaml` and asserts named cases for:

- default;
- minimal;
- external Postgres only;
- external Redis only;
- both external;
- CSP plus example API;
- JWT plus throttling.

Keep parsing structured if the root pinned environment already has a YAML
parser; otherwise assert stable case identifiers and exact argument strings.

**Verify**: external-Redis and CSP-example assertions fail initially.

### Step 2: Execute rendered helper scripts

Replace all root smoke environment rewrite blocks with copying `.env.example`
and invoking the rendered `.github/scripts/docker-smoke.sh`. Ensure the helper
handles each smoke topology and remains the single source of knob-conditional
environment preparation. Also execute rendered `deploy-check.sh` during bake
verification.

**Verify**: no duplicated smoke `sed` block remains in root CI.

### Step 3: Add missing interaction variants

Add an `external-redis` bake and production smoke variant, plus a
`csp-example-api` pytest/pre-commit bake. Keep matrix entries alphabetized and
job names stable.

**Verify**: each new variant bakes, syncs locked dependencies, and passes its
designated checks.

### Step 4: Run local representative smoke

Run Compose smoke for default, external Redis, and both-external using the
rendered helper. Run pytest for CSP+example.

**Verify**: health/readiness and service-state assertions pass; teardown runs
even on failure.

## Test plan

Root tests pin case presence; CI runs the actual rendered helper; representative
smoke exercises Compose branch behavior. Do not duplicate helper logic in tests.

## Done criteria

- [ ] Root smoke uses rendered `docker-smoke.sh` exclusively.
- [ ] External-Redis-only is baked and booted.
- [ ] CSP+example runs pytest and pre-commit.
- [ ] Matrix invariant test prevents recurrence.
- [ ] Required status-check names remain documented.

## STOP conditions

- The rendered helper cannot support a topology without production-only
  secrets; report the missing abstraction instead of restoring inline sed.
- A new job name requires uncoordinated branch-protection changes.

## Maintenance notes

When adding a knob, decide whether it has an interaction partner and add a
named representative case plus an invariant assertion.
