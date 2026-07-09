# Plan 002: Reject `author_email` values containing quotes or backslashes before they corrupt the generated pyproject.toml

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving to the
> next step. If anything in the "STOP conditions" section occurs, stop and
> report — do not improvise. When done, update the status row for this plan
> in `plans/README.md` — unless a reviewer dispatched you and told you they
> maintain the index.
>
> **Drift check (run first)**:
> `git diff --stat e0ec725..HEAD -- hooks/pre_gen_project.py .github/workflows/ci.yaml tests/hooks_test.py`
> If any in-scope file changed since this plan was written, compare the
> "Current state" excerpts against the live code before proceeding; on a
> mismatch, treat it as a STOP condition.

## Status

- **Priority**: P2
- **Effort**: S
- **Risk**: LOW
- **Depends on**: none
- **Category**: bug
- **Planned at**: commit `e0ec725`, 2026-07-09

## Why this matters

This repository is a cookiecutter template. The pre-generation hook validates
inputs before rendering. `author_name` and `description` are screened for
`"`, `\`, and newlines because they are written into double-quoted TOML
strings in the generated `pyproject.toml` — but `author_email`, written into
the *same kind of TOML string*, is validated only against a loose email regex
that accepts `"` and `\` (e.g. `a"b@example.com` passes). Such a value renders
a malformed `pyproject.toml`; the post-gen hook then swallows the resulting
`uv lock` failure into a warning, so the baker receives a silently broken
project with no lockfile. The CI reject-matrix has quote cases for name and
description but none for email, so nothing catches this.

## Current state

- `hooks/pre_gen_project.py` — cookiecutter pre-gen hook. NOTE: this file
  contains Jinja substitutions (`{{ cookiecutter.x | tojson }}`) and is not
  runnable Python until rendered. Relevant excerpts:

  ```python
  # lines 4, 11-12
  AUTHOR_EMAIL = {{ cookiecutter.author_email | tojson }}
  ...
  EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
  FORBIDDEN_CHARS_PATTERN = re.compile(r'["\\\n\r]')
  ```

  ```python
  # lines 35-48 (inside main())
  if not EMAIL_PATTERN.fullmatch(AUTHOR_EMAIL):
      sys.exit("author_email must be a valid email address.")

  if FORBIDDEN_CHARS_PATTERN.search(AUTHOR_NAME):
      sys.exit(
          "author_name must not contain double quotes, backslashes, or "
          "newlines because it is written into pyproject.toml."
      )

  if FORBIDDEN_CHARS_PATTERN.search(DESCRIPTION):
      sys.exit(
          "description must not contain double quotes, backslashes, or "
          "newlines because it is written into pyproject.toml."
      )
  ```

  (`EMAIL_PATTERN`'s `[^@\s]` classes already reject whitespace/newlines; the
  gap is exactly `"` and `\`.)

- The sink — `{{cookiecutter.project_slug}}/pyproject.toml:8-12` writes the
  raw value into double-quoted TOML strings:

  ```toml
  authors = [
      { name = "{{ cookiecutter.author_name }}", email = "{{ cookiecutter.author_email }}" }
  ]
  ```

- The swallow path — `hooks/post_gen_project.py:167-171`:

  ```python
  if shutil.which("uv"):
      try:
          subprocess.run(["uv", "lock"], check=True)
      except subprocess.CalledProcessError:
          print(UV_LOCK_WARNING)
  ```

  Do NOT change this — a soft-fail `uv lock` is deliberate (uv may be absent
  or offline at bake time). The fix is to reject bad input up front.

- The CI reject matrix — `.github/workflows/ci.yaml:156-172` (root workflow,
  plain YAML, no Jinja). Existing cases, alphabetically ordered by `case`:

  ```yaml
  - case: bad-author-name
    extra-args: author_name='has "quotes"'
  - case: bad-description
    extra-args: description='has "quotes"'
  - case: bad-domain
    extra-args: domain_name=no-dot
  - case: bad-email
    extra-args: author_email=nope
  - case: bad-knob
    extra-args: use_celery=bogus
  ...
  ```

- Root unit tests — `tests/hooks_test.py` currently covers only
  `post_gen_project.py`. It loads the hook by regex-substituting the Jinja
  constant lines (see its `JINJA_CONSTANT` regex and `_load_hook_module`
  helper, `tests/hooks_test.py:13-16` and the `# Utils` section). The
  pre-gen hook's constants have the same `NAME = {{ cookiecutter.x | tojson }}`
  shape, so the same substitution technique applies.

- Repo conventions: alphabetize matrix entries and constants; conventional
  commit messages; blank lines around control-flow blocks; never
  `from __future__ import annotations`.

## Commands you will need

| Purpose | Command | Expected on success |
|---------|---------|---------------------|
| Root unit tests | `uvx pytest tests` | all pass |
| Root pre-commit (all guards) | `uvx pre-commit run --all-files` | exit 0 |
| Rejection e2e (local) | `uvx cookiecutter . -o /tmp/verify-002 --no-input author_email='has"quote@example.com'` | NON-zero exit; message about author_email; no project directory created under /tmp/verify-002 |
| Happy-path bake | `uvx cookiecutter . -o /tmp/verify-002-ok --no-input` | exit 0 |

## Scope

**In scope** (the only files you should modify):

- `hooks/pre_gen_project.py`
- `.github/workflows/ci.yaml` (reject-invalid-input matrix only)
- `tests/hooks_test.py`

**Out of scope** (do NOT touch, even though they look related):

