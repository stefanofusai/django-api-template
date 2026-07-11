# Plan 014: Remove django-ninja-extra from feature-minimal bakes

> **Executor instructions**: Preserve it for every feature that imports it.
> Run the full option checks and update the index.
>
> **Drift check (run first)**: `rtk git diff --stat b367191..HEAD -- 'hooks/post_gen_project.py' '{{cookiecutter.project_slug}}/pyproject.toml' '{{cookiecutter.project_slug}}/src/apps/api/' '{{cookiecutter.project_slug}}/tests/api/' '.github/workflows/ci.yaml'`

## Status

- **Priority**: P2
- **Effort**: S
- **Risk**: LOW
- **Depends on**: plan 012
- **Category**: dependencies
- **Planned at**: commit `b367191`, 2026-07-10

## Why this matters

`django-ninja-extra` is unconditional even when the example API and throttling
are both absent. In those bakes, `ninja_extra` is not installed as an app, but
the unused pagination module/test remain and force an otherwise unnecessary
runtime framework and transitive dependency surface.

## Current state

- `pyproject.toml` always includes `django-ninja-extra==0.31.5`.
- `apps.py:27-29` installs it only for throttling or the example API.
- `pagination.py` and its unit test import it but are useful only to the notes
  example.
- `throttling.py` also imports it and is already pruned when throttling is off.

## Commands you will need

| Purpose | Command | Expected |
|---|---|---|
| Minimal bake | `rtk uvx cookiecutter . -o /tmp/plan-014-min --no-input use_example_api=no api_throttling=none` | created |
| Throttle bake | `rtk uvx cookiecutter . -o /tmp/plan-014-throttle --no-input api_throttling=basic` | created |
| Example bake | `rtk uvx cookiecutter . -o /tmp/plan-014-example --no-input use_example_api=yes` | created |
| Dependency tree | `rtk uv tree` | expected presence/absence |

## Scope

**In scope**:
- `{{cookiecutter.project_slug}}/pyproject.toml`
- `hooks/post_gen_project.py`
- root hook tests
- minimal/throttle/example bake assertions in CI or root tests

**Out of scope**:
- Replacing django-ninja-extra in enabled features.
- Removing django-ninja itself.
- Updating its version.

## Git workflow

Do not commit or push unless explicitly requested.

Start from the approved Plan 012 toolchain baseline because this plan changes
the generated pyproject and post-generation hook that carry its synchronized
uv contract.

## Steps

### Step 1: Make the dependency conditional

Render the dependency only when `api_throttling=basic` or
`use_example_api=yes`. Keep dependency ordering stable.

**Verify**: minimal rendered pyproject lacks the dependency; both enabled
feature bakes contain the exact existing pin.

### Step 2: Prune orphan pagination files

When `use_example_api=no`, remove `src/apps/api/pagination.py` and
`tests/api/unit/pagination_test.py`. Add both paths to removal-list existence
tests. Do not remove pagination when the example exists.

**Verify**: post-gen hook succeeds in every relevant combination.

### Step 3: Assert import and dependency closure

Run locked sync, deptry, Ty, pytest, and pre-commit for minimal, throttle-only,
and example bakes. Assert no remaining minimal source imports `ninja_extra` and
`uv tree` contains no package by that name.

**Verify**: all three bakes pass.

## Test plan

Test the four truth-table combinations of example API and throttling for file
presence, dependency presence, settings import, and full suite where code
exists.

## Done criteria

- [ ] Minimal/default bakes contain no ninja-extra package or imports.
- [ ] Throttling and example bakes retain it.
- [ ] Pagination files are pruned only with the example API.
- [ ] All truth-table combinations pass generation checks.

## STOP conditions

- A minimal retained module imports ninja-extra for a non-example feature.
- Conditional dependency rendering makes the generated TOML invalid.
- Deptry identifies a runtime use not found during audit.

## Maintenance notes

Any future unconditional ninja-extra feature must update this predicate and
truth-table tests together.
