# Plan 027: Validate demand for a staging settings and Compose overlay

> **Executor instructions**: This is a low-confidence direction spike. Do not
> add a staging knob or duplicate production configuration without evidence.
>
> **Drift check (run first)**: `rtk git diff --stat b367191..HEAD -- 'cookiecutter.json' '{{cookiecutter.project_slug}}/src/config/settings/environments/' '{{cookiecutter.project_slug}}/.docker/compose/' '{{cookiecutter.project_slug}}/README.md'`

## Status

- **Priority**: P3
- **Effort**: M
- **Risk**: MED
- **Depends on**: none
- **Category**: direction
- **Planned at**: commit `b367191`, 2026-07-10

## Why this matters

The template has dev, CI, and production environments but no staging surface.
A staging overlay could support pre-production smoke and migration rehearsal,
but it may merely duplicate production with different secrets and expand every
knob's test matrix. Evidence of a distinct configuration contract is required.

## Current state

- Production topology is already configurable for external/bundled services
  and Traefik.
- `DJANGO_ENV` selects split-settings overlays.
- Deployment uses one production Compose file plus CI service stand-ins.
- No user intent document requests staging.

## Commands you will need

| Purpose | Command | Expected |
|---|---|---|
| Prototype bake | `rtk uvx cookiecutter . -o /tmp/plan-027 --no-input` | created |
| Deploy checks | `rtk ./.github/scripts/deploy-check.sh` | exit 0 |
| Compose render | `rtk docker compose -f .docker/compose/prod.yaml -f "$OVERLAY" --env-file=.env config` | valid |

## Scope

**In scope**:
- interviews/issues/downstream usage evidence
- disposable overlay prototype
- `docs/decisions/staging-overlay.md` (create)

**Out of scope**:
- Adding staging solely as a copy of production.
- New secrets or public staging defaults.
- A third deployment orchestrator.

## Git workflow

Keep the overlay prototype disposable. Commit only the decision document unless
the maintainer approves a staging contract.

## Steps

### Step 1: Identify distinct staging requirements

Collect concrete needs such as non-production domains, separate Sentry
environment, lower worker sizing, sandbox email, production-like security,
database migration rehearsal, or ephemeral review environments. Reject needs
already satisfied by production env values.

### Step 2: Prototype the smallest overlay

If at least two real distinct requirements remain, create a disposable
`staging.py` importing/mutating production-safe components and a Compose
override rather than duplicating `prod.yaml`. Require secure cookies, debug
off, real secret guards, and separate observability environment.

**Verify**: staging passes deploy checks and cannot boot with template secrets.

### Step 3: Estimate lifecycle cost

Map every new file, environment variable, matrix case, workflow, documentation
section, and branch-protection check. Compare with documenting “use prod config
with staging secrets/domain.”

### Step 4: Record adopt/defer verdict

Adopt only when distinct requirements outweigh lifecycle cost. Otherwise
document the supported production-config-for-staging recipe and a revisit
trigger.

## Test plan

For an adopted prototype, test secret boot guards, debug off, secure cookies,
separate domain/Sentry environment, migration checks, Compose rendering, and
full pytest/pre-commit. For defer, run the documented prod-with-staging-env
recipe once.

## Done criteria

- [ ] Real distinct staging requirements are documented or absence is explicit.
- [ ] Prototype reuses production security rather than copying it.
- [ ] Full lifecycle/matrix cost is estimated.
- [ ] Adopt/defer verdict has a revisit trigger.

## STOP conditions

- No distinct requirement survives comparison with production env overrides.
- Prototype weakens production security checks for convenience.
- Supporting staging requires duplicating the full Compose file.

## Maintenance notes

Low-confidence verdicts should default to defer. Revisit after a downstream
project demonstrates repeated staging-specific customization.
