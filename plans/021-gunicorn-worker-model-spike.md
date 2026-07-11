# Plan 021: Measure and decide the production Gunicorn worker model

> **Executor instructions**: This is an investigate/decision plan. Do not
> switch production workers unless the measured decision gate is satisfied.
>
> **Drift check (run first)**: `rtk git diff --stat b367191..HEAD -- '{{cookiecutter.project_slug}}/.docker/scripts/gunicorn.sh' '{{cookiecutter.project_slug}}/src/' '{{cookiecutter.project_slug}}/.docker/compose/prod.yaml' '{{cookiecutter.project_slug}}/README.md'`

## Status

- **Priority**: P3
- **Effort**: M
- **Risk**: MED
- **Depends on**: none
- **Category**: perf, direction
- **Planned at**: commit `b367191`, 2026-07-10

## Why this matters

Gunicorn uses `uvicorn_worker.UvicornWorker` while every first-party endpoint
is synchronous. Django bridges sync views through thread-sensitive ASGI paths,
which may cap useful concurrency per worker while retaining ASGI overhead. The
actual effect depends on Django/Uvicorn/Gunicorn behavior and must be measured,
not inferred into an unsafe worker swap.

## Current state

- `gunicorn.sh:12-14` selects UvicornWorker and `config.asgi`.
- No first-party `async def` endpoint exists.
- The template may still need ASGI for future websockets/async downstream code;
  that product direction is not currently documented.

## Commands you will need

| Purpose | Command | Expected |
|---|---|---|
| Bake | `rtk uvx cookiecutter . -o /tmp/plan-021 --no-input` | created |
| Build | `rtk docker compose -f .docker/compose/prod.yaml --env-file=.env build api` | exit 0 |
| Tests | `rtk uv run pytest` | pass |

## Scope

**In scope**:
- disposable benchmark files outside the source branch
- `docs/decisions/gunicorn-worker-model.md` (create if decision is accepted)
- production worker files only after explicit decision gate

**Out of scope**:
- Converting views to async.
- Benchmarking on a developer laptop and presenting absolute capacity claims.
- Adding a permanent load-test dependency without approval.

## Git workflow

Do not commit benchmark artifacts or runtime changes unless the maintainer
approves the measured verdict. Never push disposable benchmark branches.

## Steps

### Step 1: Define representative workloads

Benchmark liveness, a database-backed authenticated notes list, and one slow
sync operation simulated only in a disposable benchmark branch. Use fixed
worker count, CPU quota, connection count, warmup, duration, and database
state. Record latency percentiles, throughput, errors, CPU, and memory.

**Verify**: repeated baseline runs vary by less than 10%; otherwise fix the
environment before comparing.

### Step 2: Compare worker models

Compare current UvicornWorker/ASGI with Gunicorn `gthread`/WSGI at at least two
thread counts. Keep timeouts, max requests, graceful shutdown, and image
dependencies equivalent. Run graceful termination and health checks for each.

**Verify**: raw results and commands are captured in the decision document.

### Step 3: Decide with an explicit threshold

Recommend switching only if gthread improves representative concurrent sync
throughput or p95 latency by at least 20% without worse errors/shutdown/memory,
and if maintainers accept losing default ASGI capability. Otherwise retain
UvicornWorker and close the finding as not worth changing.

**Verify**: decision document records verdict, evidence, tradeoffs, and a
revisit trigger.

### Step 4: Implement only an approved switch

If the gate passes and the maintainer approves, change worker class/entrypoint,
update dependencies, tests, Docker smoke, README, and AGENTS. Otherwise make no
runtime change.

**Verify**: full baked tests/pre-commit and production smoke pass.

## Test plan

Use repeated fixed-duration trials with identical CPU/memory/worker limits.
Exercise health, database-backed sync work, graceful termination, error rate,
and resource use. Preserve raw commands/results in the decision document.

## Done criteria

- [ ] Reproducible benchmark commands/results exist.
- [ ] A keep/switch decision uses the stated threshold.
- [ ] Runtime changes occur only after approval.
- [ ] Decision includes ASGI capability tradeoff and revisit trigger.

## STOP conditions

- Benchmark variance remains above 10%.
- A downstream requirement for websockets/async is discovered.
- Worker comparison changes more than one major variable at once.

## Maintenance notes

Revisit when first-party async endpoints appear or Django changes sync-to-ASGI
execution semantics.
