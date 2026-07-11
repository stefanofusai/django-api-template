# Plan 017: Automate updates for pins inside the Jinja template

> **Executor instructions**: This plan adds update discovery, not automatic
> merging. Run all config validation and update the index.
>
> **Drift check (run first)**: `rtk git diff --stat b367191..HEAD -- '.github/' 'pyproject.toml' 'uv.lock' '{{cookiecutter.project_slug}}/pyproject.toml' '{{cookiecutter.project_slug}}/.docker/' '{{cookiecutter.project_slug}}/.pre-commit-config.yaml' 'README.md'`

## Status

- **Priority**: P2
- **Effort**: M
- **Risk**: LOW
- **Depends on**: plan 012
- **Category**: dependencies
- **Planned at**: commit `b367191`, 2026-07-10

## Why this matters

Generated repositories receive Dependabot uv updates after baking, but the
template repository cannot parse Jinja-wrapped Python dependency lines through
Dependabot's uv ecosystem. New Django, psycopg, Celery, and security releases
therefore reach future bakes only through manual maintainer discovery.

## Current state

- Root Dependabot tracks GitHub Actions and pre-commit only.
- Generated Dependabot tracks uv, but that does not update the source template.
- Direct generated dependencies use strict `name==version` strings, including
  Jinja-conditional entries and extras.
- Plan 012 establishes a locked root toolchain; do not duplicate its pins.

## Commands you will need

| Purpose | Command | Expected |
|---|---|---|
| JSON/config lint | `rtk uv run --locked pre-commit run --all-files` | exit 0 |
| Renovate dry run | `renovate --dry-run=full <repo>` | dependency matches listed, no write |
| Bake checks | `rtk uv run --locked cookiecutter . -o /tmp/plan-017 --no-input` | created |

## Scope

**In scope**:
- Renovate configuration under `.github/` or repository root (create)
- root onboarding documentation
- validation tests for dependency-match coverage
- Dependabot configuration only to avoid duplicate ownership

**Out of scope**:
- Auto-merge.
- Major-version upgrades without review.
- Publishing credentials or tokens in the repository.

## Git workflow

Do not commit or push unless explicitly requested. Installing/enabling a
GitHub App requires maintainer action outside the repository.

## Steps

### Step 1: Create a complete pin inventory test

Add a root test that extracts exact direct pins from the generated
`pyproject.toml`, Dockerfile/Compose images, pre-commit revisions, and pinned
downloaded tools. Store no copied version list; the test should assert each
source line is matched by an update manager or an explicit documented ignore.

**Verify**: the test fails before update-manager configuration exists.

### Step 2: Configure Renovate custom managers

Use Renovate because Dependabot cannot update Jinja TOML. Add a PyPI regex
manager matching quoted `package[extras]==version` dependencies in the literal
template path, preserving extras while using the base package as `depName` and
PEP 440 versioning. Use built-in Docker, Compose, Actions, and pre-commit
managers where they already work; avoid duplicate PRs with Dependabot by
assigning each ecosystem to one owner.

Group Python minor/patch updates similarly to generated Dependabot and leave
major framework/runtime updates separate.

**Verify**: dry-run output lists every direct template dependency once, with
correct datasource and current value.

### Step 3: Add guarded post-update verification

Configure Renovate PRs to rely on existing root CI: render representative
bakes, regenerate locks, run tests/pre-commit, and build production images.
Do not let Renovate edit generated `uv.lock` in the source template because it
does not exist there.

**Verify**: a test branch changing one harmless patch pin produces one PR and
green representative checks.

### Step 4: Document activation and ownership

Document the required GitHub App/repository setting, update cadence, grouping,
and the rule that dependency PRs are never auto-merged. Explain which updates
remain manual and why.

**Verify**: markdownlint and config validation pass.

## Test plan

Test regex matching for plain packages, extras, Jinja-adjacent lines, duplicate
conditional variants, prereleases, and nondependency `==` text that must not
match.

## Done criteria

- [ ] Every maintained pin has exactly one automated freshness owner.
- [ ] Jinja Python dependencies appear in Renovate dry-run output.
- [ ] No update is auto-merged.
- [ ] Representative dependency PR passes template CI.

## STOP conditions

- Repository policy does not allow the Renovate App or an equivalent
  least-privilege runner.
- Regex manager rewrites Jinja syntax or extras.
- Renovate and Dependabot would open duplicate PRs for an ecosystem.

## Maintenance notes

The pin inventory test is the durable control. Any newly pinned artifact must
declare its update owner in the same change.
