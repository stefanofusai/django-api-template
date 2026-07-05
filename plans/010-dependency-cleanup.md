# Plan 010: Dependency and image cleanup (redundant hook, skills-lock check, Docker stages)

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving to the
> next step. If anything in the "STOP conditions" section occurs, stop and
> report — do not improvise. When done, update the status row for this plan
> in `plans/README.md` — unless a reviewer dispatched you and told you they
> maintain the index.
>
> **Drift check (run first)**: `git diff --stat 2485892..HEAD -- '{{cookiecutter.project_slug}}/.pre-commit-config.yaml' '{{cookiecutter.project_slug}}/skills-lock.json' '{{cookiecutter.project_slug}}/.docker/Dockerfile'`
> On any change, compare "Current state" excerpts against the live code; on a
> mismatch, treat it as a STOP condition.

## Status

- **Priority**: P3
- **Effort**: S
- **Risk**: LOW
- **Depends on**: none
- **Category**: dependencies / tech-debt
- **Planned at**: commit `2485892`, 2026-07-05

## Why this matters

Two executable cleanups remain, plus one lockfile sanity check:

1. The `pyupgrade` pre-commit hook duplicates Ruff: the project selects
   `ALL`, which includes Ruff's `UP` (pyupgrade) rules with the same 3.14
   target from `requires-python`. Two tools doing the same rewrites, two
   versions to bump. (`django-upgrade` is NOT redundant — keep it.)
2. `skills-lock.json` previously pinned skills that were not vendored in
   `.agents/skills/`. Current live state already contains only the three
   vendored skills, so the executor must verify it and make no lockfile edit
   unless the drift check reveals a mismatch.
3. The Docker `base` stage installs `curl` + `uuid-runtime` into BOTH builder
   and runtime; `uuidgen` is build-only, `curl` is runtime-only (healthcheck).
   Each image carries a package it never uses.

The original Step 1 (`whitenoise`/`django-storages[s3]` to the prod group) is
superseded by plan 020. Do not move dependencies in this plan.

## Important context: this is a cookiecutter template

- Project code lives under the literal `{{cookiecutter.project_slug}}/` dir —
  quote it in shell. Verification = bake + baked suite + docker build.

## Current state

- `{{cookiecutter.project_slug}}/.pre-commit-config.yaml:40-45`:

  ```yaml
  - repo: https://github.com/asottile/pyupgrade
    rev: v3.21.2
    hooks:
      - id: pyupgrade
        args:
          - --py314-plus
  ```

- `{{cookiecutter.project_slug}}/skills-lock.json` currently has exactly
  `django-celery-expert`, `django-expert`, and `postgres`, matching the
  vendored directories under `{{cookiecutter.project_slug}}/.agents/skills/`.
- `{{cookiecutter.project_slug}}/.docker/Dockerfile:1-7`:

  ```dockerfile
  FROM python:3.14.5-slim AS base

  RUN apt-get update \
      && apt-get install --no-install-recommends --yes \
          curl \
          uuid-runtime \
      && rm -rf /var/lib/apt/lists/*
  ```

  `uuidgen` used at lines 32 and 37 (builder); `curl` used by compose
  healthchecks against the runtime image.

## Commands you will need

| Purpose | Command | Expected on success |
|---------|---------|---------------------|
| Bake | `uvx cookiecutter . --no-input -o $BAKE` | exit 0 |
| Tests | `cd $BAKE/my-project && uv run pytest` | all pass, 100% |
| Hooks | `cd $BAKE/my-project && git add -A && uv run pre-commit run --all-files` | all pass |
| Docker build | `cd $BAKE/my-project && docker build -f .docker/Dockerfile --build-arg UV_DEPENDENCY_GROUP=prod .` | exit 0 |

## Scope

**In scope**:
- `{{cookiecutter.project_slug}}/.pre-commit-config.yaml`
- `{{cookiecutter.project_slug}}/skills-lock.json`
- `{{cookiecutter.project_slug}}/.docker/Dockerfile`

