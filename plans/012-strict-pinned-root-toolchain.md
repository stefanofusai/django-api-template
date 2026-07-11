# Plan 012: Give template development a strict pinned pyproject and lockfile

> **Executor instructions**: Treat all tool pins as one synchronized contract.
> Run every gate and update the index. Do not partially pin the toolchain.
>
> **Drift check (run first)**: `rtk git diff --stat b367191..HEAD -- 'README.md' 'CONTRIBUTING.md' 'AGENTS.md' '.github/workflows/' '.pre-commit-config.yaml' 'hooks/post_gen_project.py' 'scripts/' '{{cookiecutter.project_slug}}/pyproject.toml' '{{cookiecutter.project_slug}}/.docker/Dockerfile' '{{cookiecutter.project_slug}}/.pre-commit-config.yaml'`

## Status

- **Priority**: P2
- **Effort**: M
- **Risk**: MED
- **Depends on**: none
- **Category**: dependencies, dx
- **Planned at**: commit `b367191`, 2026-07-10

## Why this matters

The generated application has exact dependency pins and a committed lockfile,
but template development uses ambient uv plus unpinned `uvx cookiecutter`,
pytest, and pre-commit. On the planning host, ambient uv was 0.9.15 while the
Docker/pre-commit template pin was 0.11.19, and `uvx pytest` selected 9.1.1
instead of the generated 9.0.3. The same template commit therefore does not
have one reproducible development/generation toolchain.

## Current state

- Root has no `pyproject.toml` or `uv.lock`.
- Current supported tool targets: Python `>=3.14,<3.15`, uv `0.11.19`,
  Cookiecutter `2.7.1`, pre-commit `4.6.0`, pytest `9.1.1` for root-only tests.
- `setup-uv` installs latest when no `required-version` exists.
- Generated Docker and uv pre-commit hooks already pin uv 0.11.19.
- Root scripts call `uvx cookiecutter`, `uvx pytest`, and `uvx pre-commit`.

## Commands you will need

| Purpose | Command | Expected |
|---|---|---|
| Sync | `rtk uv sync --locked` | exact root environment installed |
| Root tests | `rtk uv run pytest tests` | pass |
| Root checks | `rtk uv run pre-commit run --all-files` | exit 0 |
| Pin check | `rtk uv --version` | output starts `uv 0.11.19` |

## Scope

**In scope**:
- `pyproject.toml` (create)
- `uv.lock` (create)
- root README, CONTRIBUTING, AGENTS
- root workflows, pre-commit config, and maintenance scripts that invoke tools
- `hooks/post_gen_project.py`
- `{{cookiecutter.project_slug}}/pyproject.toml`
- synchronized uv pins in generated Docker/pre-commit/workflows
- focused invariant tests

**Out of scope**:
- Updating application runtime dependencies.
- Replacing pre-commit-managed linters with project dependencies.
- Allowing version ranges for direct root tools.

## Git workflow

Do not commit or push unless explicitly requested. `pyproject.toml` and
`uv.lock` must always be reviewed and landed together.

## Steps

### Step 1: Create the strict root project

Create a non-package root `pyproject.toml` with:

- `[project]` metadata and `requires-python = ">=3.14,<3.15"`;
- an exact development group containing `cookiecutter==2.7.1`,
  `pre-commit==4.6.0`, and `pytest==9.1.1`;
- `[tool.uv] package = false` and `required-version = "==0.11.19"`;
- minimal pytest configuration for root `tests/` only.

Generate and commit the root `uv.lock` with uv 0.11.19. Do not add application
dependencies to the root environment.

**Verify**: `uv sync --locked` and `uv run pytest tests` pass; an intentionally
wrong uv version is rejected by `required-version`.

### Step 2: Put the same uv requirement in generated projects

Add `required-version = "==0.11.19"` to the existing generated `[tool.uv]`
table. Confirm Docker's uv image, uv pre-commit revision, root requirement,
and generated requirement are identical. Let `setup-uv` resolve from the
checked-in pyproject; add explicit `version` only where action working
directory prevents discovery.

**Verify**: default bake produces a lock with uv 0.11.19 and every generated
workflow installs the same tool version.

### Step 3: Replace floating `uvx` development commands

Change root CI/scripts/docs from unqualified `uvx cookiecutter`, pytest, and
pre-commit to `uv run --locked ...` through the root project. For the end-user
one-shot GitHub template command, use an exact tool selector such as
`uvx --from=cookiecutter==2.7.1 cookiecutter ...` so consumers do not need the
root checkout first.

Update `post_gen_project.py` warning text: an incompatible uv must fail loudly
with instructions to install 0.11.19; do not silently generate a lock with a
different version.

**Verify**: fff content search finds no unversioned root `uvx cookiecutter`,
`uvx pytest`, or `uvx pre-commit` command.

### Step 4: Add synchronization tests

Create a root test/check that extracts the uv requirement from root and
generated pyprojects, the Docker image, and the generated uv pre-commit hook.
Require exactly one version. Also assert root direct tool dependencies use
`==` pins and `uv.lock` is current.

**Verify**: perturbing any one fixture/pin makes the focused test fail with the
drifted path named.

### Step 5: Run the complete matrix-sensitive checks

Run root sync/tests/pre-commit, bake default/minimal/maximal projects, and run
their locked sync, pytest, and pre-commit.

**Verify**: every command exits 0; generated locks are created only with the
required uv version.

## Test plan

Test exact root pins, uv pin agreement, stale root lock failure, wrong ambient
uv rejection, setup-uv discovery, and exact Cookiecutter use in docs/CI.

## Done criteria

- [ ] Root `pyproject.toml` has exact tool pins and a committed `uv.lock`.
- [ ] Root and generated projects require uv 0.11.19.
- [ ] Root CI and scripts run locked tools, not latest `uvx` environments.
- [ ] End-user Cookiecutter command specifies 2.7.1.
- [ ] Pin-agreement and lock-drift tests pass.

## STOP conditions

- Cookiecutter 2.7.1 or pytest 9.1.1 cannot resolve on Python 3.14 under uv
  0.11.19.
- `setup-uv` does not honor `[tool.uv].required-version` in a generated
  workflow's working directory.
- A root tool must remain floating for a documented compatibility reason.

## Maintenance notes

Future tool upgrades are deliberate atomic changes: root manifest/lock,
generated requirement, Docker/pre-commit pins, workflows, docs, and invariant
fixtures must move together.
