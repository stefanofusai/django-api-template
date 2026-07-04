# Plan 012: Give the template repo its own checks (root pre-commit, valid Dependabot, cached CI docker build)

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving to the
> next step. If anything in the "STOP conditions" section occurs, stop and
> report — do not improvise. When done, update the status row for this plan
> in `plans/README.md` — unless a reviewer dispatched you and told you they
> maintain the index.
>
> **Drift check (run first)**: `git diff --stat 924bfba..HEAD -- .github/ .gitignore`
> Plus: `test -f .pre-commit-config.yaml && echo EXISTS` at the repo root —
> if it already exists, STOP (someone did this already; reconcile instead).

## Status

- **Priority**: P3
- **Effort**: S–M
- **Risk**: LOW (additive checks; may surface pre-existing nits to fix once)
- **Depends on**: 011 recommended first (its hook edits get linted here)
- **Category**: dx
- **Planned at**: commit `924bfba`, 2026-07-04

## Why this matters

The baked project enforces Ruff/Ty/yamllint/actionlint/markdownlint — but the
template repo itself has **zero** checks on its own files: `hooks/*.py`, the
root `ci.yaml`, `cookiecutter.json`, and the root README are never linted.
Worse, the root `.github/dependabot.yml` declares a `pre-commit`
package-ecosystem at `/` while no root `.pre-commit-config.yaml` exists — an
updater with nothing to update. And the root CI's `docker-build` job runs a
plain `docker build` with no layer cache, re-downloading every wheel on every
PR, while the baked project's own workflow already models the right
buildx+gha-cache setup.

## Important context

This plan touches ONLY template-root files. One subtlety: the
`{{cookiecutter.project_slug}}/` tree contains Jinja placeholders and
GitHub-Actions `${{ }}` sequences that generic hooks would choke on or
"fix" destructively — the root pre-commit config must exclude that entire
subtree. In pre-commit, `exclude` is a Python regex matched against the
relative path; braces must be escaped.

## Current state

- Repo root contains: `.github/` (dependabot.yml + workflows/ci.yaml),
  `.gitignore` (20 bytes), `cookiecutter.json`, `hooks/pre_gen_project.py`,
  `hooks/post_gen_project.py`, `README.md`, `plans/`, and the
  `{{cookiecutter.project_slug}}/` tree. No `.pre-commit-config.yaml`, no
  `pyproject.toml` at the root.
- Root `.github/dependabot.yml` (whole file): two updaters — `github-actions`
  at `/` (valid) and `pre-commit` at `/` (invalid today, valid after Step 1).
- Root `.github/workflows/ci.yaml` `docker-build` job (lines 49-65): plain
  `docker build -f .docker/Dockerfile --build-arg UV_DEPENDENCY_GROUP=prod .`
  run from the baked `/tmp/bake/my-project`, no buildx, no cache.
- The baked project's exemplar
  (`{{cookiecutter.project_slug}}/.github/workflows/docker-build.yaml`):

  ```yaml
      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v4.1.0
      - name: Build Docker image
        uses: docker/build-push-action@v7.2.0
        with:
          context: .
          file: .docker/Dockerfile
          push: false
          cache-from: type=gha
          cache-to: type=gha,mode=max
          build-args: UV_DEPENDENCY_GROUP=prod
  ```

- The baked project's `.pre-commit-config.yaml` is the style reference for
  hook pinning/args (gitlint, pre-commit-hooks, ruff, markdownlint, yamllint,
  yamlfmt, check-jsonschema, actionlint — same repos/revs where applicable).

## Commands you will need

Run from the template repo root.

| Purpose | Command | Expected on success |
|---------|---------|---------------------|
| Root hooks | `uvx pre-commit run --all-files` | all pass |
| Bake regression | `uvx cookiecutter . --no-input -o /tmp/bake-012 && cd /tmp/bake-012/my-project && uv run pytest` | all pass |
| Baked hooks | `cd /tmp/bake-012/my-project && git add -A && uv run pre-commit run --all-files` | all pass |

## Scope

**In scope**:
- `.pre-commit-config.yaml` (create, repo root)
- `.github/workflows/ci.yaml` (add pre-commit job; rework docker-build job)
- `README.md` (root — one line about repo checks, optional)

**Out of scope**:
- `.github/dependabot.yml` — becomes valid by virtue of the new config; no
  edit needed.
- Anything under `{{cookiecutter.project_slug}}/` (including its own
  pre-commit config).
- Adding a root pyproject/ty/pytest infrastructure — Ruff runs standalone on
  the hooks; a root Python project is overkill.

## Git workflow

- Branch: `advisor/012-template-self-checks`
- Conventional commit, e.g. `ci: lint the template repo itself and cache the docker build`
- Do NOT push or open a PR unless the operator instructed it.

## Steps

### Step 1: Root .pre-commit-config.yaml

Create it with this shape (pin `rev`s to the same versions the baked config
uses — read them from
`'{{cookiecutter.project_slug}}/.pre-commit-config.yaml'` at execution time
and copy exactly; update args only where noted):

