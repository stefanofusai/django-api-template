# Plan 008: Close the test-suite gaps (v1 contract, docs gating, reload leak)

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving to the
> next step. If anything in the "STOP conditions" section occurs, stop and
> report — do not improvise. When done, update the status row for this plan
> in `plans/README.md` — unless a reviewer dispatched you and told you they
> maintain the index.
>
> **Drift check (run first)**:
> `git diff --stat d333a73..HEAD -- '{{cookiecutter.project_slug}}/tests'`
> If any in-scope file changed since this plan was written, compare the
> "Current state" excerpts against the live code before proceeding; on a
> mismatch, treat it as a STOP condition.

## Status

- **Priority**: P2
- **Effort**: S
- **Risk**: LOW
- **Depends on**: 001 preferred first (suite then runs on Postgres);
  hard dependency: none
- **Category**: tests
- **Planned at**: commit `d333a73`, 2026-07-05

## Why this matters

Three verified gaps in an otherwise strict (100%-coverage) suite:

1. **Schemathesis covers only the internal API.** The contract-test
   fixture loads `/api/openapi.json` (health + ready). `/api/v1/` — the
   surface users actually build on — is never property-tested; the first
   real endpoint a user adds gets zero Schemathesis coverage unless they
   discover and rewire the fixture.
2. **The staff-gating of API docs in prod is untested.** `prod.py` swaps
   `API_DOCS_DECORATOR` to `staff_member_required`, but no test proves a
   staff-decorated NinjaAPI actually denies anonymous access to
   `/docs` and `/openapi.json` — a ninja upgrade regressing
   `docs_decorator` coverage (especially of `openapi.json`) would ship
   silently.
3. **A test leaks reloaded global state.** `pagination_test.py` calls
   `importlib.reload(ninja.conf)` under `@override_settings` and never
   reloads it back, leaving the worker's `ninja.conf.settings` built
   from test-modified settings — a latent cross-test flake under
   pytest-randomly/xdist.

## Current state

Cookiecutter template; generated project under the literal
`{{cookiecutter.project_slug}}/` directory. Test conventions (baked
`AGENTS.md`, Testing section): test files end `_test.py`; test names
`test_<subject>_<expected_behavior>_when_<condition>`; functions
alphabetized within a file; use `@override_settings` (never patch
`django.conf.settings`); `tests/integration/` and `tests/unit/` get
markers auto-applied by `tests/conftest.py`.

- `{{cookiecutter.project_slug}}/tests/integration/api/schema_test.py` —
  full content:

  ```python
  import pytest
  import schemathesis
  from schemathesis import Case

  from config.wsgi import application


  @pytest.fixture
  def api_schema() -> object:
      return schemathesis.openapi.from_wsgi(
          "/api/openapi.json",
          application,
      )


  schema = schemathesis.pytest.from_fixture("api_schema")


  @pytest.mark.django_db
  @schema.parametrize()
  def test_api_schema_conforms_to_openapi_contract(case: Case) -> None:
      case.call_and_validate()
  ```

- `{{cookiecutter.project_slug}}/src/apps/api/api.py` — two NinjaAPI
  instances: `internal_api` (docs at `/api/docs`, schema at
  `/api/openapi.json`; health+ready routers) and `v1_api` (mounted at
  `/api/v1/`, currently **zero routes**, so `/api/v1/openapi.json` has
  `"paths": {}`). Both take
  `docs_decorator=import_string(settings.API_DOCS_DECORATOR)` resolved
  at import time.

- `{{cookiecutter.project_slug}}/src/config/settings/environments/prod.py:12`
  — `API_DOCS_DECORATOR = "django.contrib.admin.views.decorators.staff_member_required"`.
  `core.py` default: `"apps.api.docs.public"` (identity decorator).

- `{{cookiecutter.project_slug}}/tests/integration/api/docs_test.py` —
  two tests asserting 200 under the identity decorator only.

- `{{cookiecutter.project_slug}}/tests/unit/api/pagination_test.py` —
  full content is in your checkout; the offending shape:

  ```python
  @override_settings(NINJA_PAGINATION_MAX_LIMIT=TEST_MAX_LIMIT)
  def test_bounded_pagination_caps_limit_at_max_limit_when_setting_is_finite() -> None:
      importlib.reload(ninja.conf)
      spec = importlib.util.spec_from_file_location(
          "_pagination_with_finite_max_limit",
          pagination.__file__,
      )
      ...
  ```

  (The module-from-spec part is fine — it never touches
  `sys.modules['apps.api.pagination']`; only the `ninja.conf` reload
  leaks.)