**Out of scope**:
- `requires-python = ">=3.14,<3.15"` — the upper bound was reviewed and left
  as a maintainer policy choice; do not change it.
- Moving `sentry-sdk`/`django-anymail` (Plans 007/009 deliberately keep them
  in main deps because prod.py **imports** them — string-path deps are the
  only movable kind).
- The vendored `.agents/` content itself.

## Git workflow

- Branch: `advisor/010-dependency-cleanup`
- Conventional commit, e.g. `build: drop pyupgrade and split image apt packages`
- Do NOT push or open a PR unless the operator instructed it.

## Steps

### Step 1: Drop the pyupgrade hook

Delete the `asottile/pyupgrade` block from `.pre-commit-config.yaml`. Do NOT
touch `django-upgrade`.

**Verify**: fresh bake → `git add -A && uv run pre-commit run --all-files` →
all pass (ruff-check with UP rules still active — spot-check with
`uv run ruff rule UP006` printing a rule description).

### Step 2: Verify skills-lock.json

Do not edit `skills-lock.json` unless the drift check reveals a mismatch. The
live lockfile should already match the vendored skills.

**Verify**: `python -c "import json; d=json.load(open('{{cookiecutter.project_slug}}/skills-lock.json')); assert sorted(d['skills']) == ['django-celery-expert', 'django-expert', 'postgres']"`
→ exits 0. (Run from the template root with the path quoted.)

### Step 3: Split the Docker apt packages by stage

Restructure the Dockerfile stages: remove the apt install from `base`;
install `uuid-runtime` only in `builder` and `curl` only in `runtime`:

```dockerfile
FROM python:3.14.5-slim AS base

FROM base AS builder

RUN apt-get update \
    && apt-get install --no-install-recommends --yes \
        uuid-runtime \
    && rm -rf /var/lib/apt/lists/*
...
FROM base AS runtime

RUN apt-get update \
    && apt-get install --no-install-recommends --yes \
        curl \
    && rm -rf /var/lib/apt/lists/*
```

(Keep every other line of each stage unchanged and in place; the builder's
apt layer goes where base's install was, i.e. before the uv COPY.)

**Verify**: `docker build -f .docker/Dockerfile --build-arg
UV_DEPENDENCY_GROUP=prod .` in a fresh bake → exit 0. If Docker available,
run the image's healthcheck command manually:
`docker run --rm --entrypoint curl <image> --version` → prints curl version
(curl present in runtime); and confirm `uuidgen` is absent from runtime:
`docker run --rm --entrypoint sh <image> -c "command -v uuidgen"` → exit 1.

### Step 4: Full verification loop

**Verify**: fresh bake → `uv run pytest` → all pass, 100%;
`git add -A && uv run pre-commit run --all-files` → all pass; docker build →
exit 0.

## Test plan

No new pytest tests — this plan changes packaging, not behavior. The
executable verifications are Step 1's hook run, Step 2's JSON assertion, and
Step 3's image probes.

## Done criteria

- [ ] `grep -n pyupgrade '{{cookiecutter.project_slug}}/.pre-commit-config.yaml'` → no matches
- [ ] skills-lock.json has exactly 3 skills matching `.agents/skills/` dirs
- [ ] Dockerfile: `base` has no apt layer; builder has uuid-runtime; runtime has curl
- [ ] Baked project: `uv run pytest` + `pre-commit run --all-files` + prod docker build all pass
- [ ] No files outside the in-scope list modified (`git status`)
- [ ] `plans/README.md` status row updated

## STOP conditions

- The maintainer intended `playwright-best-practices` to be re-vendored
  rather than dropped — if you find any reference to playwright elsewhere in
  the repo (grep first), stop and ask instead of deleting the lock entry.
- Docker build cache behaves unexpectedly after the stage split (e.g. builder
  layer invalidation on every build) — report; do not reorder COPY/RUN lines
  beyond this plan's diff.

## Maintenance notes

- Plan 020 owns dependency-group rationalization, including any future move of
  `whitenoise` or `django-storages[s3]`.
- If a dev-served-media story is ever added (whitenoise in dev), the group
  move must be revisited.