```yaml
exclude: ^\{\{cookiecutter\.project_slug\}\}/
repos:
  # Generic checks and fixes
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: <same as baked>
    hooks:
      - id: check-added-large-files
      - id: check-ast
      - id: check-case-conflict
      - id: check-json
      - id: check-merge-conflict
      - id: check-yaml
      - id: end-of-file-fixer
      - id: mixed-line-ending
      - id: trailing-whitespace
  # Python (hooks/ only, via the global exclude)
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: <same as baked>
    hooks:
      - id: ruff-check
        args:
          - --fix
      - id: ruff-format
  # Markdown
  - repo: https://github.com/igorshubovych/markdownlint-cli
    rev: <same as baked>
    hooks:
      - id: markdownlint
        args:
          - --disable=MD013
          - --
  # YAML
  - repo: https://github.com/adrienverge/yamllint
    rev: <same as baked>
    hooks:
      - id: yamllint
        args: <same -d config as baked>
  # GitHub Actions / JSON schema
  - repo: https://github.com/python-jsonschema/check-jsonschema
    rev: <same as baked>
    hooks:
      - id: check-dependabot
      - id: check-github-workflows
  - repo: https://github.com/rhysd/actionlint
    rev: <same as baked>
    hooks:
      - id: actionlint
```

Notes: no gitlint (root commit style is the maintainer's call, and Dependabot
PRs would trip it), no ty/uv hooks (no root Python project), `check-ast`
validates hook files parse. The `exclude` regex keeps every generic hook away
from the Jinja tree. `plans/` will get markdownlint'd — if it fails on the
plan files, add `^plans/` to the exclude rather than editing plans.

**Verify**: `uvx pre-commit run --all-files` → all hooks pass (fix any
surfaced nits in root files as part of this step — expect minor whitespace/
markdownlint findings at most; if Ruff demands substantive hook changes,
STOP condition below).

### Step 2: Run it in CI

Add a `pre-commit` job to the root `ci.yaml` (alphabetical job order — it
lands between `bake`/`bake-invalid` and `docker-build`):

```yaml
  pre-commit:
    name: Pre-commit
    runs-on: ubuntu-latest
    steps:
      - name: Checkout repository
        uses: actions/checkout@v6.0.3
      - name: Set up Python
        uses: actions/setup-python@v6.2.0
        with:
          python-version: "3.14"
      - name: Set up uv
        uses: astral-sh/setup-uv@v8.2.0
      - name: Run pre-commit
        run: uvx pre-commit run --all-files
```

**Verify**: `uvx pre-commit run --all-files` locally (same command CI runs)
→ passes.

### Step 3: Cache the CI docker build

Rework the root `ci.yaml` `docker-build` job to mirror the baked exemplar:
after the bake step, add `docker/setup-buildx-action@v4.1.0`, then replace the
plain `docker build` with `docker/build-push-action@v7.2.0` using
`context: /tmp/bake/my-project`, `file: /tmp/bake/my-project/.docker/Dockerfile`,
`push: false`, `cache-from: type=gha`, `cache-to: type=gha,mode=max`,
`build-args: UV_DEPENDENCY_GROUP=prod`. Keep the existing checkout/python/uv/
bake steps unchanged.

**Verify**: `uvx pre-commit run actionlint --all-files` → passes (validates
the workflow syntax); full validation happens on the first CI push.

### Step 4: Full verification loop

**Verify**: root `uvx pre-commit run --all-files` → all pass; fresh bake →
baked `uv run pytest` + baked `pre-commit run --all-files` → all pass
(proves the root config didn't leak into the template tree).

## Test plan

The checks ARE the deliverable; their test is running them (Step 1/2/4) plus
one deliberate failure probe: introduce a trailing space in `README.md`, run
`uvx pre-commit run trailing-whitespace --all-files` → hook fails/fixes it;
revert.

## Done criteria

- [ ] `.pre-commit-config.yaml` exists at root with the Jinja-tree exclude
- [ ] `uvx pre-commit run --all-files` at root → all pass
- [ ] Root `ci.yaml` has the pre-commit job and the buildx-cached docker-build job
- [ ] Root dependabot's `pre-commit` updater now has a config to update (no dependabot.yml edit)
- [ ] Fresh bake: baked pytest + baked pre-commit still pass
- [ ] No files outside the in-scope list modified (`git status` — note hooks may auto-fix root files; that's in scope)
- [ ] `plans/README.md` status row updated

## STOP conditions

- Ruff (root config) demands non-trivial rewrites of `hooks/*.py` beyond
  formatting/import-order — the hooks' logic belongs to Plan 011; report the
  findings instead of refactoring here.
- Any root hook modifies a file under `{{cookiecutter.project_slug}}/`
  despite the exclude — the regex is wrong; fix the exclude, never commit a
  template-tree change from this plan.
- actionlint flags pre-existing errors in `ci.yaml` unrelated to this plan's
  jobs — report them (they're free findings), fix only if one-line.

## Maintenance notes

- Dependabot now bumps the root hooks weekly (the previously-orphaned
  updater); expect grouped PRs.
- When the baked project's pre-commit revs move (via its own Dependabot), the
  root config drifts behind — acceptable, but a quarterly manual sync keeps
  the two aligned; a future improvement could generate one from the other.
