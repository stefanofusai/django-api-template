# Plan 015: Mount the business API at /api/v1/ with an unversioned ops API, so v2 is a two-line addition

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving to the
> next step. If anything in the "STOP conditions" section occurs, stop and
> report — do not improvise. When done, update the status row for this plan
> in `plans/README.md` — unless a reviewer dispatched you and told you they
> maintain the index.
>
> **Drift check (run first)**: `git diff --stat baf91ce..HEAD -- '{{cookiecutter.project_slug}}/src/apps/api/' '{{cookiecutter.project_slug}}/src/config/urls.py' '{{cookiecutter.project_slug}}/tests/' '{{cookiecutter.project_slug}}/README.md' '{{cookiecutter.project_slug}}/AGENTS.md'`
> This plan EXPECTS Plan 002's drift (health endpoint/schema/test). Compare
> the "Current state" excerpts against the live code; on any OTHER mismatch,
> treat it as a STOP condition.

## Status

- **Priority**: P2
- **Effort**: S–M
- **Risk**: MED (URL restructure; every consumer of `/api/*` paths inside the repo must move in the same change)
- **Depends on**: 002 (health endpoint should exist so the ops surface is complete; see "If 002 has not run" note). Run BEFORE 014 (docs finalization).
- **Category**: tech-debt / architecture
- **Planned at**: commit `baf91ce`, 2026-07-04

## Why this matters

Every route today mounts at bare `/api/` with no version segment. The first
breaking change in a real project then forces either breaking clients in
place or a painful late retrofit of `/v1`-`/v2` routing — the same
"decide before it hurts" class of problem as the custom user model. The fix
is cheap now and expensive later, which is exactly what a template should
absorb.

Design decision (settled here so the executor doesn't relitigate):
**operational probes stay unversioned; business endpoints get versioned.**
`/api/health` and `/api/ready` are infrastructure contracts — compose
healthchecks, load balancers, and Plan 013's smoke test reference them, and
none of those should ever churn on an API version bump. So this plan splits
the single `NinjaAPI` into:

- `ops_api`, mounted at `/api/` — health + ready, stable forever.
- `v1_api`, mounted at `/api/v1/` — empty today; the mount point, docs page,
  and test scaffolding all exist so the first business endpoint (and later a
  `v2_api`) drops in with no restructuring.

Adding v2 later = one `NinjaAPI` instance + one `path()` line; that is the
"everything is ready" criterion.

## Important context: this is a cookiecutter template

- Project code lives under the literal `{{cookiecutter.project_slug}}/` dir —
  quote it in shell. Preserve Jinja placeholders verbatim.
- Verification = bake (`uvx cookiecutter . --no-input -o <dir>`) + baked
  suite (`uv run pytest`, 100% coverage) + baked pre-commit.

## Current state

(As of `baf91ce`; Plan 002 adds `routes/health.py`, `schemas/health.py`, a
health test, and mounts `health_router` — fold that in.)

- `{{cookiecutter.project_slug}}/src/apps/api/api.py` (whole file):

  ```python
  from ninja import NinjaAPI

  from config.pyproject import project_name, project_version

  from .routes import ready_router

  api = NinjaAPI(title=project_name, version=str(project_version))
  api.add_router("", ready_router)
  ```

- `{{cookiecutter.project_slug}}/src/config/urls.py` (whole file):

  ```python
  from django.contrib import admin
  from django.urls import path

  from apps.api.api import api

  urlpatterns = [
      path("admin/", admin.site.urls),
      path("api/", api.urls),
  ]
  ```

- `{{cookiecutter.project_slug}}/tests/conftest.py` — fixture:

  ```python
  @pytest.fixture
  def api_client() -> TestClient:
      return TestClient(api)
  ```

- `{{cookiecutter.project_slug}}/tests/integration/api/schema_test.py` —
  schemathesis against `"/api/openapi.json"` via `from_wsgi`.
- `{{cookiecutter.project_slug}}/tests/unit/api/api_test.py` — asserts
  `api.title == project_name` and `api.version == str(project_version)`.
- `{{cookiecutter.project_slug}}/tests/integration/api/request_id_test.py` —
  hits `/api/missing` (a 404 path; unaffected by this plan).
- README documents `/api/docs`, `/api/ready` (and `/api/health` after 002).
- django-ninja constraint: multiple `NinjaAPI` instances need distinct URL
  namespaces or system check `ninja.E001`/namespace collisions occur — set
  `urls_namespace` explicitly on both instances.
- Infra references that this plan must NOT move: compose healthchecks
  (`/api/health` after 002, `/api/ready` before), `SECURE_REDIRECT_EXEMPT`
  regexes in `environments/prod.py`, Plan 013's probes. Keeping ops at
  `/api/` means **zero changes** to compose, settings, Dockerfile, or
  workflows — verify that stays true (`git status` at the end).
- Conventions (AGENTS.md): routers mounted at resource prefixes; alphabetical
  ordering where dependency order doesn't matter; no config-value-only tests.

**If 002 has not run yet** (check `plans/README.md`): execute this plan with
`ready_router` only — everywhere the steps mention health, skip it; Plan
002's executor will then add health to `ops_api` (its "Current state" will
have drifted — leave a note in the index row telling 002's executor that the
mount target is now `ops_api` in `api.py`).