- `{{cookiecutter.project_slug}}/tests/factories.py` — `UserFactory`
  (email, username). `is_staff` can be set per-test via pytest-factoryboy
  attribute parametrization: the `user` fixture is registered in
  `tests/conftest.py` via `register(UserFactory)`, so
  `@pytest.mark.parametrize("user__is_staff", [True])` works.

- Coverage measures `src/` only (`--cov=src`), so new files under
  `tests/` don't affect the coverage gate.

## Commands you will need

| Purpose | Command | Expected on success |
|---------|---------|---------------------|
| Bake | `uvx cookiecutter . --no-input -o /tmp/plan008` | baked |
| Suite | `uv sync --locked && uv run pytest` (Postgres per plan 001 if landed) | pass, 100% cov |
| Single file | `uv run pytest tests/unit/api/pagination_test.py -p no:randomly` | pass |
| Repeat for order bugs | `uv run pytest tests/unit/api -p no:cacheprovider` several times | pass every time |
| Baked pre-commit | `git add -A && uv run pre-commit run --all-files` | exit 0 |

## Scope

**In scope** (template `tests/` tree only):

- `{{cookiecutter.project_slug}}/tests/integration/api/schema_test.py`
- `{{cookiecutter.project_slug}}/tests/integration/api/docs_gating_test.py`
  (create)
- `{{cookiecutter.project_slug}}/tests/integration/api/prod_docs_urls.py`
  (create — helper urlconf, not a test module)
- `{{cookiecutter.project_slug}}/tests/unit/api/pagination_test.py`

**Out of scope** (do NOT touch):

- `src/**` — no production code changes in this plan.
- `docs_test.py` (the identity-decorator tests remain valid).
- `conftest.py`, `factories.py`.

## Git workflow

- Work directly on `main`; do not create or switch to a plan branch unless the
  operator explicitly asks.
- Do NOT commit, push, or open a PR unless the operator explicitly instructs it.
- If asked to commit, use a conventional commit such as
  `test: cover v1 contract, prod docs gating, fix reload leak`.

## Steps

### Step 1: Extend Schemathesis to the v1 schema

Parametrize the fixture over both OpenAPI documents:

```python
@pytest.fixture(params=["/api/openapi.json", "/api/v1/openapi.json"])
def api_schema(request: pytest.FixtureRequest) -> object:
    return schemathesis.openapi.from_wsgi(request.param, application)
```

Empirical check required: the v1 schema currently has zero operations.
Run `uv run pytest tests/integration/api/schema_test.py -v` and observe
how schemathesis handles the empty schema:

- If it collects zero cases for the v1 param (or emits a skip), done —
  the coverage activates automatically when v1 routes appear (plan 009).
- If it ERRORS on an empty schema, fall back to: keep the original
  single-URL fixture AND add a plain test
  `test_v1_openapi_schema_loads_into_schemathesis_when_template_is_fresh`
  that asserts `schemathesis.openapi.from_wsgi("/api/v1/openapi.json",
  application)` returns a schema object, plus a comment in the file
  saying to parametrize the fixture once v1 has routes. Record which
  branch you took in the completion report.

**Verify**: `uv run pytest tests/integration/api/schema_test.py` →
passes (with the internal-API cases still executing).

### Step 2: Prove staff gating denies anonymous docs access

Create `tests/integration/api/prod_docs_urls.py` (helper urlconf that
mirrors the production wiring — decorator resolved via `import_string`
exactly like `api.py` does):

```python
from django.urls import path
from django.utils.module_loading import import_string
from ninja import NinjaAPI

PROD_DOCS_DECORATOR = "django.contrib.admin.views.decorators.staff_member_required"

api = NinjaAPI(
    docs_decorator=import_string(PROD_DOCS_DECORATOR),
    urls_namespace="prod-docs",
)

urlpatterns = [path("api/", api.urls)]
```

Create `tests/integration/api/docs_gating_test.py` with three tests
(names alphabetized; `django.test.Client` via the pytest-django `client`
fixture; `admin/` is not in this urlconf, so assert the redirect
*target prefix* only):

1. `test_api_docs_redirect_anonymous_user_when_decorator_requires_staff`
   — `@override_settings(ROOT_URLCONF="tests.integration.api.prod_docs_urls")`;
   `client.get("/api/docs")` → status 302 and
   `response["Location"].startswith("/admin/login/")`.
