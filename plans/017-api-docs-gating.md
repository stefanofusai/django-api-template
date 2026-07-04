# Plan 017: Gate API docs behind staff in production and document the auth decision point

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving to the
> next step. If anything in the "STOP conditions" section occurs, stop and
> report — do not improvise. When done, update the status row for this plan
> in `plans/README.md` — unless a reviewer dispatched you and told you they
> maintain the index.
>
> **Drift check (run first)**: `git diff --stat 2849304..HEAD -- '{{cookiecutter.project_slug}}/src/apps/api/' '{{cookiecutter.project_slug}}/src/config/settings/' '{{cookiecutter.project_slug}}/tests/' '{{cookiecutter.project_slug}}/README.md' '{{cookiecutter.project_slug}}/AGENTS.md'`
> This plan EXPECTS drift from plans 002 (health) and 015 (ops/v1 split) —
> the steps handle both shapes. On any OTHER mismatch with "Current state",
> STOP.

## Status

- **Priority**: P2
- **Effort**: S–M
- **Risk**: LOW–MED (changes what anonymous users can see in prod; ci/dev behavior unchanged)
- **Depends on**: 015 preferred first (both API instances get gated in one pass); edits `prod.py` — run sequentially with 002/007/009, never in a parallel worktree
- **Category**: security
- **Planned at**: commit `2849304`, 2026-07-04

## Why this matters

`NinjaAPI()` is constructed with no `auth` and no docs restriction, so
`/api/docs` and `/api/openapi.json` are publicly readable in production —
and this is the scaffold every future endpoint joins, meaning the whole API
surface gets published by default as the project grows. The fix is a
production-gated docs decorator (staff-only), with dev/ci left open so local
work and the schemathesis contract test keep functioning. The second half of
the finding — no auth story at all — is deliberately handled as
*documentation of the decision point*, not code: a health-check-only skeleton
gets no auth class, but the place to add one (`NinjaAPI(auth=...)`) must be
written down where the first endpoint author will look.

Design constraint that shapes the implementation: the 100% branch-coverage
gate. A naive `staff_member_required if settings.X else None` at module scope
leaves the prod arm uncovered under ci tests and fails the gate. Instead the
decorator is a **settings-provided import path**, resolved unconditionally —
no branch in `api.py`:

- base settings: `API_DOCS_DECORATOR = "apps.api.docs.public"` (an identity
  decorator — dev/ci docs stay open),
- prod overlay: `API_DOCS_DECORATOR =
  "django.contrib.admin.views.decorators.staff_member_required"`.

## Important context: this is a cookiecutter template

- Project code lives under the literal `{{cookiecutter.project_slug}}/` dir —
  quote it in shell. Preserve Jinja placeholders verbatim.
- Verification = bake + baked suite (100% coverage) + baked pre-commit.

## Current state

(As of `2849304`. Plan 002 adds a health router; plan 015 splits into
`ops_api` at `/api/` + `v1_api` at `/api/v1/` — apply this plan's decorator
to EVERY NinjaAPI instance that exists when you execute.)

- `{{cookiecutter.project_slug}}/src/apps/api/api.py` (pre-002/015 shape):

  ```python
  from ninja import NinjaAPI

  from config.pyproject import project_name, project_version

  from .routes import ready_router

  api = NinjaAPI(title=project_name, version=str(project_version))
  api.add_router("", ready_router)
  ```

- No `docs_decorator`, `docs_url`, or `auth` anywhere:
  `grep -rn "docs_decorator\|docs_url\|auth=" '{{cookiecutter.project_slug}}/src'`
  → no matches.
- `src/config/settings/components/core.py` — alphabetized constants
  (`ALLOWED_HOSTS`, `DEBUG`, `ROOT_URLCONF`, `SECRET_KEY`, `TIME_ZONE`,
  `WSGI_APPLICATION`); new `API_DOCS_DECORATOR` sorts after `ALLOWED_HOSTS`.
- `src/config/settings/environments/prod.py` — the overlay to override in;
  new top-level names there need no `noqa` (they're assignments, not
  cross-component mutations).
- `tests/integration/api/schema_test.py` — schemathesis fetches
  `/api/openapi.json` through the WSGI app under `DJANGO_ENV=ci`; it must
  keep returning 200, which the identity decorator guarantees.