## Commands you will need

| Purpose | Command | Expected on success |
|---------|---------|---------------------|
| Bake | `uvx cookiecutter . --no-input -o $BAKE` | exit 0 |
| Tests | `cd $BAKE/my-project && uv run pytest` | all pass, 100% |
| Hooks | `cd $BAKE/my-project && git add -A && uv run pre-commit run --all-files` | all pass |
| URL smoke (inside bake) | `uv run python manage.py check` | no issues (catches ninja namespace collisions) |

## Suggested executor toolkit

- Authoritative reference for the multi-instance pattern this plan uses:
  <https://django-ninja.dev/guides/versioning/> — it documents the exact
  constraint ("different `version`s or different `urls_namespace`s") and the
  per-version `path()` mounting that Steps 1–2 implement.

## Scope

**In scope**:
- `{{cookiecutter.project_slug}}/src/apps/api/api.py`
- `{{cookiecutter.project_slug}}/src/config/urls.py`
- `{{cookiecutter.project_slug}}/tests/conftest.py`
- `{{cookiecutter.project_slug}}/tests/unit/api/api_test.py`
- `{{cookiecutter.project_slug}}/tests/integration/api/schema_test.py`
- `{{cookiecutter.project_slug}}/tests/integration/api/versioning_test.py` (create)
- `{{cookiecutter.project_slug}}/README.md`
- `{{cookiecutter.project_slug}}/AGENTS.md` (one bullet)

**Out of scope**:
- Compose files, `prod.py`, workflows, Dockerfile — the ops paths don't move;
  if you find yourself editing any of these, the design is being violated.
- Any business endpoint for v1 — it stays deliberately empty.
- Header/content-negotiation versioning schemes — URL-path versioning is the
  decided approach.
- Moving `/api/health`/`/api/ready` under `/v1` — explicitly rejected
  (infrastructure contracts stay unversioned).

## Git workflow

- Branch: `advisor/015-api-v1-versioning`
- Conventional commit, e.g. `feat: mount business API at /api/v1 with unversioned ops API`
- Do NOT push or open a PR unless the operator instructed it.

## Steps

### Step 1: Split the API objects

Rewrite `src/apps/api/api.py`:

```python
from ninja import NinjaAPI

from config.pyproject import project_name, project_version

from .routes import health_router, ready_router

ops_api = NinjaAPI(
    title=f"{project_name} (operations)",
    urls_namespace="ops",
    version=str(project_version),
)
ops_api.add_router("", health_router)
ops_api.add_router("", ready_router)

v1_api = NinjaAPI(
    title=project_name,
    urls_namespace="v1",
    version="1.0.0",
)
```

Notes: alphabetical constants order would put `ops_api` before `v1_api`
anyway; drop `health_router` if 002 hasn't run. `v1_api.version` is the API
contract version ("1.0.0"), intentionally decoupled from the package version
that `ops_api` carries — this is the one place the two concepts diverge, and
the point of the plan.

### Step 2: Mount both

`src/config/urls.py`:

```python
from django.contrib import admin
from django.urls import path

from apps.api.api import ops_api, v1_api

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", ops_api.urls),
    path("api/v1/", v1_api.urls),
]
```

**Verify**: bake → `uv run python manage.py check` → no issues (a namespace
collision would surface here as ninja errors).

### Step 3: Update fixtures and existing tests

- `tests/conftest.py`: keep `api_client` bound to the ops instance (existing
  ready/health tests keep working unchanged), and add a `v1_client`:

  ```python
  from apps.api.api import ops_api, v1_api

  @pytest.fixture
  def api_client() -> TestClient:
      return TestClient(ops_api)

  @pytest.fixture
  def v1_client() -> TestClient:
      return TestClient(v1_api)
  ```

  (Fixtures alphabetized; `v1_client` is consumed by Step 4's test so the
  fixture — and thus the import — is exercised, keeping coverage at 100%.)
