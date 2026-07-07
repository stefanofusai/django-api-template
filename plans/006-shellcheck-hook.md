# Plan 006: Add shellcheck to the baked and root pre-commit stacks

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving on. If
> anything in "STOP conditions" occurs, stop and report — do not improvise.
> When done, update this plan's status row in `plans/README.md` — unless a
> reviewer dispatched you and told you they maintain the index.
>
> **Drift check (run first)**:
> `git diff --stat ae42991..HEAD -- "{{cookiecutter.project_slug}}/.pre-commit-config.yaml" .pre-commit-config.yaml "{{cookiecutter.project_slug}}/README.md" README.md`
> On a mismatch with "Current state", STOP. (Plans 001, 002, 004 touch
> neighboring files — reconcile if they landed first.)

## Status

- **Priority**: P2
- **Effort**: S
- **Risk**: LOW (a new lint gate can only fail loudly; existing scripts must pass first)
- **Depends on**: none (pairs naturally with 001/002 — their scripts get a permanent gate)
- **Category**: dx
- **Planned at**: commit `ae42991`, 2026-07-07

## Repository context (read before anything else)

This is a **Cookiecutter template**; source under
`{{cookiecutter.project_slug}}/` (**quote in shell**). Two pre-commit configs
exist: the **baked** `{{cookiecutter.project_slug}}/.pre-commit-config.yaml`
(rendered; runs in generated projects and in every root-CI `bake` job) and the
**repo-root** `.pre-commit-config.yaml` (lints the template's own tracked
files; `exclude`s `{{cookiecutter.project_slug}}/`, `hooks/`, `plans/`).
Verification means baking and running both stacks.

## Why this matters

The template ships **six** `/bin/sh` scripts in the generated project
(`.docker/scripts/`: celery-beat, celery-worker, dev, gunicorn, migrations,
postgres-backup — plus `.github/scripts/deploy-check.sh` and
`migrations-check.sh`), several of which are operational (entrypoints, cron
backup). Yet **no shell linter runs anywhere**: the otherwise-exhaustive
pre-commit stack (ruff, ty, yamllint, actionlint, markdownlint, uv-audit, …)
has no shellcheck. Plans 001 and 002 both had to hand-run shellcheck because
no gate exists. One hook closes the gap permanently, consistent with the
template's "the toolchain catches mistakes before humans do" philosophy.

## Current state

