# Plan 004: Make the pagination max-limit knob actually work

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving to the
> next step. If anything in the "STOP conditions" section occurs, stop and
> report — do not improvise. When done, update the status row for this plan
> in `plans/README.md` — unless a reviewer dispatched you and told you they
> maintain the index.
>
> **Drift check (run first)**: `git diff --stat 924bfba..HEAD -- '{{cookiecutter.project_slug}}/src/apps/api/pagination.py' '{{cookiecutter.project_slug}}/tests/unit/api/pagination_test.py'`
> On any change, compare "Current state" excerpts against the live code; on a
> mismatch, treat it as a STOP condition.

## Status

- **Priority**: P2
- **Effort**: S
- **Risk**: LOW
- **Depends on**: none
- **Category**: bug
- **Planned at**: commit `924bfba`, 2026-07-04

## Why this matters

`BoundedLimitOffsetPagination` computes its `limit` ceiling as
`min(settings.PAGINATION_MAX_LIMIT, settings.PAGINATION_PER_PAGE)`. Verified
against the pinned django-ninja 1.6.2 defaults: `PAGINATION_PER_PAGE=100`,
`PAGINATION_MAX_LIMIT=inf` — so the effective cap is 100. That is the intended
default (bounding ninja's unbounded `inf`), but the `min()` makes
`NINJA_PAGINATION_MAX_LIMIT` a *downward-only* knob: a project that sets it to
500 to allow bigger pages silently still gets 100. The unit test codifies the
accident. The fix keeps today's default behavior (cap = per-page when the
ninja setting is left at `inf`) while letting an explicit finite setting raise
the cap.

## Important context: this is a cookiecutter template

- Project code lives under the literal `{{cookiecutter.project_slug}}/` dir —
  quote it in shell. Verification = bake + run the baked suite.

## Current state

- `{{cookiecutter.project_slug}}/src/apps/api/pagination.py` (whole file):

  ```python
  from ninja import Field
  from ninja.conf import settings
  from ninja.pagination import LimitOffsetPagination

  PAGINATION_MAX_LIMIT = min(settings.PAGINATION_MAX_LIMIT, settings.PAGINATION_PER_PAGE)


  class BoundedLimitOffsetPagination(LimitOffsetPagination):
      class Input(LimitOffsetPagination.Input):
          limit: int = Field(
              settings.PAGINATION_PER_PAGE,
              ge=1,
              le=PAGINATION_MAX_LIMIT,
          )
          offset: int = Field(0, ge=0, le=settings.PAGINATION_MAX_OFFSET)
  ```

- `{{cookiecutter.project_slug}}/tests/unit/api/pagination_test.py` asserts
  `limit_field.metadata[1].le == min(settings.PAGINATION_MAX_LIMIT, settings.PAGINATION_PER_PAGE)`.
- ninja 1.6.2 defaults (verified in installed `ninja/conf.py`):
  `PAGINATION_MAX_OFFSET=100` (int), `PAGINATION_PER_PAGE=100`,
  `PAGINATION_MAX_LIMIT=inf` (float `inf` despite the int annotation).
- Conventions: module-scope constants block, Ruff `ALL`, no
  config-value-only tests (the existing pagination test is structural — it
  asserts the class's field metadata, which is the class's behavior; keep that
  approach).

## Commands you will need

| Purpose | Command | Expected on success |
|---------|---------|---------------------|
| Bake | `uvx cookiecutter . --no-input -o $BAKE` | exit 0 |
| Tests | `cd $BAKE/my-project && uv run pytest` | all pass, 100% |
| Focused | `cd $BAKE/my-project && uv run pytest tests/unit/api/pagination_test.py` | all pass |
| Hooks | `cd $BAKE/my-project && git add -A && uv run pre-commit run --all-files` | all pass |

## Scope

**In scope**:
- `{{cookiecutter.project_slug}}/src/apps/api/pagination.py`
- `{{cookiecutter.project_slug}}/tests/unit/api/pagination_test.py`

**Out of scope**:
- Changing the `offset` bound or overriding ninja's `PAGINATION_MAX_OFFSET`
  default (100) — document it, don't change it (Step 1 comment).
- Ninja settings defaults themselves.

## Git workflow

