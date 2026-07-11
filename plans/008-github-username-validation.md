# Plan 008: Reject invalid GitHub usernames during generation

> **Executor instructions**: Follow the steps and update the index. Stop if
> GitHub's documented username rules differ from the assumptions below.
>
> **Drift check (run first)**: `rtk git diff --stat b367191..HEAD -- 'hooks/pre_gen_project.py' 'tests/hooks_test.py' '.github/workflows/ci.yaml' 'README.md'`

## Status

- **Priority**: P1
- **Effort**: S
- **Risk**: LOW
- **Depends on**: none
- **Category**: bug
- **Planned at**: commit `b367191`, 2026-07-10

## Why this matters

The hook accepts a trailing hyphen and consecutive hyphens even though GitHub
usernames cannot start/end with a hyphen or contain two consecutive hyphens.
Invalid owners then surface later in Dependabot assignment and GHCR image
paths instead of failing at bake time.

## Current state

- `pre_gen_project.py:14` uses
  `^[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})$`.
- The CI invalid-input matrix tests only a leading-hyphen example.
- Root unit tests exercise email validation but not all username boundaries.
- `api_auth=jwt` with `use_example_api=no` is explicitly documented as a
  no-op; do not change that settled behavior in this plan.

## Commands you will need

| Purpose | Command | Expected |
|---|---|---|
| Root tests | `rtk uvx pytest tests -q` | pass |
| Valid bake | `rtk uvx cookiecutter . -o /tmp/plan-008-valid --no-input github_username=a-b9` | succeeds |
| Invalid bake | `rtk uvx cookiecutter . -o /tmp/plan-008-invalid --no-input github_username=a--b` | nonzero, no project |

## Scope

**In scope**:
- `hooks/pre_gen_project.py`
- `tests/hooks_test.py`
- `.github/workflows/ci.yaml`
- `README.md` only if validation prose needs clarification

**Out of scope**:
- Checking whether a syntactically valid account exists.
- Changing GitHub owner casing.
- Changing `api_auth` semantics.

## Git workflow

Do not commit or push unless explicitly requested.

## Steps

### Step 1: Add boundary tests

Add unit cases for one character, 39 characters, 40 characters, leading
hyphen, trailing hyphen, consecutive hyphens, single internal hyphen, and
mixed alphanumeric casing. Extend the invalid-input CI matrix with trailing
and consecutive cases.

**Verify**: the two new invalid cases fail on current code.

### Step 2: Tighten the regex

Use a full-match pattern equivalent to:

```python
r"^(?=.{1,39}$)[A-Za-z0-9]+(?:-[A-Za-z0-9]+)*$"
```

Keep the existing actionable error message or improve it to name the no-edge
and no-consecutive-hyphen requirements.

**Verify**: root tests pass and invalid Cookiecutter runs leave no output
project directory.

### Step 3: Run root verification

Run root pytest and pre-commit.

**Verify**: both exit 0 and the worktree contains only in-scope changes.

## Test plan

Test all length and separator boundaries through the rendered hook, not only
the regex object in isolation.

## Done criteria

- [ ] Invalid edge/consecutive hyphens fail before generation.
- [ ] Valid 1- and 39-character usernames pass.
- [ ] Unit and CI invalid-input coverage exist.
- [ ] Root checks pass.

## STOP conditions

- Current GitHub documentation permits a case this plan rejects.
- Cookiecutter normalizes the supplied username before the hook sees it.

## Maintenance notes

This validates syntax only. Organization/user existence and repository access
remain deployment concerns.
