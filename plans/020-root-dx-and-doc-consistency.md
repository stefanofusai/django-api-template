# Plan 020: Provide one locked verification command and consistent generated docs

> **Executor instructions**: Keep documentation executable and tests
> side-effect-contained. Run all gates and update the index.
>
> **Drift check (run first)**: `rtk git diff --stat b367191..HEAD -- 'pyproject.toml' 'uv.lock' '.pre-commit-config.yaml' 'AGENTS.md' 'README.md' 'CONTRIBUTING.md' 'scripts/' 'tests/' '{{cookiecutter.project_slug}}/README.md'`

## Status

- **Priority**: P3
- **Effort**: M
- **Risk**: LOW
- **Depends on**: plan 012
- **Category**: dx, docs
- **Planned at**: commit `b367191`, 2026-07-10

## Why this matters

Contributors currently retype the bake, environment, Postgres, pytest, and
pre-commit sequence. The root AGENTS verification recipe uses a foreground
Compose command before a later curl, so it cannot run verbatim. Root Python
maintenance scripts are Ruff-tested but not type-checked. Generated README
branches also contradict themselves about authentication and Redis credentials.

## Current state

- Root README has the correct detached `up -d --wait` sequence.
- Root AGENTS uses foreground `up --build` before readiness curl.
- Generated README describes protected notes and then says the whole API ships
  unauthenticated; a Postgres conditional also unconditionally mentions
  `REDIS_PASSWORD`.
- Plan 012 supplies a locked root pyproject and lockfile.

## Commands you will need

| Purpose | Command | Expected |
|---|---|---|
| Wrapper help | `rtk uv run --locked python scripts/verify_bake.py --help` | exit 0 |
| Root typecheck | `rtk uv run --locked ty check scripts tests` | exit 0 |
| Root checks | `rtk uv run --locked pre-commit run --all-files` | exit 0 |

## Scope

**In scope**:
- root `pyproject.toml`/`uv.lock` for exact Ty pin
- `.pre-commit-config.yaml`
- `scripts/verify_bake.py` (create) and root unit tests
- root README, CONTRIBUTING, AGENTS
- `{{cookiecutter.project_slug}}/README.md`

**Out of scope**:
- A Makefile/Just dependency.
- Changing authentication or Redis topology behavior.
- Type-checking Jinja-bearing hooks.

## Git workflow

Do not commit or push unless explicitly requested.

## Steps

### Step 1: Add a tested one-command verifier

Create an argparse-based root script that accepts repeated Cookiecutter
`key=value` options plus an output path, bakes with the pinned root
Cookiecutter, copies `.env.example`, starts only Postgres, runs full pytest and
pre-commit, and always tears Compose down in `finally`. Default to a temporary
output directory and print its location on failure. Use structured subprocess
argument lists, never shell interpolation.

Unit-test command construction, option validation, failure propagation, and
guaranteed teardown with mocked subprocess calls.

**Verify**: root unit tests pass without Docker.

### Step 2: Type-check root maintenance code

Add the current exact Ty version to the root development group and refresh the
root lock. Configure Ty for plain root `scripts/` and `tests/`, excluding Jinja
hooks/template source. Add a root pre-commit hook invoking the locked Ty binary.
Fix only genuine root typing issues; do not blanket-ignore modules.

**Verify**: `ty check scripts tests` and root pre-commit pass.

### Step 3: Make verification docs executable

Replace duplicated recipes in root README, CONTRIBUTING, and AGENTS with the
wrapper command plus an expanded manual sequence where useful. Every manual
Compose start before curl must use detached `-d --wait`; include `.env` copy
and teardown.

**Verify**: run each documented root command block in a temporary bake.

### Step 4: Correct generated conditional prose

Render the “API ships unauthenticated” paragraph only when no example API is
included. For example bakes, state probes are public and notes use the selected
auth. Split password guidance by independent Postgres/Redis knobs so external
Redis projects never mention a nonexistent `REDIS_PASSWORD` or boot guard.

**Verify**: inspect all four backing topology README renders plus example/no
example auth renders with focused root snapshot/string assertions.

## Test plan

Mocked wrapper orchestration tests, Ty gate, documented command smoke, and
rendered prose assertions across relevant knobs.

## Done criteria

- [ ] One locked command performs full bake verification and always tears down.
- [ ] Root scripts/tests pass Ty.
- [ ] Root command recipes run verbatim.
- [ ] Generated auth and Redis guidance is truthful in every relevant bake.

## STOP conditions

- Wrapper implementation would need to parse shell strings from user input.
- Ty requires checking Jinja-invalid hook/template files.
- Documentation branches cannot be tested without brittle full-file snapshots.

## Maintenance notes

The wrapper is the canonical root verification path. Update it and all three
root docs together when verification changes.
