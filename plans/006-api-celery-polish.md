# Plan 006: Remove dead error schemas, document the Celery result story, and test the eager task path

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving to the
> next step. If anything in the "STOP conditions" section occurs, stop and
> report — do not improvise. When done, update the status row for this plan
> in `plans/README.md` — unless a reviewer dispatched you and told you they
> maintain the index.
>
> **Drift check (run first)**: `git diff --stat 924bfba..HEAD -- '{{cookiecutter.project_slug}}/src/apps/api/schemas/' '{{cookiecutter.project_slug}}/src/config/settings/components/celery.py' '{{cookiecutter.project_slug}}/tests/' '{{cookiecutter.project_slug}}/AGENTS.md'`
> On any change, compare "Current state" excerpts against the live code; on a
> mismatch, treat it as a STOP condition.

## Status

- **Priority**: P3
- **Effort**: S
- **Risk**: LOW
- **Depends on**: none
- **Category**: tech-debt / tests
- **Planned at**: commit `924bfba`, 2026-07-04

## Why this matters

Three small pieces of drift, bundled because each is a one-file change:

1. **Dead schemas**: `ValidationErrorSchema`/`ValidationErrorItemSchema` are
   defined and re-exported but wired to nothing — no route `response=`, no
   exception handler, so the OpenAPI contract (validated by schemathesis)
   never includes them. With only a no-input `/ready` endpoint (and `/health`
   after Plan 002), a 422 shape is speculative surface. Delete them; the
   docstring-level knowledge (Ninja emits its own 422 payload) moves to a
   comment where the next endpoint author will look.
2. **Contradictory-looking Celery result config**: the settings install and
   migrate `django_celery_results` (`CELERY_RESULT_BACKEND="django-db"`,
   `RESULT_EXTENDED`, `TRACK_STARTED`) while `CELERY_TASK_IGNORE_RESULT=True`
   discards all results by default. The audit concluded this is coherent only
   under one reading — *results are opt-in per task* — but nothing says so.
   Document that reading where the flags live.
3. **Never-run task path**: no test defines or executes a Celery task even
   though the ci overlay sets `CELERY_TASK_ALWAYS_EAGER=True` precisely to
   enable that. The first task a derived project writes runs on wiring CI has
   never executed. Add one eager-mode task test.

Note: if Plan 009 (email) also runs, it adds a real production task
(`send_email`) with its own eager test — this plan's Step 3 test still earns
its keep as the minimal wiring test that exists even if 009 is skipped, but if
009 has ALREADY landed when you execute this plan, skip Step 3 (its
`send_email` test covers the eager path) and note that in the index.

## Important context: this is a cookiecutter template

- Project code lives under the literal `{{cookiecutter.project_slug}}/` dir —
  quote it in shell. Verification = bake + run the baked suite (100% coverage
  gate).

## Current state

- `{{cookiecutter.project_slug}}/src/apps/api/schemas/errors.py` (whole file):

  ```python
  from ninja import Schema


  class ValidationErrorItemSchema(Schema):
      type: str
      loc: list[int | str]
      msg: str


  class ValidationErrorSchema(Schema):
      detail: list[ValidationErrorItemSchema]
  ```

- `{{cookiecutter.project_slug}}/src/apps/api/schemas/__init__.py` re-exports
  both in `__all__` alongside the ready schemas.
- `grep -rn ValidationError '{{cookiecutter.project_slug}}/src' '{{cookiecutter.project_slug}}/tests'`
  → matches only in the two files above (verified at planning time).
- `{{cookiecutter.project_slug}}/src/config/settings/components/celery.py`:

  ```python
  CELERY_RESULT_BACKEND = "django-db"
  CELERY_RESULT_EXTENDED = True
  ...
  CELERY_TASK_IGNORE_RESULT = True
  ...
  CELERY_TASK_TRACK_STARTED = True
  ```

- `{{cookiecutter.project_slug}}/src/config/settings/environments/ci.py:1-3`
  sets `CELERY_TASK_ALWAYS_EAGER`, `CELERY_TASK_EAGER_PROPAGATES`,
  `CELERY_TASK_STORE_EAGER_RESULT`.
- Conventions: tests named `test_<subject>_<expected>_when_<condition>`, files
  `*_test.py`, unit tests under `tests/unit/<package>/`; comments only where
  code can't speak (AGENTS.md).

## Commands you will need

| Purpose | Command | Expected on success |
|---------|---------|---------------------|
| Bake | `uvx cookiecutter . --no-input -o $BAKE` | exit 0 |
| Tests | `cd $BAKE/my-project && uv run pytest` | all pass, 100% |
| Hooks | `cd $BAKE/my-project && git add -A && uv run pre-commit run --all-files` | all pass |