- `hooks/post_gen_project.py` — the `uv lock` soft-fail is deliberate.
- `EMAIL_PATTERN` itself — do not attempt a stricter RFC-style email regex;
  the layered forbidden-chars check matches the established pattern used for
  name/description.
- `{{cookiecutter.project_slug}}/pyproject.toml` — do not add escaping there;
  validation at the boundary is the template's chosen approach.

## Git workflow

- Branch: `advisor/002-hook-email-validation`
- Commit style: conventional commits (e.g.
  `fix: reject author_email containing quotes or backslashes`).
- Do NOT push or open a PR unless the operator instructed it.

## Steps

### Step 1: Add the forbidden-chars branch for `author_email`

In `hooks/pre_gen_project.py`, immediately after the existing
`EMAIL_PATTERN` check (line ~35-36) and before the `AUTHOR_NAME` check, add:

```python
    if FORBIDDEN_CHARS_PATTERN.search(AUTHOR_EMAIL):
        sys.exit(
            "author_email must not contain double quotes or backslashes "
            "because it is written into pyproject.toml."
        )
```

(Message mirrors the neighboring ones; newlines are omitted from the message
because `EMAIL_PATTERN` already rejects all whitespace. Keep the blank line
between `if` blocks, matching the file's style.)

**Verify**:
`uvx cookiecutter . -o /tmp/verify-002 --no-input author_email='has"quote@example.com'`
→ exits non-zero, stderr/stdout contains
`author_email must not contain double quotes or backslashes`, and
`find /tmp/verify-002 -mindepth 1 -maxdepth 1 -type d` prints nothing.
Then `uvx cookiecutter . -o /tmp/verify-002-ok --no-input` → exit 0
(default email `john.doe@example.com` still passes).

### Step 2: Add the reject-matrix case in CI

In `.github/workflows/ci.yaml`, add to the `reject-invalid-input` matrix
(keeping alphabetical order by `case` — the new entry goes between
`bad-domain` and `bad-email`... note: alphabetically `bad-email-quote` sorts
AFTER `bad-email`, so place it between `bad-email` and `bad-knob`):

```yaml
          - case: bad-email-quote
            extra-args: author_email='has"quote@example.com'
```

Match the existing two-space/step indentation exactly; the job's "Verify
invalid input is rejected" step already asserts failure + no output directory
for every matrix case, so no step changes are needed.

**Verify**: `uvx pre-commit run --all-files` at the repo root → exit 0 (this
runs yaml checks and `zizmor` over workflows).

### Step 3: Add a root unit test for the new branch

In `tests/hooks_test.py`, add coverage for the pre-gen hook's email screening.
Follow the file's existing technique for loading a Jinja-bearing hook: reuse
(or generalize) the `JINJA_CONSTANT` regex + module-loading helper so it can
load `hooks/pre_gen_project.py` with a supplied context, then add:

- `test_pre_gen_rejects_author_email_with_double_quote` — context with
  `author_email='has"quote@example.com'` (all other values valid, e.g. the
  defaults from `cookiecutter.json`); assert `pytest.raises(SystemExit)` and
  that the exit message mentions `author_email`.
- `test_pre_gen_accepts_default_author_email` — the default context passes
  `main()` without raising.

Keep test functions alphabetized within the file. If generalizing the loader
requires restructuring more than ~30 lines of existing helper code, STOP and
report instead (the CI matrix case from step 2 already provides end-to-end
coverage; the maintainer may prefer to skip the unit layer).

**Verify**: `uvx pytest tests` → all pass, including the 2 new tests.

## Test plan

- Unit: the two tests in step 3 (`tests/hooks_test.py`), modeled on that
  file's existing `_load_hook_module` pattern.
- E2E: the `bad-email-quote` matrix case in `.github/workflows/ci.yaml`
  (step 2), which asserts both non-zero exit and no generated directory.
- Regression safety: happy-path default bake still succeeds (step 1 verify).

## Done criteria

Machine-checkable. ALL must hold:

- [ ] `uvx cookiecutter . -o /tmp/verify-002 --no-input author_email='has"quote@example.com'` exits non-zero with the new message and creates no project directory
- [ ] `uvx cookiecutter . -o /tmp/verify-002-ok --no-input` exits 0
- [ ] `grep -n "bad-email-quote" .github/workflows/ci.yaml` → one match
- [ ] `uvx pytest tests` → all pass (2 new tests included, unless step 3's escape hatch was taken and reported)
- [ ] `uvx pre-commit run --all-files` → exit 0
- [ ] `git status` shows no modified files outside the in-scope list
- [ ] `plans/README.md` status row updated

## STOP conditions

Stop and report back (do not improvise) if:

- The `pre_gen_project.py` excerpts don't match (validation was restructured
  since `e0ec725`).
- Step 1's rejection command *succeeds* in creating a project — that means
  cookiecutter's argument quoting differs from this plan's assumption; report
  the exact command behavior observed.
- Step 3's loader generalization exceeds the ~30-line budget described there.
- Any verification fails twice after a reasonable fix attempt.

## Maintenance notes

- Any future cookiecutter variable written into a quoted TOML/YAML string in
  the generated tree needs the same layered screening — grep
  `{{cookiecutter.project_slug}}/pyproject.toml` for new `{{ cookiecutter.* }}`
  interpolations when adding variables.
- Reviewer should scrutinize: alphabetical placement of the matrix entry and
  that the unit test loads the *rendered-equivalent* hook (constants
  substituted), not the raw Jinja file.
- Deferred: screening `github_username`/`domain_name` for TOML-hostile chars —
  their existing strict patterns already exclude `"` and `\`.
