# Plan 011: Harden the cookiecutter hooks and CI-test the template's input contract

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving to the
> next step. If anything in the "STOP conditions" section occurs, stop and
> report — do not improvise. When done, update the status row for this plan
> in `plans/README.md` — unless a reviewer dispatched you and told you they
> maintain the index.
>
> **Drift check (run first)**: `git diff --stat 924bfba..HEAD -- hooks/ .github/workflows/ci.yaml cookiecutter.json README.md`
> On any change, compare "Current state" excerpts against the live code; on a
> mismatch, treat it as a STOP condition.

## Status

- **Priority**: P2
- **Effort**: M
- **Risk**: LOW (template-layer only; no baked-runtime behavior changes)
- **Depends on**: none (012 will lint what this plan writes — run this first)
- **Category**: bug (template mechanics)
- **Planned at**: commit `924bfba`, 2026-07-04

## Why this matters

The hooks are the template's input contract, and it currently has verified
holes:

1. `post_gen_project.py` runs `git init` **unguarded** while the adjacent
   `uv lock` is fully guarded — a missing `git` (or git < 2.28, which lacks
   `--initial-branch`) raises an uncaught exception, the hook exits non-zero,
   and cookiecutter **deletes the freshly generated project**, leaving the
   user a Python traceback.
2. `pre_gen_project.py` validates only the slug pattern and `"@" in email`.
   `author_name`, `description`, and `github_username` flow into quoted TOML
   (`pyproject.toml` authors/description) and YAML (`dependabot.yml`
   assignees) — a `"`, `\`, or newline produces a project whose
   `pyproject.toml` doesn't parse, which crashes the API at startup
   (`config/pyproject.py` reads it) and every test. The failure surfaces
   post-bake as a confusing parse error instead of a prompt-time message.
3. No slug length bound: `project_slug.replace('-','_')` becomes the Postgres
   database/user name; identifiers over 63 bytes get silently truncated by
   Postgres while `DATABASE_URL` requests the full name — connection failure.
4. The slug derivation (`lower().replace(' ','-').replace('_','-')`) can
   produce slugs its own validator rejects (`"My  Project"` → `my--project`;
   trailing space → `my-project-`), and the error message blames
   `project_slug`, a field the user may never have typed.
5. None of the rejection/fallback branches are exercised anywhere: the CI
   matrix bakes two valid slugs only.

## Important context

This plan edits the TEMPLATE layer (`hooks/`, `.github/workflows/ci.yaml` at
the repo root) — not the `{{cookiecutter.project_slug}}/` tree. Hook files are
rendered by Jinja before execution, so `"{{ cookiecutter.author_name }}"`
strings inside them are how values arrive — preserve that mechanism.

## Current state

- `hooks/pre_gen_project.py` (whole file, 23 lines):

  ```python
  import re
  import sys

  PROJECT_SLUG = "{{ cookiecutter.project_slug }}"
  AUTHOR_EMAIL = "{{ cookiecutter.author_email }}"

  SLUG_PATTERN = re.compile(r"^[a-z][a-z0-9]*(-[a-z0-9]+)*$")


  def main() -> None:
      if not SLUG_PATTERN.fullmatch(PROJECT_SLUG):
          sys.exit(
              "project_slug must start with a lowercase letter and contain only "
              "lowercase letters, digits, and single hyphen separators."
          )

      if "@" not in AUTHOR_EMAIL:
          sys.exit("author_email must contain @.")


  if __name__ == "__main__":
      main()
  ```

- `hooks/post_gen_project.py`: `subprocess.run(["git", "init",
  "--initial-branch=main"], check=True)` unguarded at lines 11-14; the uv
  block at 16-22 models the guard pattern (`shutil.which` + try/except +
  warning print).
- `cookiecutter.json:3` — slug derivation:
  `"{{ cookiecutter.project_name.lower().replace(' ', '-').replace('_', '-') }}"`.
- `.github/workflows/ci.yaml` — `bake` matrix with two valid entries
  (`My API Server 2` → `my-api-server-2`, `My Project` → `my-project`), steps:
  checkout, setup-python, setup-uv, `uvx cookiecutter . --no-input -o
  /tmp/bake ${{ matrix.extra-args }}`, lockfile assert, uv sync, pytest,
  pre-commit.
- Template README's variable table documents the slug rule
  (`README.md:36-37`).

## Commands you will need

Run from the template repo root.

| Purpose | Command | Expected on success |
|---------|---------|---------------------|
| Valid bake | `uvx cookiecutter . --no-input -o /tmp/bake-011` | exit 0 |
| Invalid bake (example) | `uvx cookiecutter . --no-input -o /tmp/bake-011-bad project_name='Bad "Quote"'` | exit ≠ 0, error names the offending variable, no project dir left behind |
| Baked suite | `cd /tmp/bake-011/my-project && uv run pytest` | all pass |
| Hook lint (after Plan 012) | `pre-commit run --all-files` at root | passes |

## Scope

**In scope**:
- `hooks/pre_gen_project.py`
- `hooks/post_gen_project.py`
- `.github/workflows/ci.yaml` (template root)
- `README.md` (template root — variable table notes)

**Out of scope**:
- `cookiecutter.json` derivation expression — collapsing repeated hyphens
  needs regex filters cookiecutter's Jinja doesn't ship; the fix is a clearer
  pre_gen message (Step 2), not a cleverer derivation.
- Anything under `{{cookiecutter.project_slug}}/`.
- Root pre-commit config (Plan 012).

## Git workflow

- Branch: `advisor/011-cookiecutter-hooks-hardening`
- Conventional commit, e.g. `fix: harden cookiecutter hooks and test the input contract`
- Do NOT push or open a PR unless the operator instructed it.

## Steps

### Step 1: Guard git init like uv

In `post_gen_project.py`, mirror the uv pattern:

```python
GIT_INIT_WARNING = (
    "WARNING: git repository was not initialized; run git init "
    "--initial-branch=main manually"
)