- django-ninja's `NinjaAPI(docs_decorator=...)` wraps the docs view AND the
  OpenAPI JSON view — **verify this empirically in Step 4**; if only
  `/docs` is gated and `/openapi.json` is not, that is a STOP condition
  (the fallback decision — also setting `openapi_url=None` in prod — belongs
  to the maintainer because it breaks schema-driven clients).
- `staff_member_required` redirects anonymous users to the admin login
  (302), which exists in this template (`/admin/`).
- Conventions: AGENTS.md — operational constants fixed in code (this is one:
  no new env var), Ruff `ALL`, no config-value-only tests.

## Commands you will need

| Purpose | Command | Expected on success |
|---------|---------|---------------------|
| Bake | `uvx cookiecutter . --no-input -o $BAKE` | exit 0 |
| Tests | `cd $BAKE/my-project && uv run pytest` | all pass, 100% |
| Hooks | `cd $BAKE/my-project && git add -A && uv run pre-commit run --all-files` | all pass |
| Prod gating probe (inside bake) | Step 4 command | `302 302` with admin-login redirects |

## Scope

**In scope**:
- `{{cookiecutter.project_slug}}/src/apps/api/docs.py` (create)
- `{{cookiecutter.project_slug}}/src/apps/api/api.py`
- `{{cookiecutter.project_slug}}/src/config/settings/components/core.py`
- `{{cookiecutter.project_slug}}/src/config/settings/environments/prod.py`
- `{{cookiecutter.project_slug}}/tests/integration/api/docs_test.py` (create)
- `{{cookiecutter.project_slug}}/README.md`
- `{{cookiecutter.project_slug}}/AGENTS.md` (one bullet)

**Out of scope**:
- Adding any actual auth class (`HttpBearer`, API keys, sessions) — no
  protected endpoint exists; the deliverable is the documented decision
  point.
- Disabling docs entirely (`docs_url=None`) — staff-gating was chosen so
  operators keep the docs in prod.
