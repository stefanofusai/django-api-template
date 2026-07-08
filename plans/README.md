# Template Knob Implementation Plans

Clean-slate plan set created on 2026-07-08. Execute in order unless the
dependency notes say otherwise. Each executor must read the target plan fully,
honor its STOP conditions, run every verification command, and update the
status row when finished.

## Execution Order And Status

| Plan | Title | Priority | Effort | Depends on | Status |
|------|-------|----------|--------|------------|--------|
| [001](001-api-auth-token.md) | Add `api_auth=token` for the example API | P1 | L | none | DONE |
| [002](002-use-cors.md) | Add project-level `use_cors` | P1 | M | none | DONE |
| [003](003-api-throttling.md) | Add `api_throttling=basic` for public API routes | P2 | L | 001 | DONE |
| [004](004-use-csp.md) | Add project-level `use_csp` with Django native CSP | P3 | M | none | DONE |
| [005](005-notes-ninja-extra-controllers.md) | Migrate the example notes API to django-ninja-extra class-based controllers | P2 | L | none | DONE |

## Dependency Notes

- Plan 003 depends on plan 001 because throttle identity should use the
  authenticated user/token when available and fall back to IP only for anonymous
  requests.
- Plans 002 and 004 are project-level browser policy knobs. They do not depend
  on the example API.
- Keep all defaults conservative: `api_auth=session`, `use_cors=no`,
  `api_throttling=none`, and `use_csp=no`.
- Plan 005 depends on nothing directly, but touches the same
  `apps/notes/routes.py` file plan 003 will eventually touch for throttling.
  If plan 005 executes before plan 003, plan 003 must be refreshed to target
  `apps/notes/controllers.py` instead.

## Scope Decisions

- `api_auth=token` is an example-API feature in this first build. It should not
  render token models or token auth helpers when `use_example_api=no`.
- `use_cors` is global Django middleware/settings policy when enabled.
- `api_throttling=basic` applies to public `/api/v1/` business routes. It must
  not throttle `/api/health` or `/api/ready`.
- `use_csp` is global browser-surface policy when enabled. It should cover admin
  and API docs, with explicit tests for emitted headers.

## Rejected In This Set

- JWT auth and refresh tokens: too much dependency and policy surface for the
  first auth knob.
- CORS wildcard defaults: unsafe for a reusable production template.
- Throttling internal probes: breaks container/load-balancer semantics.
- `django-csp`: Django 6 has native CSP support, so no third-party dependency is
  needed for the planned CSP knob.
