# Plan 004: Add a gitleaks secret scanner to the baked project's pre-commit stack

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving to the
> next step. If anything in the "STOP conditions" section occurs, stop and
> report — do not improvise. When done, update the status row for this plan
> in `plans/README.md` — unless a reviewer dispatched you and told you they
> maintain the index.
>
> **Drift check (run first)**:
> `git diff --stat ae42991..HEAD -- "{{cookiecutter.project_slug}}/.pre-commit-config.yaml" README.md`
> If any in-scope file changed since this plan was written, compare the
> "Current state" excerpts against the live code before proceeding; on a
> mismatch, treat it as a STOP condition.

## Status

- **Priority**: P2
- **Effort**: S
- **Risk**: LOW
- **Depends on**: none
- **Category**: security
- **Planned at**: commit `ae42991`, 2026-07-07 (re-verified against live code same day)

## Repository context (read before anything else)

This repository is a **Cookiecutter template**, not a runnable Django project.
The project source lives under the literal directory
`{{cookiecutter.project_slug}}/` — the braces are part of the real path, so
**always quote it in shell** (`cd "{{cookiecutter.project_slug}}"`). Files
inside it contain Jinja placeholders (`{{ cookiecutter.* }}`,
`{%- if ... %}`) that must stay syntactically valid.

- `.pre-commit-config.yaml` lives at `{{cookiecutter.project_slug}}/.pre-commit-config.yaml`
  and **is rendered** by cookiecutter — Jinja is allowed there.
- **`.github/workflows/*` and `.agents/*` are copied WITHOUT rendering**
  (`_copy_without_render` in `cookiecutter.json`). Never put Jinja in those.
  This plan does not touch them.
- **Verification always means baking a project and running its checks.** Bake
  with: `uvx cookiecutter . --no-input -o /tmp/bake` (produces
  `/tmp/bake/my-project/`). There is also a repo-root `.pre-commit-config.yaml`
  for the template itself; this plan does **not** modify it (see Scope).

## Why this matters

The baked project ships an unusually complete pre-commit stack (actionlint,
gitlint, markdownlint, ruff, ty, uv-audit, yamllint, yamlfmt, check-github-
workflows, and more) and invests heavily in `.env` hygiene (the `.env.example`
"empty = required in prod" contract, boot guards). Yet the only secret-related
hook is `detect-private-key`, which catches PEM private keys and nothing else.
A committed cloud/API token (AWS, Resend, Sentry DSN with a real key, database
URL with a password) would sail through CI. Adding `gitleaks` — a broad,
baseline-free secret scanner — closes that gap and is consistent with the
template's "the toolchain catches mistakes before humans do" philosophy.

## Current state

`{{cookiecutter.project_slug}}/.pre-commit-config.yaml` is organized into
comment-headed sections (`# Git`, `# Generic checks and fixes`, `# Python`,
`# Markdown`, `# YAML`, `# GitHub Actions / JSON schema`,
`# Dependency management`). The top of the file and the `# Git` section:

```yaml
default_install_hook_types:
  - commit-msg
  - pre-commit
default_language_version:
  python: python3.14
exclude: ^\.agents/
repos:
  # Git
  - repo: https://github.com/jorisroovers/gitlint
    rev: v0.19.1
    hooks:
      - id: gitlint
        args:
          - --contrib=contrib-title-conventional-commits
          - --ignore=B6
          - --msg-filename
  # Generic checks and fixes
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v6.0.0
    hooks:
      - id: check-added-large-files
      ...
      - id: detect-private-key
      ...
```

The baked project's `.github/dependabot.yaml` already updates all pre-commit
hooks as one group (`package-ecosystem: pre-commit`, `patterns: ["*"]`), so a
newly added gitleaks repo is auto-updated with **no dependabot change needed**.

**Conventions that apply (from `AGENTS.md`)**:
- "Order unordered list items alphabetically ... This includes ... YAML lists
  of pre-commit hook ids." Within a repo block, hook ids are alphabetized.
- "Pin dependencies ... use the latest intended release when adding." Pin the
  gitleaks `rev` to a real, latest release tag (not a moving ref).
- The repo uses extended YAML block style (`- main`, not `[main]`).
- `.agents/` stays excluded (already handled by the top-level `exclude:`).

There is a known false-positive risk: the baked `.env.example` contains
`SECRET_KEY=django-insecure-change-me-in-production` (a Django placeholder, not
a real secret) and other empty required keys. gitleaks' default ruleset is
entropy- and pattern-based and generally ignores obvious placeholders, but this
must be verified on a real bake (Step 3) and allowlisted if it fires (Step 4).

