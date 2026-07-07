# Plan 019: Harden the browser-facing surfaces — bound the client-supplied request ID, and decide on a CSP for admin/docs

> **Executor instructions**: This plan has a small, do-it part (Part A: request
> ID) and a **design-decision** part (Part B: CSP) that ends in a recommendation
> + STOP, not necessarily a merge. Run every verification command. If anything in
> "STOP conditions" occurs, stop and report. When done, update this plan's status
> row in `plans/README.md` — unless a reviewer dispatched you and told you they
> maintain the index.
>
> **Drift check (run first)**:
> `git diff --stat ae42991..HEAD -- "{{cookiecutter.project_slug}}/src/apps/api/signals.py" "{{cookiecutter.project_slug}}/src/config/settings/components/middleware.py" "{{cookiecutter.project_slug}}/src/config/settings/components/apps.py" "{{cookiecutter.project_slug}}/tests/api/integration/request_id_test.py"`
> On a mismatch with "Current state", STOP.
>
> **Naming caution**: Part B's deliverable is a NEW file,
> `plans/019-csp-DESIGN.md`. Do not overwrite this plan file.

## Status

- **Priority**: P3
- **Effort**: S (Part A) + S (Part B design doc)
- **Risk**: LOW (Part A) / decision-only (Part B)
- **Depends on**: none
- **Category**: security
- **Planned at**: commit `ae42991`, 2026-07-07

## Repository context (read before anything else)

This is a **Cookiecutter template** (source under `{{cookiecutter.project_slug}}/`,
**quote it in shell**; files rendered except `.github/workflows/*` and
`.agents/*`). The baked project enforces **100% coverage** on `src/` — any code
you add under `src/` needs a test in the same plan. Tests live in
`tests/<app>/{unit,integration}/`; names `test_<subject>_<expected>_when_<cond>`.
Verification means baking: `uvx cookiecutter . --no-input -o /tmp/bake`; baked
tests need a reachable `postgres:18.4`.

**Respect the documented stance.** The **repo-root** `README.md:57` (the
template's own README — NOT the generated project's README, which has no such
line) states: "The template deliberately ships no CORS or throttling defaults;
add them when a real consumer and policy exist." A Content-Security-Policy is
adjacent to that decision — Part B must treat "leave it out, document instead"
as a legitimate outcome, not a failure.

## Why this matters

The API is JSON, but it serves two HTML surfaces: the Django admin and the
django-ninja Swagger UI (both gated behind `staff_member_required` in prod).
Two defense-in-depth gaps:

- **Part A — client-controlled correlation ID (small, clear win).** The
  `X-Request-ID` response header (and the `request_id` bound on every structlog
  line) reflects an inbound client-supplied value verbatim. HTTP header CRLF
  injection is blocked by Django and structlog JSON-encodes safely, so severity
  is low — but a caller can spoof another request's correlation ID and can send
  an unbounded-length value that bloats logs/headers. Bounding/validating the
  inbound ID removes both.
- **Part B — no CSP/Permissions-Policy (decision).** `SecurityMiddleware` is
  configured with nosniff/HSTS/XFO/SSL-redirect but there is no CSP. If an XSS
  sink ever reaches the admin or Swagger UI (e.g. via a dependency), nothing
  contains it. A conservative CSP scoped to those surfaces would help — but a
  too-tight CSP breaks Swagger's inline scripts, and this cuts against the
  documented minimalism. So Part B produces a recommendation, not an automatic
  merge.

## Current state

### `{{cookiecutter.project_slug}}/src/apps/api/signals.py` (full)

```python
import structlog
from django.dispatch import receiver
from django.http import HttpResponseBase  # noqa: TC002
from django_structlog import signals


@receiver(signals.update_failure_response)
def add_request_id_to_failure_response(sender, logger, response, **kwargs): ...


@receiver(signals.bind_extra_request_finished_metadata)
def add_request_id_to_response(sender, logger, response, **kwargs): ...


# Utils


def _add_request_id(logger, response) -> None:
    request_id = structlog.contextvars.get_merged_contextvars(logger)["request_id"]
    response.headers["X-Request-ID"] = request_id
```