- Admin hardening (plan 002's README note covers it).

## Git workflow

- Branch: `advisor/017-api-docs-gating`
- Conventional commit, e.g. `feat: gate API docs behind staff in production`
- Do NOT push or open a PR unless the operator instructed it.

## Steps

### Step 1: The identity decorator

Create `src/apps/api/docs.py`:

```python
from collections.abc import Callable


def public(view: Callable) -> Callable:
    return view
```

(If Ruff demands more precise typing under `ALL`, use the
`Callable[..., object]` form it suggests — keep the function a pure
pass-through.)

### Step 2: Settings wiring

- `components/core.py`: add, in alphabetical position:

  ```python
  API_DOCS_DECORATOR = "apps.api.docs.public"
  ```

- `environments/prod.py`: add, in the file's constant ordering:

  ```python
  API_DOCS_DECORATOR = "django.contrib.admin.views.decorators.staff_member_required"
  ```

### Step 3: Resolve it in api.py — no branch

In `src/apps/api/api.py`, resolve once at module scope and pass to every
NinjaAPI instance (both `ops_api` and `v1_api` if 015 landed; the single
`api` otherwise):

```python
from django.conf import settings
from django.utils.module_loading import import_string

docs_decorator = import_string(settings.API_DOCS_DECORATOR)

ops_api = NinjaAPI(
    ...,
    docs_decorator=docs_decorator,
)
```

**Verify**: bake → `uv run pytest` → all pass, 100% (under ci the identity
decorator resolves and wraps; `docs.py` gets covered via the import +
call — if the coverage report flags `docs.py`, the Step 5 test closes it).

### Step 4: Prove prod gating empirically — including openapi.json

Inside a fresh bake, with prod-like env (`DJANGO_ENV=prod
ALLOWED_HOSTS=testserver AWS_STORAGE_BUCKET_NAME=b CACHE_URL=locmemcache://
CSRF_TRUSTED_ORIGINS=https://example.com DATABASE_URL=sqlite:///:memory:
SECRET_KEY=<long-random>` plus `SENTRY_DSN`/`RESEND_API_KEY` dummies if
007/009 landed):

```
uv run python -c "
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()
from django.test import Client
client = Client()
docs = client.get('/api/docs', secure=True)
schema = client.get('/api/openapi.json', secure=True)
print(docs.status_code, schema.status_code)
print(docs.headers.get('Location', ''))
"
```

(`secure=True` bypasses `SECURE_SSL_REDIRECT`; `ALLOWED_HOSTS=testserver`
satisfies the test client's Host.) Expected: `302 302` and a Location
pointing at the admin login. **If the schema line prints 200, ninja's
`docs_decorator` does not cover the OpenAPI view on this version — STOP and
report** (decision needed: accept schema exposure or set `openapi_url=None`
in prod). If 015 landed, repeat for `/api/v1/docs` and
`/api/v1/openapi.json` → also `302 302`.

### Step 5: CI-mode regression test

Create `tests/integration/api/docs_test.py`:

```python
from http import HTTPStatus
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from django.test import Client


def test_api_docs_are_public_when_docs_decorator_is_identity(
    client: Client,
) -> None:
    response = client.get("/api/docs")

    assert response.status_code == HTTPStatus.OK


def test_openapi_schema_is_public_when_docs_decorator_is_identity(
    client: Client,
) -> None:
    response = client.get("/api/openapi.json")

    assert response.status_code == HTTPStatus.OK
```

(The prod arm is covered by Step 4's checks + the CI deploy check loading
prod settings; a pytest for the 302 would require module reloads for no
additional guarantee.)

**Verify**: bake → `uv run pytest` → all pass, 100%.

### Step 6: Document the auth decision point

- README (API/docs section): "API docs and the OpenAPI schema are public in
  dev and staff-only in production (`API_DOCS_DECORATOR`). The API itself
  ships unauthenticated: when you add the first endpoint that needs
  protection, set a global auth class — `NinjaAPI(auth=...)` — or per-router
  auth; see <https://django-ninja.dev/guides/authentication/>."
- AGENTS.md, under "## Django And Configuration": "The API has no default
  auth. Endpoints requiring protection must add ninja auth (global
  `auth=` on the API instance, or per-router/per-operation); never ship a
  mutating endpoint unauthenticated."

**Verify**: `uv run pre-commit run markdownlint --all-files` in bake → passes.

### Step 7: Full verification loop

**Verify**: fresh bake → `uv run pytest` → all pass, 100%;
`git add -A && uv run pre-commit run --all-files` → all pass; Step 4 probe →
`302 302`.

## Test plan

- `docs_test.py` (Step 5): ci-mode docs + schema stay public (this is also
  the regression net for the schemathesis fixture, which depends on an open
  `/api/openapi.json` in ci).
- Prod gating: Step 4's empirical probe (both paths, both instances if 015
  landed).
- Existing suite unchanged — schemathesis proves the identity decorator
  didn't alter the ci contract surface.

## Done criteria

- [ ] `grep -rn "docs_decorator" '{{cookiecutter.project_slug}}/src/apps/api/api.py'` → resolved once, passed to every NinjaAPI instance
- [ ] `grep -n "API_DOCS_DECORATOR" '{{cookiecutter.project_slug}}/src/config/settings'` -r → base (identity) + prod (staff) definitions
- [ ] Step 4 probe prints `302 302` with an admin-login Location under prod settings
- [ ] Baked project: `uv run pytest` → all pass, 100%
- [ ] Baked project: `uv run pre-commit run --all-files` → all pass
- [ ] No files outside the in-scope list modified (`git status`)
- [ ] `plans/README.md` status row updated

## STOP conditions

- Step 4 shows `/api/openapi.json` NOT gated by `docs_decorator` (see inline
  instruction — maintainer decision required).
- `import_string` at module scope creates an import cycle (settings →
  apps.api.docs → …) — report; do not inline the decorator to dodge it.
- The schemathesis test fails under ci after Step 3 — the identity decorator
  should be transparent; a failure means ninja treats decorated docs views
  differently than assumed. Report.

## Maintenance notes

- When the first protected endpoint lands, the author should revisit whether
  staff-gated docs are still right (docs often move behind the same auth as
  the API), and add the ninja auth class per the README pointer.
- Plan 013's smoke test can add a one-line probe asserting `/api/docs`
  returns 302 in the booted prod stack — noted here as a follow-up rather
  than editing 013 retroactively.
- If a future django-ninja version changes `docs_decorator` semantics, Step
  4's probe is the canary — keep it in the PR description for reviewers.
