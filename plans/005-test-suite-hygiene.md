# Plan 005: Test-suite hygiene — remove a framework-only test, make a vacuous assertion real, drop a dangling plan reference, and de-brittle the pagination test

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving on. If
> anything in "STOP conditions" occurs, stop and report — do not improvise. When
> done, update this plan's status row in `plans/README.md` — unless a reviewer
> dispatched you and told you they maintain the index.
>
> **Drift check (run first)**:
> `git diff --stat ae42991..HEAD -- "{{cookiecutter.project_slug}}/tests/config/unit/celery_test.py" "{{cookiecutter.project_slug}}/tests/api/integration/schema_test.py" "{{cookiecutter.project_slug}}/tests/api/unit/pagination_test.py" hooks/post_gen_project.py`
> If any changed since this plan was written, compare "Current state" against the
> live files before proceeding; on a mismatch, STOP.

## Status

- **Priority**: P2
- **Effort**: S
- **Risk**: LOW
- **Depends on**: none (but coordinates with plan 003 — both edit `hooks/post_gen_project.py`; land one, then re-check the other's excerpt)
- **Category**: tests
- **Planned at**: commit `ae42991`, 2026-07-07

## Repository context (read before anything else)

This is a **Cookiecutter template**. Source is under `{{cookiecutter.project_slug}}/`
— **quote it in shell**. Test files contain Jinja that must stay valid.

- The baked project enforces **100% coverage** on `src/`
  (`pyproject.toml`: `--cov=src --cov-fail-under=100`). Deleting a test that
  imports nothing from `src/` cannot lower coverage; changing assertions that
  exercise the same lines cannot either. Confirm with the coverage run (Step 5).
- Tests live in `tests/<app>/{unit,integration}/`; `tests/conftest.py` derives
  the `unit`/`integration` marker from the path. Test file names end `_test.py`;
  test function names follow `test_<subject>_<expected>_when_<condition>`;
  functions are alphabetized within a file (`AGENTS.md`).
- `pytest-randomly` is enabled, so tests must not depend on order or leak global
  state.
- Verification means baking: `uvx cookiecutter . --no-input -o /tmp/bake`.
  Baked tests need a reachable `postgres:18.4`.

## Why this matters

Four small test-quality issues undercut the suite's credibility on a template
whose selling point is a trustworthy 100% gate:

1. **`celery_test.py` tests Celery, not the project.** It defines a local
   `_add` task and calls `.apply()` — which runs synchronously *regardless* of
   the project's `CELERY_TASK_ALWAYS_EAGER` config or app wiring — and imports
   nothing from `src/`. It would stay green even if the project's Celery app
   were broken. The real eager path is already covered by `tasks_test.py` via
   `.delay()`. The file also carries a spurious `django_db` marker (per-test DB
   setup for a test that never touches the DB).
2. **A vacuous assertion.** `test_v1_openapi_schema_loads_into_schemathesis…`
   asserts `v1_schema is not None`, but `from_wsgi` raises on failure and never
   returns `None`, so the assertion is always true and verifies nothing about the
   fresh v1 schema.
3. **A dangling reference.** A comment in the same file points at retired
   internal "plan 009", which no longer exists (the plan set was renumbered).
   Every non-example bake ships this reference into the maintainer's private
   workflow.
4. **Brittle pagination assertions.** `pagination_test.py` indexes Pydantic
   constraint metadata positionally (`metadata[1].le`, `metadata[0].ge`). A
   future Pydantic / django-ninja / annotated-types bump that reorders or
   coalesces `FieldInfo.metadata` breaks these with a confusing
   `IndexError`/`AttributeError` rather than a real regression — a maintenance
   flake on a bleeding-edge template.

## Current state

### `{{cookiecutter.project_slug}}/tests/config/unit/celery_test.py` (full file)

```python
import pytest
from celery import shared_task

pytestmark = pytest.mark.django_db

EXPECTED_SUM = 5


@shared_task
def _add(x: int, y: int) -> int:
    return x + y


def test_shared_task_returns_result_when_executed_eagerly() -> None:
    result = _add.apply(kwargs={"x": 2, "y": 3})

    assert result.successful()
    assert result.get() == EXPECTED_SUM
```

This file is listed in `hooks/post_gen_project.py:33` for deletion when
`USE_CELERY == "none"`, inside the `REMOVED_PATHS` block:

```python
    *(
        [
            ".docker/scripts/celery-beat.sh",
            ".docker/scripts/celery-worker.sh",
            "src/config/celery.py",
            "src/config/settings/components/celery.py",
            "tests/config/unit/celery_test.py",
        ]
        if USE_CELERY == "none"
        else []
    ),
```

`tests/config/unit/` also contains `pyproject_test.py`, so the directory does not
become empty when `celery_test.py` is deleted.

### `{{cookiecutter.project_slug}}/tests/api/integration/schema_test.py` (the `use_example_api=no` tail)

```python
{%- if cookiecutter.use_example_api == "no" %}


# The v1 API currently exposes zero routes, so schemathesis has no operations
# to parametrize against `/api/v1/openapi.json` (`schema.parametrize()` fails
# the test outright with "does not match any API operations" rather than
# skipping). Once plan 009 adds v1 routes, fold this back into a single
# fixture parametrized over both `/api/openapi.json` and
# `/api/v1/openapi.json`, as the internal-API test above already exercises.
@pytest.mark.django_db
def test_v1_openapi_schema_loads_into_schemathesis_when_template_is_fresh() -> None:
    v1_schema = schemathesis.openapi.from_wsgi("/api/v1/openapi.json", application)

    assert v1_schema is not None
{%- endif %}
```

The *concept* to copy exists in `tests/api/integration/versioning_test.py`
(`test_v1_api_serves_empty_openapi_schema_when_template_is_fresh` asserts
`response.json()["info"]["version"]` and `response.json()["paths"] == {}`) —
but note it uses a plain HTTP client and `response.json()`, NOT a schemathesis
object, so it cannot tell you the schemathesis attribute name. The attribute on
the loaded schemathesis schema (`.raw_schema` or similar) must be confirmed
empirically against the installed package — see Step 2.

### `{{cookiecutter.project_slug}}/tests/api/unit/pagination_test.py` (the brittle lines)

```python
    assert limit_field.metadata[1].le == TEST_MAX_LIMIT     # line 40
    # ...
    assert limit_field.metadata[0].ge == 1                  # line 52
    assert limit_field.metadata[1].le == pagination.settings.PAGINATION_PER_PAGE   # line 53
    assert offset_field.metadata[0].ge == 0                 # line 55
    assert offset_field.metadata[1].le == pagination.settings.PAGINATION_MAX_OFFSET # line 56
```

`annotated-types` exposes `Ge` and `Le` classes; `FieldInfo.metadata` is a list
of these instances. The fix looks them up by type instead of by position.

**Conventions (from `AGENTS.md`)**: Ruff selects `ALL`; never add
`from __future__ import annotations`; only comment to state constraints code
can't show; test functions alphabetized.

## Commands you will need

| Purpose | Command | Expected |
|---------|---------|----------|
| Bake default | `uvx cookiecutter . --no-input -o /tmp/bake` | `/tmp/bake/my-project/` |
| Bake example-api | `uvx cookiecutter . --no-input -o /tmp/bake-ex use_example_api=yes` | v1 has routes → the `use_example_api=no` tail is absent |
| Bake celery-off | `uvx cookiecutter . --no-input -o /tmp/bake-nc use_celery=none` | `celery_test.py` must be absent |
| Baked tests | `cd /tmp/bake*/my-project && DATABASE_URL=postgres://postgres:postgres@localhost:5432/postgres uv run pytest` | 100% cov, all pass |
| Baked pre-commit | `cd /tmp/bake/my-project && git add -A && uv run pre-commit run --all-files` | exit 0 |
| Root pre-commit | (repo root) `uvx pre-commit run --all-files` | exit 0 |

## Scope

**In scope**:
- Delete `{{cookiecutter.project_slug}}/tests/config/unit/celery_test.py`.
- `hooks/post_gen_project.py` — remove the now-stale `celery_test.py` entry from
  `REMOVED_PATHS` (the file no longer exists to delete, so `Path(...).unlink()`
  would raise `FileNotFoundError` in a `use_celery=none` bake).
- `{{cookiecutter.project_slug}}/tests/api/integration/schema_test.py` — replace
  the vacuous assertion with a real one and remove the "plan 009" reference.
- `{{cookiecutter.project_slug}}/tests/api/unit/pagination_test.py` — look
  constraints up by type; guard the `ninja.conf` reload with try/finally.

**Out of scope**:
- `tests/core/unit/tasks_test.py` — it already covers the real eager path; leave
  it.
- Any `src/` change; any change to the Schemathesis contract test body
  (`test_api_schema_conforms_to_openapi_contract`).
- Adding new dependencies.

## Git workflow

- Work directly on `main`. Do NOT branch/commit/push/PR unless told. If asked to
  commit: Conventional Commits, e.g. `test: remove framework-only celery test and de-brittle assertions`.

## Steps

### Step 1: Delete `celery_test.py` and fix the hook

Delete `{{cookiecutter.project_slug}}/tests/config/unit/celery_test.py`. Then in
`hooks/post_gen_project.py`, remove the `"tests/config/unit/celery_test.py"`
line from the `REMOVED_PATHS` `USE_CELERY == "none"` list (leave the other four
entries). This is mandatory: `main()` calls `Path(removed_path).unlink()` with
no `missing_ok`, so a `use_celery=none` bake would crash trying to delete a file
that no longer ships.

**Verify**:
```
grep -rc "celery_test" hooks/post_gen_project.py   # expect 0
uvx cookiecutter . --no-input -o /tmp/bake-nc use_celery=none   # must succeed (no FileNotFoundError)
test ! -f /tmp/bake-nc/my-project/tests/config/unit/celery_test.py && echo OK
```

### Step 2: Make the v1-schema assertion real and drop the plan reference

In `schema_test.py`, replace the vacuous body and reword the comment. First
confirm how the loaded schemathesis schema object exposes the raw OpenAPI
document — **do this against the installed package, in a bake**:

```
cd /tmp/bake/my-project
uv run python -c "
import schemathesis
from config.wsgi import application  # match schema_test.py's import
s = schemathesis.openapi.from_wsgi('/api/openapi.json', application)
print(hasattr(s, 'raw_schema'), type(s).__name__)
"
```

(Adapt the `application` import to whatever `schema_test.py` itself imports. If
the attribute is not `raw_schema`, read
`.venv/lib/python*/site-packages/schemathesis/` to find the real accessor.)
Then assert something load-bearing about the fresh v1 schema — that it has the
expected version and zero paths, mirroring the *assertions* (not the access
mechanism) of `versioning_test.py`:

```python
# The v1 API exposes zero routes until the first business endpoint is added,
# so schemathesis has no operations to parametrize against
# `/api/v1/openapi.json` (`schema.parametrize()` fails outright with "does not
# match any API operations" rather than skipping). Assert the empty schema is
# still well-formed and served; fold this into the parametrized fixture above
# once v1 gains routes.
@pytest.mark.django_db
def test_v1_openapi_schema_is_well_formed_when_template_is_fresh() -> None:
    v1_schema = schemathesis.openapi.from_wsgi("/api/v1/openapi.json", application)

    assert v1_schema.raw_schema["info"]["version"] == "1.0.0"
    assert v1_schema.raw_schema["paths"] == {}
```

Adjust the attribute to match what the empirical check above showed — do not
guess. Rename the function to reflect the stronger assertion (keep alphabetical
ordering if there were sibling functions — here it is the only function in its
`{% if %}` branch). The `1.0.0` version string comes from
`v1_api = NinjaAPI(..., version="1.0.0", ...)` in `apps/api/api.py`.

**Verify**:
```
grep -c "plan 009" /tmp/bake/my-project/tests/api/integration/schema_test.py   # expect 0
cd /tmp/bake/my-project && DATABASE_URL=postgres://postgres:postgres@localhost:5432/postgres uv run pytest tests/api/integration/schema_test.py
```
→ passes. If `raw_schema` is the wrong attribute, the test will error — fix the
access, do not weaken the assertion back to `is not None`.

### Step 3: Look up pagination constraints by type

Import the constraint classes and search `metadata` for them instead of indexing
by position. Add at the top (Ruff-sorted):

```python
from annotated_types import Ge, Le
```

Add a small helper that extracts the bound. Per `AGENTS.md` ("Put private
helper utilities at the bottom of the file under a `# Utils` heading,
alphabetized there"), place it at the BOTTOM of the file under a `# Utils`
heading — not above the tests:

```python
def _constraint(field: object, kind: type) -> object:
    return next(m for m in field.metadata if isinstance(m, kind))
```

Then rewrite the assertions, e.g.:

```python
    assert _constraint(limit_field, Le).le == TEST_MAX_LIMIT
    # ...
    assert _constraint(limit_field, Ge).ge == 1
    assert _constraint(limit_field, Le).le == pagination.settings.PAGINATION_PER_PAGE
    assert _constraint(offset_field, Ge).ge == 0
    assert _constraint(offset_field, Le).le == pagination.settings.PAGINATION_MAX_OFFSET
```

Confirm `annotated_types` is already an available import in the baked venv (it is
a transitive dependency of pydantic/ninja; verify with
`uv run python -c "import annotated_types"` in the bake — if it is not directly
declared, prefer reading the class off `type(m).__name__ == "Le"` rather than
adding a dependency; STOP and report if unsure).

Also wrap the `importlib.reload(ninja.conf)` in the `finite_pagination_max_limit`
fixture so restoration always runs even if the reload/yield raises:

```python
@pytest.fixture
def finite_pagination_max_limit() -> Iterator[None]:
    try:
        with override_settings(NINJA_PAGINATION_MAX_LIMIT=TEST_MAX_LIMIT):
            importlib.reload(ninja.conf)
            yield
    finally:
        importlib.reload(ninja.conf)
```

**Verify**:
```
cd /tmp/bake/my-project && DATABASE_URL=postgres://postgres:postgres@localhost:5432/postgres uv run pytest tests/api/unit/pagination_test.py
```
→ passes.

### Step 4: Lint

```
cd /tmp/bake/my-project && git add -A && uv run pre-commit run --all-files
```
**Verify**: exit 0 (Ruff `ALL` + Ty clean on the edited test files).

### Step 5: Full suite at 100% on the knob states that matter

Run the full baked suite on: default, `use_example_api=yes`, and
`use_celery=none`:

```
for d in /tmp/bake /tmp/bake-ex /tmp/bake-nc; do
  (cd "$d/my-project" && DATABASE_URL=postgres://postgres:postgres@localhost:5432/postgres uv run pytest) || echo "FAIL: $d"
done
```
**Verify**: all pass at 100% coverage. Coverage must remain 100% — deleting
`celery_test.py` (which covered no `src/` lines) and editing assertions (same
lines exercised) cannot lower it. If coverage drops, STOP — something about the
assumption is wrong.

## Test plan

- Net test count: `celery_test.py` removed (−1 test); `schema_test.py` and
  `pagination_test.py` edited in place (same test count, stronger assertions).
- Structural patterns to follow: `versioning_test.py` (for the *assertions* —
  version string + empty paths; its access mechanism is `response.json()`, not
  schemathesis), existing `pagination_test.py` structure (keep it).
- Verification is the full baked `pytest` run in Step 5 across three knob states.

## Done criteria

ALL must hold:

- [ ] `{{cookiecutter.project_slug}}/tests/config/unit/celery_test.py` no longer exists; `grep -rc celery_test hooks/post_gen_project.py` == 0.
- [ ] `use_celery=none` bake succeeds (no `FileNotFoundError` in post-gen).
- [ ] `grep -rc "plan 009" "{{cookiecutter.project_slug}}/tests/"` == 0.
- [ ] `grep -c "is not None" "{{cookiecutter.project_slug}}/tests/api/integration/schema_test.py"` == 0 (the vacuous assertion is gone).
- [ ] `grep -c "metadata\[" "{{cookiecutter.project_slug}}/tests/api/unit/pagination_test.py"` == 0 (no positional metadata indexing).
- [ ] Baked `uv run pytest` passes at 100% on default, `use_example_api=yes`, and `use_celery=none` bakes.
- [ ] Baked pre-commit exits 0; root `uvx pre-commit run --all-files` exits 0.
- [ ] No `src/` file modified; no out-of-scope files modified (`git status`).
- [ ] `plans/README.md` status row updated.

## STOP conditions

Stop and report (do not improvise) if:

- Any "Current state" excerpt no longer matches the live file.
- The schemathesis loaded-schema object exposes no usable raw-document accessor
  at all (the empirical check in Step 2 finds nothing; report the real API — do
  not revert to `is not None`).
- `annotated_types` is not importable and reading the constraint class by name
  is also unreliable — report it; the maintainer may prefer a different assertion.
- Coverage drops below 100% on any bake (something about the "no coverage lost"
  assumption is false).

## Maintenance notes

- When the first real v1 route lands, fold the `use_example_api=no` v1-schema
  test into the parametrized fixture above (as the reworded comment now says
  without the internal plan number).
- A reviewer should confirm the deleted `celery_test.py` really covered no
  `src/` lines (coverage stayed 100%) and that the pagination assertions no
  longer depend on metadata ordering.
- If `tasks_test.py` is ever removed, re-evaluate whether the project needs *any*
  smoke test that the Celery app is wired and eager-configured.
