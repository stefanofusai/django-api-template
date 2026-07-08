# Plan 011: Make the root guard scripts fail closed and tested; complete the reject-invalid-input matrix

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving to the
> next step. If anything in the "STOP conditions" section occurs, stop and
> report — do not improvise. When done, update the status row for this plan
> in `plans/README.md` — unless a reviewer dispatched you and told you they
> maintain the index.
>
> **Drift check (run first)**:
> `git diff --stat 75c4dce..HEAD -- scripts/ .pre-commit-config.yaml .github/workflows/ci.yaml hooks/pre_gen_project.py`
> If any in-scope file changed since this plan was written, compare the
> "Current state" excerpts against the live code before proceeding; on a
> mismatch, treat it as a STOP condition.

## Status

- **Priority**: P2
- **Effort**: M
- **Risk**: LOW
- **Depends on**: none
- **Category**: tests / dx
- **Planned at**: commit `75c4dce`, 2026-07-08

## Why this matters

Two root-level guard scripts run as `always_run` pre-commit hooks protecting
real invariants, but neither has a test — and one **fails open**:
`scripts/check_dockerfile_prod_env.py` derives its requirements from
substring matches against `prod.py`; if a refactor renames those accesses,
`required_env` comes out empty and the script returns 0 while checking
nothing. Separately, the CI `reject-invalid-input` matrix covers only 5 of
the 7 validators in `hooks/pre_gen_project.py` — slug-length,
`github_username`, and `author_name` rejections run in zero CI jobs. This
plan makes the guard fail closed, gives both scripts regression tests wired
into root pre-commit (and therefore root CI), and completes the reject
matrix.

## Current state

This repo is a **cookiecutter template**; this plan touches only ROOT-level
files (no Jinja, plain Python/YAML) — no baking is needed except for the
matrix rows, which run in CI. The repo root has NO test suite today (all
tests live inside `{{cookiecutter.project_slug}}/tests/`, which belongs to
generated projects), and no root `pyproject.toml` — so root tests must use
stdlib `unittest`, not pytest.

Relevant files:

- `scripts/check_dockerfile_prod_env.py` — the fail-open guard:

```python
# scripts/check_dockerfile_prod_env.py:10-40 (abridged)
def main() -> int:
    dockerfile = DOCKERFILE_PATH.read_text()
    prod_settings = PROD_SETTINGS_PATH.read_text()

    required_env = []

    if 'env("POSTGRES_PASSWORD")' in prod_settings:
        required_env.append("POSTGRES_PASSWORD=mock-postgres-password")

    if 'env("REDIS_PASSWORD")' in prod_settings:
        required_env.extend([...])

    if 'env("CELERY_BROKER_URL")' in prod_settings:
        required_env.append(...)

    missing_env = [env for env in required_env if env not in dockerfile]

    if missing_env:
        ...
        return 1

    return 0
```

Note it reads the RAW template text (Jinja markers included), so the
substrings are present regardless of knobs today.

- `scripts/check_postgres_image.py` — pin-drift guard; `main()` compares
  `_tags(CANONICAL)` (regex `\bpostgres:(\d+\.\d+(?:\.\d+)?)\b` over
  `{{cookiecutter.project_slug}}/.docker/compose/prod.yaml`) against four
  other files, returns 1 on drift or when the canonical file doesn't contain
  exactly one tag. Both scripts read module-level `Path` constants inside
  `main()` — file I/O and check logic are currently fused.

- `.pre-commit-config.yaml:88-102` — the two `repo: local` hooks
  (`dockerfile-prod-env`, `postgres-image-pin`), `language: system`,
  `entry: python scripts/<name>.py`, `always_run: true`,
  `pass_filenames: false`. Line 4 excludes
  `^(\{\{cookiecutter\.project_slug\}\}/|hooks/|plans/)` from all hooks — a
  new root `tests/` directory IS covered by root linters (ruff etc.).

- `.github/workflows/ci.yaml:147-182` — `reject-invalid-input` job; matrix
  today:

```yaml
          - case: bad-description
            extra-args: description='has "quotes"'
          - case: bad-domain
            extra-args: domain_name=no-dot
          - case: bad-email
            extra-args: author_email=nope
          - case: bad-knob
            extra-args: use_celery=bogus
          - case: bad-slug
            extra-args: project_name='My  Project'
```

