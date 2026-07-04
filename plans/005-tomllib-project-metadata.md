# Plan 005: Read project metadata with stdlib tomllib; drop pyproject-parser and the CWD trap

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving to the
> next step. If anything in the "STOP conditions" section occurs, stop and
> report — do not improvise. When done, update the status row for this plan
> in `plans/README.md` — unless a reviewer dispatched you and told you they
> maintain the index.
>
> **Drift check (run first)**: `git diff --stat 924bfba..HEAD -- '{{cookiecutter.project_slug}}/src/config/pyproject.py' '{{cookiecutter.project_slug}}/tests/unit/config/pyproject_test.py' '{{cookiecutter.project_slug}}/pyproject.toml'`
> On any change, compare "Current state" excerpts against the live code; on a
> mismatch, treat it as a STOP condition.

## Status

- **Priority**: P2
- **Effort**: S
- **Risk**: LOW
- **Depends on**: none (coordinates with 001's Step 3 if both run — see note)
- **Category**: tech-debt / perf
- **Planned at**: commit `924bfba`, 2026-07-04

## Why this matters

`src/config/pyproject.py` exists to expose the project's name and version to
the `NinjaAPI` title/version. It does this with `pyproject-parser==0.14.0`, a
runtime dependency with a non-trivial transitive tree (`dom-toml`,
`domdf-python-tools`, `apeye`, `natsort`, …) shipped into the prod image and
parsed at import time in every process (each gunicorn worker, each celery
worker, every `manage.py` run). Worse, `PyProject.load("pyproject.toml")` is
**CWD-relative**: it works only because every current entrypoint happens to run
from the project root; any cron job or script started elsewhere crashes at
import with `FileNotFoundError`, cascading into a failed URLconf. Python 3.14's
stdlib `tomllib` reads the same two fields with zero dependencies, and an
absolute path anchored to the file removes the CWD trap.

A second win, empirically verified during planning: with pyproject-parser,
importing `config.pyproject` **reads `README.md` from disk** (its PEP 621
parser resolves the `readme = "README.md"` field; the import raises
`FileNotFoundError` when the file is absent). That is the only reason
`README.md` must ship in the Docker image today — `tomllib` just parses the
TOML string, and since `pyproject.toml` declares no `[build-system]`, uv
treats the project as virtual and never builds/installs it (also verified:
no distribution is installed in the venv). So once this plan lands,
`README.md` becomes dead weight in the runtime image and gets dockerignored
(Step 4).

**Coordination with Plan 015**: 015 retires `project_version` entirely (the
API contract version becomes an explicit literal). Check `plans/README.md`:
if 015 is DONE, `config/pyproject.py` no longer has version handling — write
the Step 1 rewrite WITHOUT the `project_version` lines and the version guard,
and skip the version test in Step 2. If 015 is still TODO, keep them as
written here; 015 will remove them later.

## Important context: this is a cookiecutter template

- Project code lives under the literal `{{cookiecutter.project_slug}}/` dir —
  quote it in shell. Files may contain Jinja placeholders — preserve them
  (`pyproject.toml`'s `name = "{{ cookiecutter.project_slug }}"` line must
  stay exactly as is).
- Verification = bake + run the baked suite. The bake's post-gen hook runs
  `uv lock`, so dependency changes re-lock automatically in fresh bakes.

## Current state

- `{{cookiecutter.project_slug}}/src/config/pyproject.py` (whole file):

  ```python
  from pyproject_parser import PyProject

  pyproject = PyProject.load("pyproject.toml")
  project_metadata = pyproject.project

  if project_metadata is None:
      msg = "pyproject.toml must include [project] metadata."
      raise RuntimeError(msg)

  project_name = project_metadata["name"]
  project_version = project_metadata["version"]

  if project_version is None:
      msg = "pyproject.toml must include project.version."
      raise RuntimeError(msg)
  ```

- Consumers: `src/apps/api/api.py:3` (`from config.pyproject import
  project_name, project_version`), `tests/unit/api/api_test.py`,
  `tests/unit/config/pyproject_test.py` (mocks `pyproject_parser.PyProject.load`).
- `{{cookiecutter.project_slug}}/pyproject.toml:26` —
  `"pyproject-parser==0.14.0",` in `[project].dependencies`.
- Path anatomy: `src/config/pyproject.py` → `Path(__file__).resolve()` parents
  are `config` → `src` → project root. The settings package anchors the same
  way (`src/config/settings/__init__.py:7` uses four `.parent`s from one level
  deeper — mirror the idiom).
- Conventions: Ruff `ALL`; module-level guard style with `msg = ...; raise
  RuntimeError(msg)` (keep it — it satisfies Ruff's EM rules).

## Commands you will need

| Purpose | Command | Expected on success |
|---------|---------|---------------------|
| Bake | `uvx cookiecutter . --no-input -o $BAKE` | exit 0 |
| Tests | `cd $BAKE/my-project && uv run pytest` | all pass, 100% |
| Hooks | `cd $BAKE/my-project && git add -A && uv run pre-commit run --all-files` | all pass |
| CWD regression check (inside bake) | `env DJANGO_ENV=ci ALLOWED_HOSTS=x CACHE_URL=locmemcache:// DATABASE_URL=sqlite:///:memory: SECRET_KEY=s PYTHONPATH=$PWD/src DJANGO_SETTINGS_MODULE=config.settings $PWD/.venv/bin/python -c "import config.pyproject; print(config.pyproject.project_name)"` run from `/` | prints `my-project` |

## Scope

**In scope**:
- `{{cookiecutter.project_slug}}/src/config/pyproject.py`
- `{{cookiecutter.project_slug}}/tests/unit/config/pyproject_test.py`
- `{{cookiecutter.project_slug}}/pyproject.toml` (remove one dependency line)
- `{{cookiecutter.project_slug}}/.docker/Dockerfile.dockerignore` (add README.md)

**Out of scope**:
- `src/apps/api/api.py` and `tests/unit/api/api_test.py` — the exported names
  (`project_name`, `project_version`, `project_metadata`) keep their contracts.
- Switching to `importlib.metadata` — viable but couples metadata to the
  installed distribution; the maintainer's current design reads the file. Keep
  file-based.

## Git workflow

- Branch: `advisor/005-tomllib-project-metadata`
- Conventional commit, e.g. `refactor: read project metadata with tomllib`
- Do NOT push or open a PR unless the operator instructed it.

## Steps

### Step 1: Rewrite the module

Replace `src/config/pyproject.py` with:

```python
import tomllib
from pathlib import Path

PYPROJECT_PATH = Path(__file__).resolve().parent.parent.parent / "pyproject.toml"

with PYPROJECT_PATH.open("rb") as pyproject_file:
    pyproject = tomllib.load(pyproject_file)

project_metadata = pyproject.get("project")

if project_metadata is None:
    msg = "pyproject.toml must include [project] metadata."
    raise RuntimeError(msg)

project_name = project_metadata["name"]
project_version = project_metadata.get("version")

if project_version is None:
    msg = "pyproject.toml must include project.version."
    raise RuntimeError(msg)
```

Contract notes: `project_version` was previously a `Version` object rendered
via `str(...)` in `api.py` (`version=str(project_version)`); with tomllib it
is already a `str`, and `str(str)` is a no-op — `api.py` needs no change.
`pyproject` changes type from `PyProject` to `dict` — grep confirms only the
test file touches it.

### Step 2: Update the unit tests

Rewrite `tests/unit/config/pyproject_test.py` mocks from
`pyproject_parser.PyProject.load` to `tomllib.load` returning plain dicts:

- happy-path test: assert `project_metadata == pyproject["project"]`,
  `project_name == project_metadata["name"]`, `project_version ==
  project_metadata["version"]` (drop the `isinstance(pyproject, PyProject)`
  assertion; assert `isinstance(pyproject, dict)` instead).
- missing-`[project]` test: `patch("tomllib.load", return_value={})`, pop
  `config.pyproject` from `sys.modules`, expect `RuntimeError` matching
  `\[project\] metadata`.
- missing-version test: `patch("tomllib.load", return_value={"project":
  {"name": "example"}})`, expect `RuntimeError` matching `project\.version`.
- Keep `_restore_pyproject_module()`; if Plan 001 already landed, its
  try/finally shape around these bodies must be preserved (see 001 Step 3).

**Verify**: bake → `uv run pytest tests/unit/config/pyproject_test.py` → all
pass.

### Step 3: Drop the dependency

Remove the `"pyproject-parser==0.14.0",` line from
`{{cookiecutter.project_slug}}/pyproject.toml` `[project].dependencies`.

**Verify**: fresh bake (post-gen re-locks) →
`grep -rn pyproject_parser $BAKE/my-project/src $BAKE/my-project/tests` → no
matches; `grep -n pyproject-parser $BAKE/my-project/uv.lock` → no matches.

### Step 4: Drop README.md from the Docker image

Add `README.md` to `{{cookiecutter.project_slug}}/.docker/Dockerfile.dockerignore`.
This file is kept byte-sorted by the `file-contents-sorter` pre-commit hook —
insert in sorted position (between `.vscode/` and `TODO.md`; capital letters
sort before lowercase, so run the hook to confirm placement).

This is safe ONLY because of this plan's rewrite: the old pyproject-parser
code read `README.md` at import time inside the container (verified —
`FileNotFoundError` without it), while `tomllib` does not, and the image
build never installs the project as a distribution (no `[build-system]`).

**Verify** (needs Docker): in a fresh bake,
`docker build -f .docker/Dockerfile --build-arg UV_DEPENDENCY_GROUP=prod -t t005 .`
→ exit 0 (the build's `collectstatic` loads full prod settings). Then prove
the runtime import path works without the README in the image:

```
docker run --rm -e DJANGO_ENV=prod -e ALLOWED_HOSTS=example.com \
  -e AWS_STORAGE_BUCKET_NAME=b -e CACHE_URL=locmemcache:// \
  -e CSRF_TRUSTED_ORIGINS=https://example.com -e DATABASE_URL=sqlite:///:memory: \
  -e SECRET_KEY=some-long-random-value t005 \
  python -c "import config.pyproject; print(config.pyproject.project_name)"
```

→ prints `my-project`. (Add `-e SENTRY_DSN=... -e RESEND_API_KEY=...` dummies
if plans 007/009 have landed.) Also confirm the file is really absent:
`docker run --rm --entrypoint sh t005 -c "test ! -f README.md"` → exit 0.
If Docker is unavailable, state so in the PR and rely on the CI docker-build
job — but do not skip the dockerignore sorting verification.

### Step 5: Full verification loop + CWD regression check

**Verify**:
- Fresh bake → `uv run pytest` → all pass, 100%
- `git add -A && uv run pre-commit run --all-files` → all pass
- The CWD regression check from the commands table, run with CWD `/` → prints
  `my-project` (this is the behavior that was previously broken).

## Test plan

Step 2's three rewritten tests, same file, same naming conventions. The CWD
fix is verified by the Step 4 command (import from `/`), which fails on the
old code with `FileNotFoundError`.

## Done criteria

- [ ] `grep -rn "pyproject_parser\|pyproject-parser" '{{cookiecutter.project_slug}}'` → no matches (excluding this plans/ directory)
- [ ] Baked project: `uv run pytest` → all pass, 100%
- [ ] Baked project: import `config.pyproject` with CWD=/ succeeds
- [ ] `README.md` listed in `.docker/Dockerfile.dockerignore` (sorted); prod image builds and imports `config.pyproject` without it
- [ ] Baked project: `uv run pre-commit run --all-files` → all pass
- [ ] No files outside the in-scope list modified (`git status`)
- [ ] `plans/README.md` status row updated

## STOP conditions

- `api.py` or any other module turns out to rely on `PyProject`-specific
  attributes beyond the three exported names (grep first; if found, report).
- `ty` (the type checker pre-commit hook) rejects the `tomllib` usage in a way
  that needs suppressions beyond one targeted `# ty: ignore[...]` — report
  instead of stacking ignores.

## Maintenance notes

- The module now hard-anchors to `src/config/../..` — if the `src/` layout
  ever changes depth, this path (and `settings/__init__.py`'s `BASE_DIR`)
  change together.
- If the project is later distributed as an installed package (no
  `pyproject.toml` on disk at runtime), switch to `importlib.metadata` — the
  Dockerfile currently ships the whole `/app` tree, so the file is present.