(Signatures elided; the `request_id` originates from django-structlog's
`RequestMiddleware`, which honors an inbound `X-Request-ID` — confirmed by
`tests/api/integration/request_id_test.py`, which asserts an inbound value is
preserved verbatim in the response.)

### `{{cookiecutter.project_slug}}/src/config/settings/components/middleware.py` (full)

```python
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django_structlog.middlewares.RequestMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]
```

No `django-csp` in `components/apps.py` `INSTALLED_APPS`; no CSP middleware.

**Where the inbound ID is honored**: django-structlog's `RequestMiddleware` reads
the request-id header. Its behavior is configured via settings
(`DJANGO_STRUCTLOG_*`). **Read the installed django-structlog** in a bake
(`.venv/.../django_structlog/middlewares/request.py`) to confirm the exact
setting name and format-validation hook before Part A — do not guess the knob.

**Conventions**: Ruff `ALL`; never `from __future__ import annotations`; add env
vars only for secrets/topology/sizing; pin any new dependency to an exact latest
version.

## Commands you will need

| Purpose | Command | Expected |
|---------|---------|----------|
| Bake default | `uvx cookiecutter . --no-input -o /tmp/bake` | project |
| Inspect django-structlog | (in bake) read `.venv/lib/python*/site-packages/django_structlog/middlewares/request.py` | confirm request-id handling + settings |
| Baked tests | `cd /tmp/bake/my-project && DATABASE_URL=postgres://postgres:postgres@localhost:5432/postgres uv run pytest` | 100% cov, all pass |
| Baked pre-commit | `cd /tmp/bake/my-project && git add -A && uv run pre-commit run --all-files` | exit 0 |
| Root pre-commit | (repo root) `uvx pre-commit run --all-files` | exit 0 |

## Scope

**Part A in scope**:
- The request-id validation point. **Prefer** django-structlog's built-in
  request-id settings (a length cap / format guard configured in
  `components/logging.py` or wherever request-id is configured) over new code. If
  and only if no built-in exists, add a minimal guard in `signals.py`'s
  `_add_request_id` (cap length; if the inbound value is not a well-formed
  UUID/trace ID, fall back to the generated one) — with a test.
- `{{cookiecutter.project_slug}}/tests/api/integration/request_id_test.py` — add
  cases for an over-long and a malformed inbound ID.

**Part B in scope**:
- `plans/019-csp-DESIGN.md` (create) — the CSP recommendation (see Part B steps).
- Only if the recommendation is "ship it" AND the executor is explicitly told to
  proceed: `components/apps.py`, a CSP config component, and a docs line. Do NOT
  ship a CSP without the recommendation being accepted (STOP after the design).

**Out of scope**:
- CORS/throttling (deliberately omitted per the repo-root README's Design
  Decisions).
- Changing the request-id *response* header name or the logging pipeline shape.
- Adding a CSP that is not scoped/tested against the Swagger UI (would break docs).

## Git workflow

- Work directly on `main`. Do NOT branch/commit/push/PR unless told. If asked to
  commit: Conventional Commits, e.g. `feat: bound the client-supplied request id`.

## Steps

### Part A

#### Step A1: Find the right validation point

Read the installed django-structlog `RequestMiddleware`. Determine whether it
exposes a setting to (a) cap the accepted request-id length and/or (b) validate
its format, or whether it always trusts the inbound header. Record what you find.

**Verify**: you can state, from the source, exactly how the inbound `X-Request-ID`
becomes `request_id`.

#### Step A2: Bound the inbound ID

- If django-structlog has a built-in cap/validation setting: enable it in the
  appropriate settings component (probably `components/logging.py`), choosing a
  conservative max length (e.g. 200 chars) and, if supported, a UUID/trace-ID
  format guard.
- Else: in `signals.py`, before reflecting/binding, cap the length and, if the
  value is not a well-formed ID, use the generated fallback. Keep it tiny and
  Ruff-clean; only comment to state the constraint (why the cap exists).