def main() -> None:
    if shutil.which("git"):
        try:
            subprocess.run(
                ["git", "init", "--initial-branch=main"],
                check=True,
            )

        except (OSError, subprocess.CalledProcessError):
            print(GIT_INIT_WARNING)

    else:
        print(GIT_INIT_WARNING)
    ...
```

(Constants block at top alphabetized with `UV_LOCK_WARNING`; keep the rest of
`main()` unchanged. Blank lines around branches per house style.)

**Verify**: `env PATH=/usr/bin:/bin uvx cookiecutter . --no-input -o
/tmp/bake-011-nogit` — if you cannot construct a PATH without git on this
machine, instead temporarily test by editing a scratch copy of the hook to
call `subprocess.run(["git-missing-binary", ...])` and confirming the warning
prints and the bake SURVIVES (project dir exists). Do not commit the scratch
edit. Then a normal bake → git repo initialized as before.

### Step 2: Validate all rendered variables in pre_gen

Extend `pre_gen_project.py` (keep the existing constants/pattern style;
constants alphabetized):

```python
AUTHOR_EMAIL = "{{ cookiecutter.author_email }}"
AUTHOR_NAME = "{{ cookiecutter.author_name }}"
DESCRIPTION = "{{ cookiecutter.description }}"
GITHUB_USERNAME = "{{ cookiecutter.github_username }}"
PROJECT_SLUG = "{{ cookiecutter.project_slug }}"

EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
FORBIDDEN_CHARS_PATTERN = re.compile(r'["\\\n\r]')
GITHUB_USERNAME_PATTERN = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})$")
MAX_SLUG_LENGTH = 50
SLUG_PATTERN = re.compile(r"^[a-z][a-z0-9]*(-[a-z0-9]+)*$")
```

Checks in `main()` (each `sys.exit` message must name the variable and, for
the slug, mention it may be derived):

1. Slug pattern (existing) — reword the message: "project_slug (derived from
   project_name unless set explicitly) must start with a lowercase letter and
   contain only lowercase letters, digits, and single hyphen separators."
2. `len(PROJECT_SLUG) > MAX_SLUG_LENGTH` → exit: slug too long (Postgres
   identifiers derived from it are capped at 63 bytes).
3. `EMAIL_PATTERN.fullmatch(AUTHOR_EMAIL)` replaces the `"@" in` check.
4. `FORBIDDEN_CHARS_PATTERN.search(...)` on AUTHOR_NAME and DESCRIPTION →
   exit naming the field ("must not contain double quotes, backslashes, or
   newlines — it is written into pyproject.toml").
5. `GITHUB_USERNAME_PATTERN.fullmatch(GITHUB_USERNAME)` → exit (written into
   dependabot.yml).

Note on Jinja-in-Python: a literal `"` in a value would also break the hook's
own string literal — but cookiecutter renders the hook BEFORE running it, so
the SyntaxError still aborts the bake pre-generation; the regexes handle the
merely-awkward cases and the messages handle the rest. Acceptable.

