# Plan 001: Make every CI bake case green again (format/render regressions)

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving to the
> next step. If anything in the "STOP conditions" section occurs, stop and
> report — do not improvise. When done, update the status row for this plan
> in `plans/README.md` — unless a reviewer dispatched you and told you they
> maintain the index.
>
> **Drift check (run first)**:
> `git diff --stat 75c4dce..HEAD -- '{{cookiecutter.project_slug}}/tests/api/integration/throttling_test.py'`
> If this file changed since this plan was reconciled, compare the "Current
> state" excerpt below against the live code before proceeding; on a
> mismatch, treat it as a STOP condition.

## Status

- **Priority**: P1
- **Effort**: S (reduced from M — three of the original four defects are
  already fixed; see Reconciliation below)
- **Risk**: LOW
- **Depends on**: none
- **Category**: dx / bug
- **Planned at**: commit `eee3978`, 2026-07-08
- **Reconciled at**: commit `75c4dce`, 2026-07-08 (advisor `execute` pass —
  re-verified all four defects empirically before dispatching an executor)

## Reconciliation (2026-07-08, advisor)

This plan was written against commit `eee3978`. Commit `75c4dce`
("fix: repair generated project CI checks") landed on `main` afterward and,
per its message, fixed three of the four defects this plan targeted. The
advisor re-verified all four empirically on current `HEAD` (`75c4dce`) before
dispatching an executor, rather than trust the commit message alone:

- **Defect A (admin_test.py blank lines)** — **FIXED**. The file now uses
  `{%- if %}` / `{%- endif %}` trim markers with explicit blank lines inside
  the block. Verified: baked `default` (no flags) and `use_example_api=yes
  api_auth=token` — both `ruff format --check` and `ruff check` exit 0 on
  both.
- **Defect B (throttling_test.py under-88-char assert)** — **STILL BROKEN**.
  Unchanged since this plan was written (confirmed via
  `git diff --stat eee3978..HEAD` on this file: empty). Verified by baking
  `use_example_api=yes api_auth=token api_throttling=basic`:
  `ruff format --check` reports
  `Would reformat: tests/api/integration/throttling_test.py`. This is the
  only remaining work in this plan.
- **Defect C (smtp EMAIL_HOST)** — **FIXED**. `prod_settings_test.py` now has
  a Jinja-guarded `"EMAIL_HOST": "smtp.example.test",` entry (and, as a bonus
  not in the original plan, `RESEND_API_KEY` is now also guarded to
  `email_provider == "resend"`). Verified: baked `email_provider=smtp`,
  ran ruff (clean) and the full suite under Docker
  (`uv run pytest`) — **46 passed, 2 subtests passed, 100% coverage**.
- **Defect D (conftest.py I001 in minimal render)** — **FIXED**. Verified:
  baked `use_example_api=no use_celery=none`, `ruff check` and
  `ruff format --check` on `tests/conftest.py` both pass.
- **Step 5 sweep** — also re-run by the advisor across all seven combos
  listed in the original plan's Step 5 (`use_cors=yes`, `use_csp=yes`, both
  together, `api_throttling=basic`, `use_celery=worker`,
  `postgres=external redis=external use_traefik=no`, and the
  celery/email/sentry/s3/traefik all-off combo). All seven pass
  `ruff format --check` and `ruff check`. None of these combos render
  `throttling_test.py` with `use_example_api=yes api_auth=token` at once, so
  none exercise defect B — that combo is covered by defect B's own Step 2
  verify below.

**Net result: only defect B needs an edit.** Everything else in this plan is
already done — no further action, no re-verification required from the
executor (the advisor will re-confirm during review anyway, per the
`execute` workflow).

## Current state