- Branch: `advisor/004-pagination-bounds`
- Conventional commit, e.g. `fix: let NINJA_PAGINATION_MAX_LIMIT raise the pagination cap`
- Do NOT push or open a PR unless the operator instructed it.

## Steps

### Step 1: Fix the ceiling computation

Replace the constant in `pagination.py`:

```python
import math

from ninja import Field
from ninja.conf import settings
from ninja.pagination import LimitOffsetPagination

# Ninja defaults PAGINATION_MAX_LIMIT to inf; fall back to the page size so the
# default stays bounded, while an explicit finite setting can raise the cap.
# Note: ninja's PAGINATION_MAX_OFFSET defaults to 100 — raise it via
# NINJA_PAGINATION_MAX_OFFSET when clients must page past the first ~200 rows.
PAGINATION_MAX_LIMIT = (
    settings.PAGINATION_PER_PAGE
    if math.isinf(settings.PAGINATION_MAX_LIMIT)
    else settings.PAGINATION_MAX_LIMIT
)
```

The class body stays unchanged.

**Verify**: bake → `uv run pytest tests/unit/api/pagination_test.py` → FAILS
(the old test asserts the min()) — expected, fixed next.

### Step 2: Update the test to assert intent, both branches

Rewrite `tests/unit/api/pagination_test.py` to cover default (inf → per-page)
and overridden (finite → itself) behavior. The constant is computed at import
time, so the override branch reloads the module with a patched ninja settings
object:

```python
import importlib

from ninja.conf import settings
from pytest_mock import MockerFixture

from apps.api import pagination


def test_bounded_pagination_caps_limit_at_max_limit_when_setting_is_finite(
    mocker: MockerFixture,
) -> None:
    mocker.patch.object(settings, "PAGINATION_MAX_LIMIT", 500)

    module = importlib.reload(pagination)

    try:
        assert module.PAGINATION_MAX_LIMIT == 500

    finally:
        mocker.stopall()
        importlib.reload(pagination)


def test_bounded_pagination_caps_limit_at_per_page_when_max_limit_is_unset() -> None:
    input_fields = pagination.BoundedLimitOffsetPagination.Input.model_fields

    limit_field = input_fields["limit"]
    offset_field = input_fields["offset"]

    assert limit_field.default == settings.PAGINATION_PER_PAGE
    assert limit_field.metadata[0].ge == 1
    assert limit_field.metadata[1].le == settings.PAGINATION_PER_PAGE
    assert offset_field.default == 0
    assert offset_field.metadata[0].ge == 0
    assert offset_field.metadata[1].le == settings.PAGINATION_MAX_OFFSET
```

Keep tests alphabetized (AGENTS.md); adjust imports to Ruff's ordering. The
`try/finally` with a final `reload` ensures the module-level constant is
restored for other tests regardless of order (pytest-randomly).

**Verify**: bake → `uv run pytest tests/unit/api/pagination_test.py` → 2 pass.

### Step 3: Full verification loop

**Verify**: fresh bake → `uv run pytest` → all pass, 100%;
`git add -A && uv run pre-commit run --all-files` → all pass.

## Test plan

Covered by Step 2 — the two tests above, in the existing file, following its
structural-assertion pattern.

## Done criteria

- [ ] `grep -n "min(" '{{cookiecutter.project_slug}}/src/apps/api/pagination.py'` → no matches
- [ ] Baked project: `uv run pytest` → all pass, 100%
- [ ] Baked project: `uv run pre-commit run --all-files` → all pass
- [ ] No files outside the in-scope list modified (`git status`)
- [ ] `plans/README.md` status row updated

## STOP conditions

- `importlib.reload` of the pagination module breaks other collected tests
  (module identity issues with ninja class registration) — report rather than
  papering over with test ordering.
- ninja's `settings.PAGINATION_MAX_LIMIT` is not `inf` on the pinned version
  (would contradict the audit's verified value — report).

## Maintenance notes

- If a future django-ninja release changes `PAGINATION_MAX_LIMIT`'s default to
  a finite value, the `isinf` branch silently becomes dead and the ninja
  setting takes over — which is the desired end state; the comment can then be
  simplified.
- Reviewers: check that no endpoint starts depending on `limit > 100` without
  the project explicitly setting `NINJA_PAGINATION_MAX_LIMIT`.
