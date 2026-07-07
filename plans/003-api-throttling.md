# Plan 003: Add `api_throttling=basic` for public API routes

> **For agentic workers:** REQUIRED SUB-SKILL: Use
> superpowers:subagent-driven-development (recommended) or
> superpowers:executing-plans to implement this plan task-by-task. Steps use
> checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an opt-in basic throttle for public `/api/v1/` routes while
leaving internal health/readiness probes unthrottled.

**Architecture:** Add `api_throttling = ["none", "basic"]`. Implement a small
local fixed-window throttle using Django cache, with authenticated user identity
when available and client IP fallback. Apply it to `v1_api` operations through a
Ninja-compatible decorator or wrapper, not to `internal_api`.

**Tech Stack:** Django cache, Django Ninja, pytest, Redis/locmem cache, uv,
pre-commit.

---

## Status

- **Priority**: P2
- **Effort**: L
- **Risk**: MED
- **Depends on**: plans/001-api-auth-token.md
- **Category**: direction
- **Planned at**: commit `9d129c1`, 2026-07-08

## Drift Check

```shell
git diff --stat 9d129c1..HEAD -- cookiecutter.json "{{cookiecutter.project_slug}}/src/apps/api/api.py" "{{cookiecutter.project_slug}}/src/apps/api/routes.py" "{{cookiecutter.project_slug}}/src/config/settings/components/cache.py" "{{cookiecutter.project_slug}}/tests/api/integration/health_test.py"
```

Stop if `v1_api` or `internal_api` mounting changed.

## Current State

- `internal_api` owns health and readiness routes.
- `v1_api` owns public business routers.
- Django cache is configured from `CACHE_URL`; tests use `locmemcache://`.
- There is no DRF dependency and no existing throttle utility.

## Scope

**In scope**:
- `cookiecutter.json`
- `.github/workflows/ci.yaml`
- `README.md`
- `{{cookiecutter.project_slug}}/README.md`
- `{{cookiecutter.project_slug}}/.env.example`
- `{{cookiecutter.project_slug}}/src/apps/api/throttling.py` (create)
- `{{cookiecutter.project_slug}}/src/apps/api/api.py`
- `{{cookiecutter.project_slug}}/src/config/settings/components/core.py`
- `{{cookiecutter.project_slug}}/tests/api/integration/throttling_test.py` (create)
- `{{cookiecutter.project_slug}}/tests/api/unit/throttling_test.py` (create)

**Out of scope**:
- Throttling `/api/health`, `/api/ready`, admin, static, or media.
- Per-route product quotas.
- Sliding-window or distributed strict quotas.
- A third-party rate-limit dependency unless the local cache approach cannot
  satisfy tests.

## Steps

### Task 1: Add the knob and settings

- [ ] Add `api_throttling = ["none", "basic"]`, default `none`.
- [ ] Add prompt text: `none` disables throttling, `basic` enables cache-backed
      public API throttling.
- [ ] In `components/core.py`, add under the basic gate:

```python
API_THROTTLE_ANON_RATE = env("API_THROTTLE_ANON_RATE", default="60/minute")
API_THROTTLE_USER_RATE = env("API_THROTTLE_USER_RATE", default="600/minute")
```

- [ ] In `.env.example`, add optional commented overrides under a public API
      block:

```dotenv
# Optional anonymous public API throttle rate.
# API_THROTTLE_ANON_RATE=60/minute
# Optional authenticated public API throttle rate.
# API_THROTTLE_USER_RATE=600/minute
```

### Task 2: Implement rate parsing and cache keys

- [ ] Create `src/apps/api/throttling.py` under the basic gate.
- [ ] Implement `parse_rate(rate: str) -> tuple[int, int]` supporting
      `second`, `minute`, `hour`, and `day` singular/plural units.
- [ ] Implement `get_throttle_identity(request)`:
  - authenticated user: `user:<pk>`
  - anonymous fallback: `ip:<client-ip>`
- [ ] Implement `client-ip` from `HTTP_X_FORWARDED_FOR` first, then
      `REMOTE_ADDR`, using only the first forwarded value.
- [ ] Unit tests:
  - `60/minute` becomes `(60, 60)`.
  - `10/hour` becomes `(10, 3600)`.
  - bad rates raise `ValueError`.
  - authenticated user identity wins over IP.
  - first forwarded IP is used.

**Verify**:

```shell
rtk uv run pytest --no-cov tests/api/unit/throttling_test.py
```

Expected: unit tests pass.

### Task 3: Implement fixed-window throttling

- [ ] Add `check_throttle(request) -> None`.
- [ ] Use a cache key shaped like:

```python
f"api-throttle:{identity}:{window_start}:{limit}:{period}"
```

- [ ] Use `cache.add(key, 1, timeout=period)` for the first hit and
      `cache.incr(key)` for later hits.
- [ ] When the count exceeds the limit, raise:

```python
HttpError(429, "Request was throttled.")
```

- [ ] Use authenticated rate when `request.user.is_authenticated` is true,
      otherwise anonymous rate.

### Task 4: Apply throttling to public API routes

- [ ] In `apps/api/api.py`, keep `internal_api` unchanged.
- [ ] Apply throttling only to `v1_api`. Prefer a small helper that wraps
      operations or routers once. If Django Ninja cannot wrap at API/router
      level cleanly, apply a decorator to each public operation and document
      that explicit route-level application is the project convention.
- [ ] Do not throttle CORS `OPTIONS` preflight if plan 002 has already landed.

**Verify**:

```shell
rtk uv run pytest --no-cov tests/api/integration/throttling_test.py
```

Expected: throttling integration tests pass.

### Task 5: Add integration tests

- [ ] Test that `/api/v1/` notes requests hit the limit and then return `429`.
- [ ] Test authenticated users get separate counters.
- [ ] Test anonymous IPs get separate counters.
- [ ] Test `/api/health` and `/api/ready` continue returning success beyond
      the public API limit.

Use tiny override rates in tests, for example `2/minute`, and clear the cache
between tests.

### Task 6: Document and add CI coverage

- [ ] Update README variable tables.
- [ ] Add CI case after plan 001 lands:

```yaml
- case: example-token-auth-throttling
  project_name: My Project
  extra-args: use_example_api=yes api_auth=token api_throttling=basic
  slug: my-project
```

- [ ] Keep matrix cases sorted by `case`.

## Test Plan

- Default bake: no throttling files/settings, full tests pass.
- `use_example_api=yes api_auth=token api_throttling=basic`: unit tests,
  integration tests, generated pre-commit, and full pytest pass.
- Optional session auth bake with throttling: confirm user-based identity still
  works through session auth if the example remains session-based.

## Done Criteria

- [ ] `api_throttling` defaults to `none`.
- [ ] Internal probes are not throttled.
- [ ] Public API routes return `429` after the configured limit.
- [ ] Authenticated identity and IP fallback are both tested.
- [ ] CORS preflight is not consumed as normal quota when plan 002 is present.
- [ ] Root and generated checks pass.

## STOP Conditions

- Django Ninja cannot support a maintainable public-route throttle hook.
- Tests require sleeping or wall-clock timing.
- Correct behavior requires a third-party dependency.
- Health/readiness become throttled.

## Maintenance Notes

This is a basic abuse guard, not a billing-grade quota system. If future users
need strict distributed throttling, replace this with a dedicated service or
well-supported dependency in a separate plan.