## Scope

**In scope**:
- `{{cookiecutter.project_slug}}/src/apps/api/schemas/errors.py` (delete)
- `{{cookiecutter.project_slug}}/src/apps/api/schemas/__init__.py`
- `{{cookiecutter.project_slug}}/src/config/settings/components/celery.py` (comment only)
- `{{cookiecutter.project_slug}}/AGENTS.md` (one bullet)
- `{{cookiecutter.project_slug}}/tests/unit/config/celery_test.py` (create)

**Out of scope**:
- Changing any Celery flag value — this plan documents, it does not re-tune.
- Adding a custom validation-error handler — deferred until an endpoint with
  a request body exists.

## Git workflow

- Branch: `advisor/006-api-celery-polish`
- Conventional commit, e.g. `chore: drop unused error schemas and document celery result policy`
- Do NOT push or open a PR unless the operator instructed it.

## Steps

### Step 1: Delete the dead schemas

Delete `src/apps/api/schemas/errors.py`. In `schemas/__init__.py`, remove the
errors import and the two `__all__` entries, leaving:

```python
from .ready import ReadyError, ReadyErrorSchema, ReadyOkSchema

__all__ = [
    "ReadyError",
    "ReadyErrorSchema",
    "ReadyOkSchema",
]
```

(If Plan 002 already added health schemas, keep those entries — just remove
the ValidationError ones.)

**Verify**: bake → `uv run pytest` → all pass, 100% (the deletion removes
covered-but-dead lines, so coverage cannot drop).

### Step 2: Document the result policy where the flags live

In `components/celery.py`, add one comment block directly above
`CELERY_RESULT_BACKEND` (this is a constraint the code can't show — the
allowed kind of comment):

```python
# Results are opt-in per task: CELERY_TASK_IGNORE_RESULT discards results by
# default; pass ignore_result=False to @shared_task to persist that task's
# result (and its STARTED state, per CELERY_TASK_TRACK_STARTED) to
# django-celery-results.
```

In `AGENTS.md`, add one bullet under "## Django And Configuration":
"Celery results are opt-in per task: use `@shared_task(ignore_result=False)`
when a task's result must be persisted; tasks are at-least-once
(`acks_late` + `reject_on_worker_lost`), so keep them idempotent."

**Verify**: bake → `uv run pre-commit run --all-files` (markdownlint + ruff
pass).

### Step 3: Eager task wiring test (skip if Plan 009 already landed)

Create `tests/unit/config/celery_test.py`:

```python
from celery import shared_task


@shared_task
def _add(x: int, y: int) -> int:
    return x + y


def test_shared_task_returns_result_when_executed_eagerly() -> None:
    result = _add.apply(kwargs={"x": 2, "y": 3})

    assert result.successful()
    assert result.get() == 5
```

(Module-level task definition is required — Celery registers tasks at import.
`apply()` runs inline under the ci overlay's eager settings; no broker.)

**Verify**: bake → `uv run pytest tests/unit/config/celery_test.py` → passes.

### Step 4: Full verification loop

**Verify**: fresh bake → `uv run pytest` → all pass, 100%;
`git add -A && uv run pre-commit run --all-files` → all pass.

## Test plan

- Step 3's eager-execution test (new file, unit marker auto-applied by
  `tests/conftest.py`'s path-based marker hook).
- Deletion is regression-tested by the full suite + schemathesis (schema
  unchanged — the dead schemas were never in it).

## Done criteria

- [ ] `grep -rn "ValidationError" '{{cookiecutter.project_slug}}/src' '{{cookiecutter.project_slug}}/tests'` → no matches
- [ ] `components/celery.py` contains the opt-in results comment
- [ ] AGENTS.md contains the idempotency/opt-in bullet
- [ ] Baked project: `uv run pytest` → all pass, 100%
- [ ] Baked project: `uv run pre-commit run --all-files` → all pass
- [ ] No files outside the in-scope list modified (`git status`)
- [ ] `plans/README.md` status row updated

## STOP conditions

- The grep in "Current state" no longer holds (something now consumes the
  ValidationError schemas) — the deletion premise is void; report.
- The eager test fails with a task-not-registered error — Celery app wiring
  differs from the audit's understanding; report rather than forcing
  registration hacks.

## Maintenance notes

- When the first request-body endpoint is added, that author should decide the
  422 contract then — either accept Ninja's default or reintroduce an explicit
  schema wired via a validation-error handler, so schemathesis validates it.
- The opt-in results comment is the anchor for any future change to
  `CELERY_TASK_IGNORE_RESULT`; if that flag flips, delete the comment too.
