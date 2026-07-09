# Plan 008: Document throttling.py's coupling to ninja-extra cache internals

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving to the
> next step. If anything in the "STOP conditions" section occurs, stop and
> report — do not improvise. When done, update the status row for this plan
> in `plans/README.md` — unless a reviewer dispatched you and told you they
> maintain the index.
>
> **Drift check (run first)**:
> `git diff --stat eee3978..HEAD -- '{{cookiecutter.project_slug}}/src/apps/api/throttling.py'`
> If the file changed since this plan was written, compare the "Current
> state" excerpt against the live code before proceeding; on a mismatch,
> treat it as a STOP condition.

## Status

- **Priority**: P3
- **Effort**: S
- **Risk**: LOW (comment-only change)
- **Depends on**: none
- **Category**: tech-debt / docs
- **Planned at**: commit `eee3978`, 2026-07-08

## Why this matters

`_anon_budget_exhausted()` in `src/apps/api/throttling.py` re-implements the
private cache representation of ninja-extra's `SimpleRateThrottle` family: it
reads `throttle.cache.get(key)` expecting a list of timestamps and re-derives
the sliding-window arithmetic (`timestamp > now - duration`,
`len(history) >= num_requests`). That is a dependency's *internal storage
format*, not its API. If a django-ninja-extra release changes the format, the
function degrades silently — it returns `False` (budget never exhausted) and
the anon-bypass protection evaporates. The failure IS tripwired: the
integration tests drive this function against ninja-extra's real cache
writes, so a format change turns the bake matrix red on the version bump. But
nothing in the code tells the person triaging that red CI *why* the test
broke or where the coupling lives. This plan writes that knowledge into the
code so the future triage takes minutes, not an afternoon.

## Current state

This repo is a **cookiecutter template**; the file renders only when
`api_throttling=basic` (deleted otherwise by `hooks/post_gen_project.py`).
The file is Jinja-free plain Python, but verification still means baking.
Always single-quote `{{cookiecutter.project_slug}}` paths in shell commands.

`{{cookiecutter.project_slug}}/src/apps/api/throttling.py:69-86`:

```python
def _anon_budget_exhausted(
    throttle: AnonRateThrottle,
    request: HttpRequest,
) -> bool:
    key = throttle.get_cache_key(request)

    if key is None:
        return False

    duration = cast("int", throttle.duration)
    now = throttle.timer()
    num_requests = cast("int", throttle.num_requests)
    history = [
        timestamp
        for timestamp in throttle.cache.get(key, [])
        if timestamp > now - duration
    ]
    return len(history) >= num_requests
```

The tripwire tests (do NOT modify them; they are referenced by the comment):
- `{{cookiecutter.project_slug}}/tests/api/integration/throttling_test.py` —
  `test_anonymous_requests_with_bogus_authorization_header_return_429_after_configured_limit`
  and `test_bogus_authorization_requests_share_the_anonymous_ip_budget` both
  exhaust the real ninja-extra-written cache and require a final 429, which
  only happens if this function reads that cache correctly.
- The pinned dependency is `django-ninja-extra==0.31.5` in
  `{{cookiecutter.project_slug}}/pyproject.toml`.

Repo comment conventions (visible throughout `src/`): comments state
constraints and consequences, not mechanics; sentence case; wrapped near 79
columns. Exemplar in the same file: the module docstring.

## Commands you will need

| Purpose | Command | Expected on success |
|---------|---------|---------------------|
| Bake the combo | `uvx cookiecutter . -o /tmp/verify-008 --no-input use_example_api=yes api_auth=jwt api_throttling=basic` | project generated |
| Lint/format (in bake) | `uvx ruff@0.15.16 format --check . && uvx ruff@0.15.16 check .` | exit 0 (see STOP note re plan 001) |

## Scope

**In scope** (the only file you should modify):
- `{{cookiecutter.project_slug}}/src/apps/api/throttling.py` (comment only —
  zero behavior change)

**Out of scope**:
- Any test file — the tripwire tests already exist; do not add tests for a
  comment.
- Replacing the reimplementation with a ninja-extra API call — no public
  "peek without consuming" API exists in 0.31.x (that absence is *why* the
  function exists; an upstream feature request is a maintainer decision, see
  Maintenance notes).
- The rest of `throttling.py`'s logic.

## Git workflow

- Branch: `advisor/008-document-throttle-cache-coupling`
- Single commit, e.g. `docs: record the throttle cache-format coupling`.
- Do NOT push or open a PR unless the operator instructed it.

## Steps

### Step 1: Add the constraint comment

Immediately above the `history = [...]` block (after the `num_requests`
line) in `_anon_budget_exhausted`, add:

```python
    # Pre-checks the budget WITHOUT consuming it, which ninja-extra has no
    # public API for — so this mirrors SimpleRateThrottle's private cache
    # format (a list of request timestamps, window-filtered) as of
    # django-ninja-extra 0.31.x. If a bump changes that format, this returns
    # False forever and the integration throttling tests fail on their final
    # 429 assertion — that failure means "re-sync this function with the new
    # cache format," not "the tests are flaky."
```

Adjust placement/wrapping to whatever `ruff format` accepts; keep the three
facts intact: (1) why the reimplementation exists (no non-consuming public
API), (2) what it mirrors and at which version, (3) what a future failure
looks like and what it means.

**Verify**:
```
uvx cookiecutter . -o /tmp/verify-008 --no-input use_example_api=yes api_auth=jwt api_throttling=basic
cd /tmp/verify-008/my-project && uvx ruff@0.15.16 format --check . && uvx ruff@0.15.16 check .
```
→ exit 0. (If `ruff format` fails on `tests/api/integration/throttling_test.py`
or `tests/core/integration/admin_test.py`, that is plan 001's known defect,
not yours — confirm YOUR file passes with
`uvx ruff@0.15.16 format --check src/apps/api/throttling.py` and note the
rest in your report.)

### Step 2: Confirm zero behavior change

**Verify**: `git diff -- '{{cookiecutter.project_slug}}/src/apps/api/throttling.py'`
→ the diff contains ONLY comment lines (every changed line starts with `#`
after indentation, or is blank).

## Test plan

None — comment-only. The existing integration tests remain the behavioral
tripwire; this plan's entire value is making their future failure
self-explaining.

## Done criteria

- [ ] Comment present in `_anon_budget_exhausted` carrying the three facts
- [ ] `git diff` on the file shows comment-only changes
- [ ] Baked `uvx ruff@0.15.16 format --check src/apps/api/throttling.py` → exit 0
- [ ] `git status --short` shows changes ONLY to the in-scope file
- [ ] `plans/README.md` status row updated

## STOP conditions

- `_anon_budget_exhausted` no longer matches the excerpt (drifted — e.g. an
  upstream API appeared and someone already replaced the reimplementation).
- You feel the urge to "improve" the logic while you're in there — don't;
  comment only.

## Maintenance notes

- Optional follow-up for the maintainer (deliberately not in this plan, as
  it's an outward-facing action): file a feature request on
  vitalik/django-ninja-extra for a public non-consuming budget-check (e.g.
  `SimpleRateThrottle.would_allow(request)`); if it ships, replace this
  function's body with the API call and delete the comment.
- When Dependabot bumps `django-ninja-extra`, a red
  `example-jwt-auth-throttling` bake case failing on a 429 assertion is
  this coupling — the comment now says so at the site.
