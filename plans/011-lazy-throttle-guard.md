# Plan 011: Short-circuit the throttle guard before resolving the session user

> **Executor instructions**: Preserve behavior exactly; this is an evaluation
> order optimization. Run all gates and update the index.
>
> **Drift check (run first)**: `rtk git diff --stat b367191..HEAD -- '{{cookiecutter.project_slug}}/src/apps/api/throttling.py' '{{cookiecutter.project_slug}}/tests/api/unit/throttling_test.py'`

## Status

- **Priority**: P2
- **Effort**: S
- **Risk**: LOW
- **Depends on**: none
- **Category**: perf
- **Planned at**: commit `b367191`, 2026-07-10

## Why this matters

`PublicAPIThrottleMiddleware` is global in throttling bakes. Its guard calls
`all()` on an eagerly built tuple, so `request.user.is_authenticated` resolves
even when throttling is disabled, the method is OPTIONS, or the path is admin,
static, health, or readiness. A session-bearing off-API request can therefore
load the session/user unnecessarily.

## Current state

`throttling.py:100-108` currently returns:

```python
return all(
    (
        settings.API_THROTTLE_ANON_RATE is not None,
        not getattr(request.user, "is_authenticated", False),
        request.method != "OPTIONS",
        request.path_info.startswith("/api/v1/"),
    )
)
```

Unit middleware patterns live in `tests/api/unit/throttling_test.py`.

## Commands you will need

| Purpose | Command | Expected |
|---|---|---|
| Bake | `rtk uvx cookiecutter . -o /tmp/plan-011 --no-input use_example_api=yes api_throttling=basic` | created |
| Focused | `rtk uv run pytest tests/api/unit/throttling_test.py -q` | pass |
| Full | `rtk uv run pytest` | pass, coverage 100% |

## Scope

**In scope**:
- `{{cookiecutter.project_slug}}/src/apps/api/throttling.py`
- `{{cookiecutter.project_slug}}/tests/api/unit/throttling_test.py`

**Out of scope**:
- Anonymous-budget semantics or cache format.
- Trusted proxy identity (plan 002).
- Avoiding user resolution for actual `/api/v1/` requests.

## Git workflow

Do not commit or push unless explicitly requested.

## Steps

### Step 1: Add a lazy-user regression test

Use `SimpleLazyObject` backed by a helper that calls `pytest.fail`. Send an
off-API request through the middleware with throttling configured and assert
200 without resolving the sentinel. Add equivalent cheap cases for an unset
rate and OPTIONS if coverage requires them.

**Verify**: the off-API test fails on current code by resolving the sentinel.

### Step 2: Replace the eager tuple

Use an `and` chain ordered cheapest-first: configured rate, method, path, then
authenticated user. Keep the same four predicates and results.

**Verify**: focused tests pass; existing integration throttle tests are
unchanged and pass.

### Step 3: Run session and JWT bakes

Verify session+throttle and JWT+throttle combinations with full pytest; run
pre-commit in one representative bake and at root.

**Verify**: all pass at 100% coverage.

## Test plan

Pin non-resolution off path, with disabled runtime rate, and for OPTIONS; keep
all existing 429 behavior untouched.

## Done criteria

- [ ] `request.user` is the final evaluated predicate.
- [ ] Off-API and disabled-throttle paths do not resolve it.
- [ ] Session and JWT suites pass.

## STOP conditions

- Any existing integration behavior changes.
- Django resolves `SimpleLazyObject` before this middleware for the test path.

## Maintenance notes

Future guard conditions must keep pure settings/request metadata checks before
session-backed user access.