`{{cookiecutter.project_slug}}/.pre-commit-config.yaml` — sections in order:
`# Git`, `# Generic checks and fixes`, `# Python`, `# Markdown`, `# YAML`,
`# GitHub Actions / JSON schema`, `# Dependency management`. No `# Shell`
section, no shellcheck repo (grep `shellcheck` → nothing). Same for the
repo-root config (whose `exclude: ^(\{\{cookiecutter\.project_slug\}\}/|hooks/|plans/)`
means it lints no shell today anyway — but future root-level scripts, e.g.
plan 010's `scripts/`, would be covered).

The generated `.github/dependabot.yaml` updates all pre-commit hooks as one
grouped ecosystem (`patterns: ["*"]`) — a new hook repo is auto-bumped, no
dependabot change needed. Root dependabot: confirm it has the same
`pre-commit` ecosystem (read `.github/dependabot.yaml` at the repo root).

**Hook choice**: use `shellcheck-py` (https://github.com/shellcheck-py/shellcheck-py),
hook id `shellcheck` — it is pip-installable, so it works in this uv/pre-commit
toolchain **without requiring a system shellcheck or Docker** (the alternative,
`koalaman/shellcheck-precommit`, needs Docker). Pin `rev` to the latest
release tag (check the repo's releases; if no web access, use the newest tag
`pre-commit autoupdate` resolves and note it).

**Conventions**: alphabetized hook ids within a repo block; sections
comment-headed; extended YAML block style; pin exact versions.

## Commands you will need

| Purpose | Command | Expected |
|---------|---------|----------|
| Bake default | `uvx cookiecutter . --no-input -o /tmp/bake` | project |
| Baked shellcheck only | `cd /tmp/bake/my-project && git add -A && uv run pre-commit run shellcheck --all-files` | `Passed` |
| Full baked pre-commit | `cd /tmp/bake/my-project && git add -A && uv run pre-commit run --all-files` | exit 0 |
| Root pre-commit | (repo root) `uvx pre-commit run --all-files` | exit 0 |
| Bake minimal | `uvx cookiecutter . --no-input -o /tmp/bake-min use_celery=none email_provider=none use_sentry=no use_s3_media=no use_traefik=no` | fewer scripts; hook still passes |

## Scope

**In scope**:
- `{{cookiecutter.project_slug}}/.pre-commit-config.yaml` — add a `# Shell`
  section with the shellcheck hook (place the section alphabetically among the
  existing comment sections: after `# Python`, before `# YAML`? — the existing
  order is Git, Generic, Python, Markdown, YAML, GitHub Actions, Dependency
  management, which is NOT alphabetical; match the spirit by inserting
  `# Shell` between `# Markdown` and `# YAML`).
- `.pre-commit-config.yaml` (repo root) — same hook, same placement logic.
- `README.md` (repo root) — add `shellcheck` to the line-16 tool inventory
  (alphabetical, after `Ruff`... confirm against the actual list; if plan 004
  landed, `gitleaks` is already in that list).

**Out of scope**:
- Fixing any shellcheck findings in existing scripts beyond what the hook
  requires to pass (if a script needs a *behavioral* change to satisfy
  shellcheck, STOP — that belongs in its own plan).
- `.agents/` (already excluded by the baked config's top-level `exclude`).
- Dependabot configs (grouped `*` pattern covers the new repo).

## Git workflow

- Work directly on `main`. Do NOT branch/commit/push/PR unless told. If asked
  to commit: Conventional Commits, e.g. `ci: add shellcheck pre-commit hook`.

## Steps

### Step 1: Add the hook to the baked config

In `{{cookiecutter.project_slug}}/.pre-commit-config.yaml`, insert between the
`# Markdown` and `# YAML` sections:

```yaml
  # Shell
  - repo: https://github.com/shellcheck-py/shellcheck-py
    rev: <latest vX.Y.Z.N tag>
    hooks:
      - id: shellcheck
```

### Step 2: Bake and run — fix or report findings

```
uvx cookiecutter . --no-input -o /tmp/bake
cd /tmp/bake/my-project && git add -A && uv run pre-commit run shellcheck --all-files
```

**Expected**: `Passed` — the eight scripts are simple `set -eu` POSIX sh and
should be clean. If shellcheck reports findings: style-level fixes (quoting a
variable, `$(...)` over backticks) are in scope — apply them in the template
source and re-bake; anything requiring behavioral change is a STOP.

Then the full baked run and the minimal bake (Commands table) — all exit 0.

### Step 3: Add the hook to the root config

Same block in the repo-root `.pre-commit-config.yaml` (same placement logic).
Today the root exclude means it lints nothing (no tracked shell outside the
excluded dirs) — it exists so future root-level scripts are covered from day
one.

**Verify**: `uvx pre-commit run --all-files` (repo root) exits 0.

### Step 4: Update the root README tool inventory

Insert `shellcheck` alphabetically into the pre-commit tool list at repo-root
`README.md:16`.

**Verify**: `grep -c shellcheck README.md` ≥ 1 (repo root); root markdownlint
passes.

## Test plan

- The gate is self-testing: Step 2's run over the eight existing scripts is
  the test. Additionally inject a deliberate fault in a bake copy (e.g. an
  unquoted `$BACKUP_DIR` in postgres-backup.sh inside `/tmp/bake`) and confirm
  the hook FAILS, then discard the bake — proving the hook actually inspects
  the scripts rather than matching zero files.

## Done criteria

ALL must hold:

- [ ] Both pre-commit configs have the shellcheck-py hook with an exact pinned `rev`.
- [ ] Default AND minimal bakes: `uv run pre-commit run shellcheck --all-files` → `Passed`; full baked runs exit 0.
- [ ] The injected-fault check failed (hook demonstrably inspects the scripts), then was discarded.
- [ ] Root `uvx pre-commit run --all-files` exits 0; root README inventory updated.
- [ ] No behavioral change to any script (`git diff` on `.docker/scripts/` and `.github/scripts/` shows only quoting/style fixes, if any).
- [ ] `plans/README.md` status row updated.

## STOP conditions

Stop and report (do not improvise) if:

- shellcheck findings on an existing script require a behavioral change (own
  plan; do not fix here).
- The shellcheck-py hook cannot install in the baked environment (record the
  error; the Docker-based `koalaman/shellcheck-precommit` is the fallback to
  *propose*, not to silently adopt — it changes the toolchain's no-Docker
  assumption for pre-commit).
- Hook matches zero files in the baked project (types filter mismatch —
  investigate before claiming success).

## Maintenance notes

- shellcheck-py is auto-bumped by the grouped `pre-commit` Dependabot
  ecosystem in generated projects; confirm the root dependabot has the same
  group (it should — note in your report if not).
- Plans 001/002's hand-run `uvx --from shellcheck-py shellcheck` verifications
  become redundant once this lands — the hook covers them; no need to edit
  those plans.
- If a future script legitimately needs a `# shellcheck disable=SCxxxx`, keep
  it line-scoped with a justification comment — there is deliberately no
  precedent for blanket disables.