## Commands you will need

| Purpose | Command | Expected on success |
|---------|---------|---------------------|
| Bake a project | `uvx cookiecutter . --no-input -o /tmp/bake` | creates `/tmp/bake/my-project/` |
| Baked pre-commit (all) | `cd /tmp/bake/my-project && git add -A && uv run pre-commit run --all-files` | exit 0, gitleaks `Passed` |
| Run just gitleaks | `cd /tmp/bake/my-project && uv run pre-commit run gitleaks --all-files` | `Passed` |
| Root pre-commit (regression) | (repo root) `uvx pre-commit run --all-files` | exit 0 |

Note: baking runs `uv lock` in the post-gen hook; that needs network + `uv`
installed. If the bake output warns that `uv.lock` was not generated, the
environment lacks `uv` on PATH — that is a STOP condition (you cannot verify).

## Scope

**In scope** (the only files you should modify):
- `{{cookiecutter.project_slug}}/.pre-commit-config.yaml` — add the gitleaks repo block.
- `{{cookiecutter.project_slug}}/.gitleaks.toml` — **create only if** Step 3
  surfaces false positives (see Step 4). Otherwise do not create it.
- `README.md` (**repo root** — the template's own README, a normal editable
  file) — add `gitleaks` to the one-line inventory of pre-commit tools at
  `README.md:16` (the line beginning "actionlint, gitlint, markdownlint,
  Ruff, Ty, uv-audit, yamlfmt, yamllint, and other pre-commit checks"). Keep
  the existing alphabetical order of that comma-separated list. NOTE: the
  *generated* project's README (`{{cookiecutter.project_slug}}/README.md`) has
  no such inventory line — do not hunt for one there.

**Out of scope** (do NOT touch, even though they look related):
- The repo-root `.pre-commit-config.yaml` (the template's own hooks). Adding
  gitleaks there risks flagging the template's intentional fake credentials
  (`$(uuidgen)` DSNs in CI scripts, the `.env.example` placeholder). If the
  maintainer wants it there too, that is a separate follow-up — note it in
  Maintenance notes, do not do it here.
- `.github/dependabot.yaml` — no change needed (grouped `*` pattern covers it).
- Any `.github/workflows/*` file — the generated ones are copied without
  rendering, and the **repo-root** `.github/workflows/ci.yaml` (the template's
  own CI) already runs the baked pre-commit inside its `bake` job, so the new
  hook is exercised on every push with no workflow change.

## Git workflow

- Work directly on `main`. Do NOT create a branch, commit, push, or open a PR
  unless the operator explicitly instructs it.
- If asked to commit, match the repo's Conventional Commits style (see
  `git log --oneline`), e.g. `ci: add gitleaks secret scanner to pre-commit`.

## Steps

### Step 1: Determine the latest gitleaks pre-commit release tag

The gitleaks pre-commit hook lives at `https://github.com/gitleaks/gitleaks`
(hook id `gitleaks`). Find the latest release tag (form `v8.x.y`). If you have
web access, read `https://github.com/gitleaks/gitleaks/releases`. If you do
not, use `v8.30.0` as a known-good recent tag and note in your report that the
executor could not confirm it was the latest.

Record the exact tag you will use; it goes in the `rev:` field in Step 2.

### Step 2: Add the gitleaks repo block to the baked pre-commit config

In `{{cookiecutter.project_slug}}/.pre-commit-config.yaml`, add a new repo
block under the `# Git` section, **immediately BEFORE the existing `gitlint`
block** (directly under the `# Git` comment). Use the tag from Step 1 —
`v8.30.0` below is a placeholder, replace it with the Step 1 tag:

```yaml
  - repo: https://github.com/gitleaks/gitleaks
    rev: v8.30.0
    hooks:
      - id: gitleaks
```

Placement rationale: gitleaks is a git/secret-oriented hook, so it belongs in
the `# Git` section, and `gitleaks` < `gitlint` alphabetically (they share
`gitl`, then `e` < `i`), so the gitleaks block goes first. (The file does not
alphabetize repo blocks perfectly in every section, but AGENTS.md's
alphabetization rule is the tiebreaker here.)

**Verify**: this step has no standalone check — the bake in Step 3 is the
verification (a malformed YAML or unresolvable hook fails there). Confirm only
that you did not touch any `{%- ... %}` Jinja block elsewhere in the file.

### Step 3: Bake and run the full baked pre-commit suite

```
uvx cookiecutter . --no-input -o /tmp/bake
cd /tmp/bake/my-project
git add -A
uv run pre-commit run --all-files
```

**Verify**: exit 0, and the output shows `gitleaks....Passed`.

- If gitleaks reports **findings in `.env.example`, the fake CI credential
  scripts, or other intentional placeholders**, proceed to Step 4.
- If gitleaks reports findings that look like **real** secrets anywhere in the
  template, that is a genuine security issue — STOP and report it (reference
  file:line and credential type only; do not paste the value).
- If it passes cleanly, skip Step 4 and go to Step 5.

### Step 4: (Only if Step 3 flagged placeholders) add a minimal allowlist

Create `{{cookiecutter.project_slug}}/.gitleaks.toml` extending the default
config and allowlisting only the specific intentional-placeholder paths that
fired. Keep the allowlist as narrow as possible (path-scoped, not global):

```toml
[extend]
useDefault = true

[[allowlists]]
description = "Template placeholders and documented example credentials"
paths = [
    '''\.env\.example$''',
]
```

Add only the paths that actually fired in Step 3. Re-run Step 3's command and
confirm `gitleaks....Passed` with the allowlist in place. Do NOT broaden the
allowlist to silence a finding you have not confirmed is a placeholder.

### Step 5: Update the README inventory line

In the **repo-root** `README.md` (the template's own README), find the bullet
at line 16 that lists the pre-commit tools (begins "actionlint, gitlint,
markdownlint, Ruff, Ty, uv-audit, yamlfmt, yamllint, and other pre-commit
checks"). Insert `gitleaks` in its correct alphabetical position (between
`actionlint` and `gitlint`).

**Verify**: `grep -n "gitleaks" README.md` → one match in the inventory line
(run from the repo root).

### Step 6: Regression-check the template's own root pre-commit

From the **repo root** (not the baked project):

```
uvx pre-commit run --all-files
```

**Verify**: exit 0. (This confirms you did not accidentally break the root
config or leave the baked file malformed in a way markdownlint/yamllint catch
when the template repo lints its own tracked files.)

## Test plan

There is no unit test for pre-commit config; verification is the baked
pre-commit run itself (Steps 3 and 6). Additionally bake the **minimal**
variant to confirm the new hook renders and passes with all knobs off:

```
uvx cookiecutter . --no-input -o /tmp/bake-min \
  use_celery=none email_provider=none use_sentry=no use_s3_media=no use_traefik=no
cd /tmp/bake-min/my-project && git add -A && uv run pre-commit run gitleaks --all-files
```

**Verify**: `gitleaks....Passed`.

## Done criteria

Machine-checkable. ALL must hold:

- [ ] `grep -n "gitleaks/gitleaks" "{{cookiecutter.project_slug}}/.pre-commit-config.yaml"` returns one match with a pinned `vX.Y.Z` rev on the next line.
- [ ] A fresh default bake's `git add -A && uv run pre-commit run --all-files` exits 0 with `gitleaks....Passed`.
- [ ] A fresh minimal bake's gitleaks hook passes.
- [ ] Root `uvx pre-commit run --all-files` exits 0.
- [ ] Repo-root `README.md:16` inventory line includes `gitleaks` (`grep -c gitleaks README.md` ≥ 1 from the repo root).
- [ ] No files outside the in-scope list are modified (`git status`).
- [ ] `plans/README.md` status row updated.

## STOP conditions

Stop and report back (do not improvise) if:

- The "Current state" excerpt of `.pre-commit-config.yaml` no longer matches
  the live file (drift since ae42991).
- gitleaks reports what appears to be a **real** secret in the template.
- `uv`/`uvx` is unavailable or a bake fails to produce `uv.lock` — you cannot
  verify without it.
- Silencing false positives would require a broad/global allowlist rather than
  a small set of path rules — the placeholder set may be larger than expected.

## Maintenance notes

- gitleaks is auto-updated via the grouped `pre-commit` Dependabot ecosystem;
  no manual bump cadence needed.
- If future work adds real example credentials or fixtures, extend
  `.gitleaks.toml` (path-scoped) rather than disabling the hook.
- **Deferred follow-up**: consider adding gitleaks to the repo-root
  `.pre-commit-config.yaml` (the template's own hooks). It was left out here
  because the template intentionally contains fake credentials
  (`$(uuidgen)`-generated DSNs in `.github/scripts/*` and the `.env.example`
  placeholder) that would need allowlisting; decide separately.
- Reviewer should confirm the allowlist (if any) is path-scoped and minimal,
  and that no Jinja was introduced into `.github/workflows/*` or `.agents/*`.
