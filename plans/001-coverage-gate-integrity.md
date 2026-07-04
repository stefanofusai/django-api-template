# Plan 001: Make the 100% coverage gate actually cover src/, and fix test-isolation leaks

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving to the
> next step. If anything in the "STOP conditions" section occurs, stop and
> report — do not improvise. When done, update the status row for this plan
> in `plans/README.md` — unless a reviewer dispatched you and told you they
> maintain the index.
>
> **Drift check (run first)**: `git diff --stat 924bfba..HEAD -- '{{cookiecutter.project_slug}}/pyproject.toml' '{{cookiecutter.project_slug}}/tests/'`
> If any in-scope file changed since this plan was written, compare the
> "Current state" excerpts against the live code before proceeding; on a
> mismatch, treat it as a STOP condition.

## Status

- **Priority**: P1
- **Effort**: S
- **Risk**: MED (the honest gate goes red until the omit policy is in place)
- **Depends on**: none
- **Category**: tests
- **Planned at**: commit `924bfba`, 2026-07-04

## Why this matters

This repo is a cookiecutter template whose flagship claim is "pytest with 100%
coverage". That gate is currently weaker than it reads: `--cov` with no source
argument only measures files that get *imported* during the test run. It was
empirically reproduced during the audit that a module never imported by any
test is simply absent from the report and the gate still passes at 100% —
`src/config/settings/environments/prod.py` and `dev.py` are in exactly that
blind spot today (tests run with `DJANGO_ENV=ci`, so only `ci.py` loads).
Additionally, two tests mutate global state without cleanup guards, which can
cascade failures under `pytest-randomly` + `pytest-xdist`. This plan makes the
gate enumerate all of `src/` and fixes the two isolation leaks.

## Important context: this is a cookiecutter template

- All project code lives under the literal directory
  `{{cookiecutter.project_slug}}/` — **always quote this path in shell
  commands** (it contains braces).
- Files inside it may contain Jinja placeholders like
  `{{ cookiecutter.project_slug }}` — preserve them verbatim; never "fix" them.
- Verification always happens by **baking** a project and running its suite,
  because the template repo itself has no test runner.

## Current state

- `{{cookiecutter.project_slug}}/pyproject.toml:70-71` — coverage config:

  ```toml
  [tool.coverage.run]
  branch = true
  ```

- `{{cookiecutter.project_slug}}/pyproject.toml:78`:

  ```toml
  addopts = "--cov --cov-fail-under=100 --cov-report=term-missing:skip-covered --numprocesses=auto"
  ```

- `{{cookiecutter.project_slug}}/tests/integration/api/request_id_test.py:14-22`
  binds a structlog contextvar and clears it only on the test's last line — a
  failing assertion leaks `request_id` into subsequent tests on the same
  worker:

  ```python
  def test_failure_response_includes_request_id_from_context() -> None:
      logger = structlog.get_logger()
      response = HttpResponse(status=HTTPStatus.INTERNAL_SERVER_ERROR)
      structlog.contextvars.bind_contextvars(request_id="failed-request")

      add_request_id_to_failure_response(object(), logger, response)

      assert response.headers["X-Request-ID"] == "failed-request"
      structlog.contextvars.clear_contextvars()
  ```

- `{{cookiecutter.project_slug}}/tests/unit/config/pyproject_test.py:19-48`
  pops `config.pyproject` from `sys.modules` and restores it via
  `_restore_pyproject_module()` placed *after* the `with pytest.raises(...)`
  block — if the `raises` expectation is unmet, restoration is skipped.

- Why `prod.py`/`dev.py` cannot simply be imported by a test: the settings use
  `django-split-settings`; environment overlays reference names (`MIDDLEWARE`,
  `LOGGING`, `STORAGES`, `INSTALLED_APPS`) that only exist in the shared
  `include()` exec namespace (see the `noqa: F821` markers in
  `src/config/settings/environments/prod.py`). They are **not importable as
  standalone modules**. Their real executable verification is the CI deploy
  check (`{{cookiecutter.project_slug}}/.github/workflows/tests.yaml:25-35`),
  which runs `manage.py check --deploy` with `DJANGO_ENV=prod`.

- Repo conventions (from `{{cookiecutter.project_slug}}/AGENTS.md`): keep
  changes Ruff-clean (`select = ["ALL"]`), pyproject subsections alphabetical,
  no tests that only assert configuration values.

## Commands you will need

Run from the template repo root unless stated otherwise. `$BAKE` is any
scratch dir, e.g. `/tmp/bake-001`.

| Purpose | Command | Expected on success |
|---------|---------|---------------------|
| Bake    | `uvx cookiecutter . --no-input -o $BAKE` | exit 0; project at `$BAKE/my-project` (post-gen hook runs `git init` + `uv lock`) |
| Tests   | `cd $BAKE/my-project && uv run pytest` | all pass; `Required test coverage of 100% reached` |
| Hooks   | `cd $BAKE/my-project && git add -A && uv run pre-commit run --all-files` | all hooks pass |

## Scope

**In scope** (the only files you should modify):
- `{{cookiecutter.project_slug}}/pyproject.toml` (coverage/pytest config only)
- `{{cookiecutter.project_slug}}/tests/integration/api/request_id_test.py`
- `{{cookiecutter.project_slug}}/tests/unit/config/pyproject_test.py`