This repo is a **cookiecutter template**. Files under
`{{cookiecutter.project_slug}}/` contain Jinja and cannot be run directly —
verification means baking a project into a temp dir and running checks there.
Always single-quote paths containing `{{cookiecutter.project_slug}}` in shell
commands. Do not hand-trace Jinja whitespace control; always verify renders
empirically (a prior session's recorded lesson).

**Defect B: `throttling_test.py` has a hand-wrapped assert under 88 chars →
`ruff format` joins it.**
`{{cookiecutter.project_slug}}/tests/api/integration/throttling_test.py:33-36`
(inside `test_authenticated_users_get_separate_counters`):

```python
    assert (
        client_1.get("/api/v1/notes", headers=headers_1).status_code
        == HTTPStatus.OK
    )
```

Rendered, the single-line form is 87 chars (< 88), so ruff formats it onto one
line. The asserts directly above that compare against
`HTTPStatus.TOO_MANY_REQUESTS` exceed 88 chars and are correctly wrapped —
leave those alone. This file renders only when `api_throttling=basic AND
use_example_api=yes` (CI case `example-token-auth-throttling`).

Repo conventions that apply (from root `AGENTS.md`): alphabetize where order
doesn't matter; blank lines around control-flow blocks; never add
`from __future__ import annotations`; conventional-commit messages (example
from `git log`: `test: alphabetize ready_test.py and fix stale error-order
assertion`).

## Commands you will need

| Purpose | Command | Expected on success |
|---------|---------|---------------------|
| Bake a combo | `uvx cookiecutter . -o /tmp/verify-001/<case> --no-input <knob=value ...>` | exit 0, project at `/tmp/verify-001/<case>/my-project` |
| Format check (in bake) | `uvx ruff@0.15.16 format --check .` | `N files already formatted`, exit 0 |
| Lint (in bake) | `uvx ruff@0.15.16 check .` | `All checks passed!` |
| Root checks | `uvx pre-commit run --all-files` | all hooks pass |

The ruff version **must** match the pin in
`{{cookiecutter.project_slug}}/.pre-commit-config.yaml` (currently
`v0.15.16` — the advisor confirmed this pin during reconciliation).

## Scope

**In scope** (the only file you should modify):
- `{{cookiecutter.project_slug}}/tests/api/integration/throttling_test.py`

**Out of scope** (do NOT touch, even though they look related):
- `{{cookiecutter.project_slug}}/tests/core/integration/admin_test.py` —
  defect A, already fixed by `75c4dce`. Do not re-edit.
- `{{cookiecutter.project_slug}}/tests/config/unit/prod_settings_test.py` —
  defect C, already fixed by `75c4dce`. Do not re-edit.
- `{{cookiecutter.project_slug}}/tests/conftest.py` — defect D, already fixed
  by `75c4dce`. Do not re-edit.
- `{{cookiecutter.project_slug}}/tests/api/unit/throttling_test.py` — the
  *unit* throttling tests; unrelated, already passing.
- `src/` anywhere.
- `.github/workflows/ci.yaml` (root).
- `hooks/post_gen_project.py`.

## Git workflow

- Branch: `advisor/001-fix-bake-matrix-regressions`
- One commit; conventional-commit style, e.g. `fix: collapse throttling_test
  assert that ruff reformats onto one line`.
- Do NOT push or open a PR unless the operator instructed it.

## Steps

### Step 1: Collapse the under-88-char assert (defect B)

In `throttling_test.py`, replace lines 33-36 with the single-line form:

```python
    assert client_1.get("/api/v1/notes", headers=headers_1).status_code == HTTPStatus.OK
```

Then check the rest of the file for sibling hand-wrapped expressions that
ruff would also rewrite — the authoritative check is the bake in the Verify
below, which formats the whole file.

**Verify**:
```
uvx cookiecutter . -o /tmp/verify-001/throttle --no-input use_example_api=yes api_auth=token api_throttling=basic
uvx ruff@0.15.16 format --check /tmp/verify-001/throttle/my-project
uvx ruff@0.15.16 check /tmp/verify-001/throttle/my-project
```
→ both exit 0 (`ruff format --check` prints `N files already formatted`,
`ruff check` prints `All checks passed!`).

### Step 2: Confirm no regression in the already-fixed defects

These should already pass with no edits from you (advisor-verified above).
Run once to confirm your Step 1 edit didn't disturb anything else:

```
uvx cookiecutter . -o /tmp/verify-001/default --no-input
uvx ruff@0.15.16 format --check /tmp/verify-001/default/my-project
uvx ruff@0.15.16 check /tmp/verify-001/default/my-project
```
→ both exit 0. If this fails, STOP — it means something other than your
Step 1 edit changed; you touched only `throttling_test.py`, so a failure
here indicates worktree contamination or a misread scope. Report it.

## Test plan

No new tests — this plan repairs formatting of an existing test file. The
regression guard *is* the CI bake matrix (`.github/workflows/ci.yaml`), whose
per-bake `uv run pre-commit run --all-files` step covers this defect once
green.

## Done criteria

Machine-checkable. ALL must hold:

- [ ] Step 1's ruff commands both exit 0 on the `throttle` bake
- [ ] Step 2's ruff commands both exit 0 on the `default` bake (no
      regression)
- [ ] `git status --short` (in the worktree) shows changes ONLY to
      `{{cookiecutter.project_slug}}/tests/api/integration/throttling_test.py`
- [ ] `plans/README.md` status row updated to DONE for plan 001 — unless the
      reviewer said they maintain the index

## STOP conditions

Stop and report back (do not improvise) if:

- `throttling_test.py` no longer matches the "Current state" excerpt above
  (this repo has multiple concurrent sessions; drift is likely, not
  hypothetical).
- After 3 empirical iterations, the `throttle` bake still fails
  `ruff format --check` — report the full `ruff format --check` diff output.
- Step 2 (regression check) fails — that means scope was violated or the
  worktree is contaminated; report rather than fixing it.

## Maintenance notes

- Root pre-commit cannot format template source (Jinja isn't parseable
  Python), so this defect class — hand-formatting drift in
  `{{cookiecutter.project_slug}}/**/*.py` — will recur. Plan 005 adds a fast
  local bake-and-format gate; it hard-depends on this plan landing first.
- Any future Jinja block inserted between two module-level statements must be
  whitespace-verified in BOTH branches of any surrounding conditional — that
  is exactly how defect A shipped originally (fixed in `75c4dce`, described
  above for historical context).