**Verify** (each command exits non-zero with the right message, and leaves no
output dir):

```
uvx cookiecutter . --no-input -o /tmp/bad project_name='My  Project'
uvx cookiecutter . --no-input -o /tmp/bad project_name='x-very-long...' (>50 chars)
uvx cookiecutter . --no-input -o /tmp/bad author_email='nope'
uvx cookiecutter . --no-input -o /tmp/bad description='has "quotes"'
uvx cookiecutter . --no-input -o /tmp/bad github_username='has space'
```

And the two valid matrix inputs still bake: `--no-input` default and
`project_name="My API Server 2"`.

### Step 3: Negative-bake and underscore-positive CI jobs

In `.github/workflows/ci.yaml`, add a `bake-invalid` job (parallel to `bake`)
with its own small matrix — each entry runs cookiecutter with a bad input and
asserts failure:

```yaml
  bake-invalid:
    name: Reject ${{ matrix.case }}
    runs-on: ubuntu-latest
    strategy:
      fail-fast: false
      matrix:
        include:
          - case: bad-description
            extra-args: description='has "quotes"'
          - case: bad-email
            extra-args: author_email=nope
          - case: bad-slug
            extra-args: project_name='My  Project'
    steps:
      - name: Checkout repository
        uses: actions/checkout@v6.0.3
      - name: Set up Python
        uses: actions/setup-python@v6.2.0
        with:
          python-version: "3.14"
      - name: Set up uv
        uses: astral-sh/setup-uv@v8.2.0
      - name: Bake must fail
        run: |
          if uvx cookiecutter . --no-input -o /tmp/bake ${{ matrix.extra-args }}; then
            echo "expected bake to fail" && exit 1
          fi
          test ! -d /tmp/bake/my-project
```

Also add one positive matrix entry to the existing `bake` job exercising the
underscore-replacement path:
`- project_name: My_Underscore App` / `extra-args: project_name="My_Underscore App"` /
`slug: my-underscore-app`.

Mind the existing style: extended YAML block style, alphabetized where order
doesn't matter, quoting that survives both YAML and shell (`actionlint` in
the baked project won't check this file, but Plan 012's root hooks will —
keep it clean).

**Verify**: `uvx cookiecutter . --no-input -o /tmp/b011 project_name="My_Underscore App"`
→ bakes `my-underscore-app`; `cd /tmp/b011/my-underscore-app && uv run pytest`
→ all pass. For the workflow itself: if `act` is unavailable, validation is
Plan 012's actionlint (or push-time CI) — state in the PR that the job ran
green in CI or was validated by actionlint only.

### Step 4: README variable table

Update the slug rule row/note in the template README to include the new
constraints (≤ 50 chars) and mention that author/description fields must not
contain `"`/`\`/newlines.

**Verify**: visual; markdownlint if Plan 012's root hooks are installed.

## Test plan

The Step 2 negative-bake commands ARE the tests locally; the Step 3 CI job
pins them permanently. The two existing matrix bakes plus the new underscore
entry cover the positive space.

## Done criteria

- [ ] All five Step 2 negative commands fail with messages naming the field; no `/tmp/bad` project dir remains
- [ ] Default bake and `My API Server 2` bake still succeed end-to-end (pytest passes in the bake)
- [ ] `My_Underscore App` bakes to `my-underscore-app` and its suite passes
- [ ] `post_gen_project.py` has git guarded symmetrically with uv
- [ ] `ci.yaml` contains the `bake-invalid` job and the new positive matrix entry
- [ ] No files outside the in-scope list modified (`git status`)
- [ ] `plans/README.md` status row updated

## STOP conditions

- cookiecutter's behavior on hook `sys.exit` differs from expected (project
  dir left behind on failure) — report the cookiecutter version; the cleanup
  guarantee is version-dependent.
- The GitHub-username regex rejects the maintainer's own default
  (`stefanofusai`) — sanity-check before committing; if it does, the regex is
  wrong, fix it.
- Any existing valid input class (the two current matrix entries) starts
  failing pre_gen.

## Maintenance notes

- New cookiecutter variables MUST get a pre_gen check and, if they can break
  a rendered file's syntax, a negative matrix entry. The `bake-invalid` job is
  where template-contract regressions get caught.
- If the maintainer later wants smarter slug derivation (collapse hyphens,
  transliterate), that's a cookiecutter Jinja-extension decision — the
  validation here stays as the backstop regardless.