**Out of scope** (do NOT touch):
- `src/config/settings/environments/*.py` — do not restructure settings to
  make overlays importable; the omit + CI deploy check is the accepted policy.
- Any workflow file.
- Adding new tests for settings values (explicitly forbidden by AGENTS.md).

## Git workflow

- Branch: `advisor/001-coverage-gate-integrity`
- Conventional commits (gitlint enforces), e.g.
  `test: make coverage measure all of src and fix test isolation`
- Do NOT push or open a PR unless the operator instructed it.

## Steps

### Step 1: Point coverage at src/ and add the omit policy

In `{{cookiecutter.project_slug}}/pyproject.toml`:

1. In `addopts`, change `--cov` to `--cov=src` (rest of the line unchanged).
2. Extend the coverage config:

   ```toml
   [tool.coverage.run]
   branch = true
   # Environment overlays execute inside django-split-settings' include()
   # namespace and cannot be imported standalone; prod.py is exercised by the
   # `manage.py check --deploy` step in .github/workflows/tests.yaml.
   omit = [
       "src/config/settings/environments/dev.py",
       "src/config/settings/environments/prod.py",
   ]
   ```

**Verify**: bake fresh (`uvx cookiecutter . --no-input -o $BAKE`), then
`cd $BAKE/my-project && uv run pytest` → passes at 100%. Then prove the gate
now has teeth: in the *baked* copy create `src/apps/core/unused_module.py`
containing `def f():\n    return 1`, rerun `uv run pytest` → **fails** with
total < 100% and `unused_module.py` listed. Delete the file, rerun → passes.

### Step 2: Fix the contextvars leak

In `tests/integration/api/request_id_test.py`, wrap the body of
`test_failure_response_includes_request_id_from_context` so cleanup always
runs:

```python
def test_failure_response_includes_request_id_from_context() -> None:
    logger = structlog.get_logger()
    response = HttpResponse(status=HTTPStatus.INTERNAL_SERVER_ERROR)
    structlog.contextvars.bind_contextvars(request_id="failed-request")

    try:
        add_request_id_to_failure_response(object(), logger, response)

        assert response.headers["X-Request-ID"] == "failed-request"

    finally:
        structlog.contextvars.clear_contextvars()
```

(Blank lines around control-flow branches are an AGENTS.md style rule — keep
them.)

**Verify**: `uv run pytest tests/integration/api/request_id_test.py` in the
baked copy (re-bake or copy the file in) → 3 tests pass.

### Step 3: Make pyproject_test restoration unconditional

In `tests/unit/config/pyproject_test.py`, in both
`test_pyproject_raises_when_project_metadata_is_missing` and
`test_pyproject_raises_when_project_version_is_missing`, move the
`_restore_pyproject_module()` call into a `finally:` so an unmet `raises`
cannot strand `sys.modules`:

```python
    try:
        with patch("pyproject_parser.PyProject.load", return_value=parsed_pyproject):
            sys.modules.pop("config.pyproject", None)

            with pytest.raises(RuntimeError, match=r"\[project\] metadata"):
                importlib.import_module("config.pyproject")

    finally:
        _restore_pyproject_module()
```

(Adjust the `match=` per test; keep the existing patterns.)

Note: if Plan 005 (tomllib swap) has already landed, this file will mock
`tomllib.load` instead of `PyProject.load` — apply the same try/finally shape
to whatever the current test bodies are.

**Verify**: `uv run pytest tests/unit/config/` in the baked copy → all pass.

### Step 4: Full verification loop

Bake fresh, run the full suite and hooks.

**Verify**:
- `uvx cookiecutter . --no-input -o $BAKE2` → exit 0
- `cd $BAKE2/my-project && uv run pytest` → all pass, coverage 100%
- `git add -A && uv run pre-commit run --all-files` → all hooks pass

## Test plan

No new test files. The changed behavior is the gate itself; its test is the
Step 1 red/green experiment (unused module → gate fails → remove → passes).
Existing tests must all still pass.

## Done criteria

- [ ] `grep -n 'cov=src' '{{cookiecutter.project_slug}}/pyproject.toml'` → one match in `addopts`
- [ ] `grep -n 'omit' '{{cookiecutter.project_slug}}/pyproject.toml'` → present with exactly the two environment overlay entries
- [ ] Baked project: `uv run pytest` → 100%, all pass
- [ ] Baked project + planted unused module → `uv run pytest` fails (gate has teeth)
- [ ] `uv run pre-commit run --all-files` in baked project → all pass
- [ ] No files outside the in-scope list are modified (`git status`)
- [ ] `plans/README.md` status row updated

## STOP conditions

Stop and report back (do not improvise) if:

- After Step 1 the baked suite fails at 100% for any file **other than** the
  two omitted overlays (that means some other module is silently unimported —
  report which, don't omit it without a decision).
- The `pyproject_test.py` on disk no longer matches either the excerpt above
  or the Plan 005 (tomllib) shape.
- You find yourself wanting to add a test that imports `prod.py`/`dev.py`
  directly — that contradicts the split-settings design; stop.

## Maintenance notes

- Every future plan that adds a module under `src/` is now genuinely forced to
  test it. If a future module legitimately cannot run under `DJANGO_ENV=ci`,
  the omit list is the escape hatch — each entry needs a comment saying what
  covers it instead.
- Reviewers should reject any PR that grows the omit list without a stated
  alternative verification.