#### Step A3: Test it

In `tests/api/integration/request_id_test.py`, add:
- `test_request_id_response_is_bounded_when_client_sends_overlong_value` — send a
  multi-kilobyte `X-Request-ID`, assert the reflected/logged ID is capped (or
  replaced).
- `test_request_id_is_regenerated_when_client_sends_malformed_value` (only if you
  chose format validation) — send a non-UUID value, assert a fresh ID is used.

While you are in this file, also fix a pre-existing coverage gap the audit
found: `test_failure_response_includes_request_id_from_context` calls the
receiver `add_request_id_to_failure_response(object(), logger, response)`
**directly**, so the `@receiver(signals.update_failure_response)` wiring in
`signals.py` is never exercised — a django-structlog bump that renames or
drops that signal would pass tests while breaking error-response correlation
in production. Convert it (or add a sibling test) to drive a real failing
request through the stack — or at minimum emit
`signals.update_failure_response.send(...)` — and assert the `X-Request-ID`
header, so the signal registration itself is under test.

Model structure on the existing tests in that file. Keep coverage at 100%.

**Verify**: `cd /tmp/bake/my-project && DATABASE_URL=… uv run pytest tests/api/integration/request_id_test.py` passes; full baked suite stays 100%.

### Part B

#### Step B1: Prototype and measure a CSP against Swagger

In a **scratch bake**, add a conservative CSP (via `django-csp`'s latest release
or a small static-header middleware) and load the Swagger UI at `/api/docs`
(staff-authenticated). Determine the minimal policy that does not break the docs
UI or admin (Swagger typically needs `script-src`/`style-src` allowances).
Record the exact policy and what it took to keep Swagger working.

#### Step B2: Write the recommendation

Create `plans/019-csp-DESIGN.md`: the minimal working policy, the dependency
weight (`django-csp` version + Django 6 compat), whether it should be a new knob
(`use_csp`) or an always-on default, how it interacts with the documented
minimalism stance, and an explicit recommendation (ship default / ship opt-in /
document-only). Include the scratch diff as an appendix.

#### Step B3: STOP for the decision

Do not merge a CSP into the committed template until the recommendation is
accepted. Report the recommendation and the open question (default vs knob vs
docs-only).

## Test plan

- **Part A**: new integration tests in `request_id_test.py` (overlong, malformed);
  full baked suite at 100%.
- **Part B**: verification is the scratch prototype loading Swagger without
  breakage; no committed test until the design is accepted.

## Done criteria

ALL must hold:

- [ ] **Part A**: inbound `X-Request-ID` is length-bounded (and format-guarded if chosen); new tests cover overlong/malformed input; the failure-response receiver is exercised via real signal dispatch (not a direct call); baked suite passes at 100%.
- [ ] **Part A**: baked + root pre-commit exit 0.
- [ ] **Part B**: `plans/019-csp-DESIGN.md` exists with a working minimal Swagger-compatible policy, dependency assessment, and an explicit recommendation.
- [ ] **Part B**: no CSP merged into the committed template unless the recommendation was accepted and the executor was told to proceed.
- [ ] No out-of-scope files modified (`git status`); `plans/README.md` status row updated.

## STOP conditions

Stop and report (do not improvise) if:

- Part A would require changing the response-header name or the logging pipeline
  shape (out of scope).
- No conservative CSP keeps the Swagger UI working without effectively disabling
  it (report — the recommendation is then "document-only" or "admin-only CSP").
- The maintainer's intent on CSP-vs-minimalism is unclear — surface it as the
  design's first open question.

## Maintenance notes

- Part A and Part B are independent — Part A can land alone as a clean small win;
  Part B is a decision.
- If a CSP is later shipped, it must be re-tested against Swagger on every
  django-ninja upgrade (the docs UI's inline assets can change).
- A reviewer should confirm Part A caps length without breaking legitimate
  upstream trace-ID propagation (don't over-constrain the format if real callers
  send W3C `traceparent`-style IDs).