2. `test_api_docs_return_ok_for_staff_user_when_decorator_requires_staff`
   — `@pytest.mark.django_db` +
   `@pytest.mark.parametrize("user__is_staff", [True])`; use the `user`
   fixture, `client.force_login(user)`, expect 200.
3. `test_openapi_schema_redirects_anonymous_user_when_decorator_requires_staff`
   — same as (1) for `/api/openapi.json`. This is the load-bearing
   assertion: it locks in that ninja's `docs_decorator` covers the
   schema document, not just the docs UI.

Known limitation to note in a file comment: this exercises the
decorator-resolution mechanism with the same import path prod uses, not
`prod.py` itself (prod overlay modules are coverage-omitted and resolved
at import time in `api.py`).

**Verify**: `uv run pytest tests/integration/api/docs_gating_test.py -v`
→ 3 passed. Negative check: temporarily change `PROD_DOCS_DECORATOR` in
the helper to `"apps.api.docs.public"` → tests 1 and 3 fail; revert.

### Step 3: Fix the ninja.conf reload leak

Rework the finite-max-limit test to restore global state
deterministically. Replace the decorator with a fixture (module-local,
in the same file):

```python
@pytest.fixture
def finite_pagination_max_limit() -> Iterator[None]:
    with override_settings(NINJA_PAGINATION_MAX_LIMIT=TEST_MAX_LIMIT):
        importlib.reload(ninja.conf)
        yield

    importlib.reload(ninja.conf)
```

(`Iterator` from `collections.abc`.) The test takes the fixture as a
parameter and keeps its current body minus the inline reload. After the
fixture exits, `ninja.conf.settings` is rebuilt from unmodified Django
settings — assert that too, at the end of the OTHER (unset) test or via
a final check inside the fixture-using test:
`assert math.isinf(ninja.conf.settings.PAGINATION_MAX_LIMIT)` placed in
the unset-limit test to pin the invariant regardless of execution order
— note pytest-randomly randomizes order, so the invariant must hold
before AND after; run the file repeatedly to confirm.

**Verify**:

```shell
uv run pytest tests/unit/api/pagination_test.py -v          # pass
uv run pytest tests/unit/api -v                              # pass
for i in 1 2 3 4 5; do uv run pytest tests/unit -q || break; done  # 5/5 pass
```

### Step 4: Full verification

`uv run pytest` (full suite, 100% coverage), then
`git add -A && uv run pre-commit run --all-files` in the baked project.
Apply the final changes to the TEMPLATE files (remember: you develop
against a bake, but the deliverable edits live under
`{{cookiecutter.project_slug}}/tests/` — none of these files contain
Jinja, so they are copyable as-is), re-bake fresh, and rerun the suite.

**Verify**: fresh bake passes suite + pre-commit; root
`pre-commit run --all-files` exits 0.

## Test plan

This plan IS tests. New: 3 gating tests + (per Step 1 branch) the v1
schema coverage; changed: pagination reload hygiene. Model style on
`docs_test.py` (structure) and `models_test.py` (fixture usage).

## Done criteria

- [ ] Schemathesis fixture covers `/api/v1/openapi.json` (or the
      documented fallback is in place with its loads-test)
- [ ] `docs_gating_test.py`: 3 tests pass; negative check demonstrated
      once
- [ ] `pagination_test.py` leaves `ninja.conf` restored (5/5 repeated
      runs pass)
- [ ] Full suite passes at 100% coverage on a fresh bake
- [ ] Baked + root pre-commit exit 0; `git status` clean outside scope
- [ ] `plans/README.md` status row updated

## STOP conditions

- Schemathesis raises on the parametrized empty schema AND the fallback
  in Step 1 also fails — report the schemathesis behavior verbatim.
- The staff-gating test finds ninja does NOT protect `/openapi.json`
  behind `docs_decorator` — that is a real security finding; stop and
  report immediately (do not "fix" it in this plan).
- Repeated runs in Step 3 still flake — the leak is bigger than
  `ninja.conf`; report which module differs.

## Maintenance notes

- Plan 009 (example v1 resource) activates the v1 Schemathesis coverage
  for real and must declare response schemas (401/404) so
  `call_and_validate` passes — its plan accounts for this.
- If `API_DOCS_DECORATOR`'s prod value ever changes, update
  `PROD_DOCS_DECORATOR` in the helper urlconf to match (grep for it).
- Reviewer: check the helper urlconf isn't collected as a test module
  (no `_test.py` suffix — correct as specified).