- `hooks/pre_gen_project.py` — seven validators; the three untested ones:
  slug length (`:28`, `MAX_SLUG_LENGTH = 50`), `author_name` forbidden chars
  (`:38`), `github_username` pattern (`:56`,
  `^[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})$`). All call `sys.exit(<message>)` so
  cookiecutter aborts before rendering.

Root CI runs `uvx pre-commit run --all-files` (ci.yaml `pre-commit` job), so
any new local pre-commit hook automatically runs in CI too.

## Commands you will need

| Purpose | Command | Expected on success |
|---------|---------|---------------------|
| Run root tests | `python -m unittest discover -s tests -t .` (repo root) | `OK`, exit 0 |
| Root pre-commit | `uvx pre-commit run --all-files` | exit 0 |
| Single hook | `uvx pre-commit run root-tests --all-files` | exit 0 |
| Reject-case rehearsal | `uvx cookiecutter . -o /tmp/verify-010 --no-input project_slug=$(python -c "print('a'*51)")` | non-zero exit, error mentions "50 characters or fewer" |
| Workflow lint | `uvx pre-commit run actionlint --all-files` | exit 0 |

## Scope

**In scope**:

- `scripts/check_dockerfile_prod_env.py` (refactor: pure check function +
  fail-closed)
- `scripts/check_postgres_image.py` (refactor: pure check function; behavior
  unchanged)
- `tests/` at repo root (create; `tests/__init__.py`,
  `tests/check_dockerfile_prod_env_test.py`,
  `tests/check_postgres_image_test.py`)
- `.pre-commit-config.yaml` (add one local `root-tests` hook)
- `.github/workflows/ci.yaml` (three new reject-matrix rows ONLY)

**Out of scope** (do NOT touch):

- `hooks/pre_gen_project.py` — the validators are correct; only CI coverage
  changes.
- Anything under `{{cookiecutter.project_slug}}/` — the generated project's
  own tests are a different suite.
- The bake matrix (`jobs.bake.strategy.matrix`) in ci.yaml — plan 012 owns a
  change there; touching it here risks a conflict.

## Git workflow

- Conventional commits, e.g. `test: cover the root invariant scripts and
  missing reject cases` (or split: one `refactor:`/`test:` for scripts+tests,
  one `ci:` for the matrix rows).
- Do NOT push unless instructed.

## Steps

### Step 1: Refactor `check_dockerfile_prod_env.py` to a pure, fail-closed check

Reshape so logic is injectable and an empty requirements list is an error:

```python
def check(dockerfile: str, prod_settings: str) -> list[str]:
    """Return human-readable problems; empty list means the check passes."""
    required_env = []
    # ... existing three substring blocks appending to required_env ...

    if not required_env:
        return [
            f"{PROD_SETTINGS_PATH}: no known env(...) accesses found; "
            "check_dockerfile_prod_env.py's detection is stale — update it",
        ]

    return [
        f"{DOCKERFILE_PATH}: collectstatic build env is missing {env}"
        for env in required_env
        if env not in dockerfile
    ]


def main() -> int:
    problems = check(DOCKERFILE_PATH.read_text(), PROD_SETTINGS_PATH.read_text())
    for problem in problems:
        print(problem)
    return 1 if problems else 0
```

Keep constants, docstring style, and the `if __name__ == "__main__":
raise SystemExit(main())` tail as-is.

**Verify**: `python scripts/check_dockerfile_prod_env.py` → exit 0 (current
tree satisfies the check).

### Step 2: Refactor `check_postgres_image.py` the same way

Extract `check(canonical_tags: set[str], file_tags: dict[str, set[str]]) ->
list[str]` (or equivalent pure signature) from `main()`; `main()` keeps the
file reading via `_tags` and prints/returns as today. Preserve the existing
stderr message wording.

**Verify**: `python scripts/check_postgres_image.py` → exit 0.

### Step 3: Add root unittest tests

Create `tests/__init__.py` (empty) and two test modules using stdlib
`unittest` (no pytest at root). Import via
`sys.path.insert(0, "scripts")`-free mechanism: prefer
`importlib.util.spec_from_file_location("check_dockerfile_prod_env",
"scripts/check_dockerfile_prod_env.py")` so no packaging changes are needed.

`tests/check_dockerfile_prod_env_test.py` cases:

1. matching inputs → `check(...)` returns `[]` (feed a dockerfile string
   containing all three mock env lines and a prod_settings string containing
   all three `env("...")` substrings)
2. dockerfile missing one line → exactly that problem reported
3. **fail-closed**: prod_settings with NO recognized substrings → non-empty
   problems (the stale-detection message)

`tests/check_postgres_image_test.py` cases:

1. all files agree on one tag → no problems
2. one file drifted → problem naming that file
3. canonical file with zero (or two) tags → problem

**Verify**: `python -m unittest discover -s tests -t .` → `OK` with 6 tests.

### Step 4: Wire the tests into root pre-commit

In `.pre-commit-config.yaml`, add to the `repo: local` block (after
`postgres-image-pin`, keeping alphabetical-ish grouping of the local hooks):

```yaml
      - id: root-tests
        name: root guard-script unit tests
        entry: python -m unittest discover -s tests -t .
        language: system
        pass_filenames: false
        always_run: true
```

**Verify**: `uvx pre-commit run root-tests --all-files` → exit 0; then
`uvx pre-commit run --all-files` → exit 0 (new `tests/` files must satisfy
root ruff/format hooks — fix style if flagged).

### Step 5: Add the three missing reject-matrix rows

In `.github/workflows/ci.yaml`, `reject-invalid-input` matrix, insert
(alphabetical by `case`, matching the existing list's ordering):

```yaml
          - case: bad-author-name
            extra-args: author_name='has "quotes"'
          - case: bad-slug-length
            extra-args: project_slug=aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
          - case: bad-username
            extra-args: github_username=-bad-
```

(`bad-author-name` sorts before `bad-description`; `bad-slug-length` after
`bad-slug`; `bad-username` last. The slug is 51 × `a` — passes the character
pattern, fails only the length check. `-bad-` starts with a hyphen, failing
the username pattern.)

**Verify**:
- `python -c "print(len('aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa'))"` → `51`
- `uvx pre-commit run actionlint --all-files` and
  `uvx pre-commit run check-github-workflows --all-files` → exit 0
- Rehearse each case locally, e.g.
  `uvx cookiecutter . -o /tmp/verify-010 --no-input github_username=-bad-`
  → non-zero exit, message about a valid GitHub username, and
  `find /tmp/verify-010 -mindepth 1 -maxdepth 1 -type d` → empty.

## Test plan

Steps 3's six unittest cases are the new tests; the reject rows are
CI-executed tests by construction (each asserts the bake FAILS). Structural
pattern: none exists at root yet — this plan establishes it; keep it stdlib
`unittest` so `language: system` hooks need no dependencies.

## Done criteria

- [ ] `python scripts/check_dockerfile_prod_env.py` exits 0 on the current
  tree, and exits 1 if you temporarily blank `prod.py`'s content in the test
  (covered by unittest case 3 — no manual mutation of the repo)
- [ ] `python -m unittest discover -s tests -t .` → `OK`, ≥6 tests
- [ ] `uvx pre-commit run --all-files` exits 0 (includes the new hook)
- [ ] ci.yaml reject matrix has 8 cases; actionlint passes
- [ ] Each of the 3 new invalid inputs rejected in a local rehearsal
- [ ] `git status` clean apart from in-scope files
- [ ] `plans/README.md` status row updated

## STOP conditions

Stop and report back if:

- The local-hook `python` interpreter cannot run the tests (e.g. `python`
  resolves to Python 2 or is missing) — do not silently switch to `python3`
  in only one place; report so the entry lines stay consistent with the two
  existing local hooks.
- `uvx pre-commit run --all-files` fails on the new tests for reasons other
  than style (would indicate the refactor changed script behavior).
- The reject rehearsal for `bad-slug-length` produces a GENERATED project
  (would mean `pre_gen` ordering changed and the pattern check fires first
  with a different message — re-check `hooks/pre_gen_project.py`).

## Maintenance notes

- Future guard scripts in `scripts/` should follow the pure-`check()` +
  thin-`main()` shape and get a module in root `tests/` — the `root-tests`
  hook picks them up automatically via unittest discovery.
- If `prod.py` legitimately stops using one of the three `env("...")`
  accesses, update BOTH the script's substring blocks and the tests — the
  fail-closed branch will force this, which is the point.
- Plan 013 adds more root tests to this same `tests/` directory — land this
  plan first.