- `tests/unit/api/api_test.py`: update to the split objects — assert
  `ops_api.title` embeds `project_name` and `ops_api.version ==
  str(project_version)`; assert `v1_api.title == project_name` and
  `v1_api.version == "1.0.0"`. (These remain structural assertions on the
  objects the app builds, matching the file's existing pattern.)
- `tests/integration/api/schema_test.py`: the schemathesis fixture stays on
  `"/api/openapi.json"` (ops schema — where all real operations live today).
  No change needed; confirm it still collects and passes.

### Step 4: Version-surface integration test

Create `tests/integration/api/versioning_test.py`:

```python
from http import HTTPStatus
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from django.test import Client
    from ninja.testing import TestClient


def test_v1_api_exposes_openapi_schema_at_versioned_path(client: Client) -> None:
    response = client.get("/api/v1/openapi.json")

    assert response.status_code == HTTPStatus.OK
    assert response.json()["info"]["version"] == "1.0.0"


def test_v1_api_serves_no_operations_when_template_is_fresh(
    v1_client: TestClient,
) -> None:
    response = v1_client.get("/does-not-exist")

    assert response.status_code == HTTPStatus.NOT_FOUND
```

(The first uses Django's `client` fixture — full URLconf path, proving the
mount; the second exercises the `v1_client` fixture. Names/alphabetization
per AGENTS.md.)

**Verify**: bake → `uv run pytest` → all pass, 100% coverage.

### Step 5: Optionally point schemathesis at v1 too — verify, don't assume

In the bake, temporarily parametrize a second schemathesis fixture against
`"/api/v1/openapi.json"` and run it. If schemathesis collects zero operations
gracefully (suite still passes), keep it in the template with a one-line
comment ("exercises every v1 operation as they are added"). If it errors on
an empty schema, drop it and note in the plan's index row that v1 contract
testing starts when the first endpoint lands (the ops schema test remains).

### Step 6: Documentation

- `README.md`: update endpoint list — ops docs at `/api/docs`, versioned API
  docs at `/api/v1/docs`; state the rule: "operational probes are
  unversioned; business endpoints live under `/api/v1/`. To introduce v2,
  create a `v2_api = NinjaAPI(urls_namespace="v2", version="2.0.0")` and
  mount it at `path("api/v2/", v2_api.urls)`."
- `AGENTS.md`, under "Django And Configuration": add "Mount business routers
  on `v1_api` (under `/api/v1/`); `ops_api` is reserved for operational
  probes and must stay unversioned."

**Verify**: `uv run pre-commit run markdownlint --all-files` in bake → passes.

### Step 7: Full verification loop

**Verify**: fresh bake → `uv run pytest` → all pass, 100%;
`git add -A && uv run pre-commit run --all-files` → all pass;
`git status` in the TEMPLATE repo → only the in-scope files changed
(especially: no compose/settings/workflow diffs).

## Test plan

- `versioning_test.py` (Step 4): versioned schema reachable with the right
  contract version; empty v1 404s cleanly.
- Updated `api_test.py`: both instances carry the intended title/version
  split.
- Existing ready/health/request-id/schemathesis tests: unchanged behavior —
  they prove the ops surface didn't move.

## Done criteria

- [ ] `grep -n "api/v1/" '{{cookiecutter.project_slug}}/src/config/urls.py'` → one mount
- [ ] `grep -n "urls_namespace" '{{cookiecutter.project_slug}}/src/apps/api/api.py'` → two distinct namespaces
- [ ] Baked project: `/api/ready` (and `/api/health` if 002 ran) still served at UNVERSIONED paths (existing integration tests pass unchanged)
- [ ] Baked project: `curl`-equivalent test proves `/api/v1/openapi.json` → 200 with `info.version == "1.0.0"`
- [ ] `uv run pytest` → all pass, 100%; `pre-commit run --all-files` → all pass
- [ ] No compose/settings/workflow files modified (`git status`)
- [ ] `plans/README.md` status row updated (note the 002 interplay if executed out of order)

## STOP conditions

- ninja raises namespace/registry errors that explicit `urls_namespace`
  values don't resolve — report the exact error; do not fall back to a single
  instance with path prefixes.
- Any existing test needs its requested PATH changed (other than imports/
  fixtures) — that means an ops endpoint moved; the design forbids it.
- Schemathesis on the ops schema stops collecting after the split — report;
  the `from_wsgi("/api/openapi.json", ...)` target should be unaffected.

## Maintenance notes

- The v2 recipe is the README paragraph from Step 6 — keep it accurate; it is
  the deliverable.
- When the first real v1 endpoint lands: mount its router on `v1_api`, and
  enable/add the v1 schemathesis fixture (Step 5) if it wasn't kept.
- Plan 013's smoke test could add a `/api/v1/openapi.json` probe once this
  lands — one-line follow-up, noted here rather than editing 013
  retroactively.
- Deprecating v1 someday = removing one `path()` + one instance; the ops API
  never participates in that lifecycle.
