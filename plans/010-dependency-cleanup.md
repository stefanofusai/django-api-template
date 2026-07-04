# Plan 010: Dependency and image cleanup (prod-only deps, redundant hook, skills-lock drift, Docker stages)

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving to the
> next step. If anything in the "STOP conditions" section occurs, stop and
> report — do not improvise. When done, update the status row for this plan
> in `plans/README.md` — unless a reviewer dispatched you and told you they
> maintain the index.
>
> **Drift check (run first)**: `git diff --stat 924bfba..HEAD -- '{{cookiecutter.project_slug}}/pyproject.toml' '{{cookiecutter.project_slug}}/.pre-commit-config.yaml' '{{cookiecutter.project_slug}}/skills-lock.json' '{{cookiecutter.project_slug}}/.docker/Dockerfile'`
> On any change, compare "Current state" excerpts against the live code; on a
> mismatch, treat it as a STOP condition. (Plans 007/009 add dependencies to
> pyproject.toml — expect those lines.)

## Status

- **Priority**: P3
- **Effort**: S
- **Risk**: LOW–MED (the group move changes what installs where; each move has an explicit check)
- **Depends on**: none (run after 007/009 to avoid pyproject merge friction)
- **Category**: dependencies / tech-debt
- **Planned at**: commit `924bfba`, 2026-07-04

## Why this matters

Four independent cleanups, each small:

1. `whitenoise` and `django-storages[s3]` sit in `[project].dependencies` but
   are referenced **only by prod settings, only as strings** (middleware path,
   storage backend paths) — never imported in dev/ci. `boto3` (via
   django-storages' s3 extra) is a large tree installed on every dev machine
   and CI run for nothing.
2. The `pyupgrade` pre-commit hook duplicates Ruff: the project selects
   `ALL`, which includes Ruff's `UP` (pyupgrade) rules with the same 3.14
   target from `requires-python`. Two tools doing the same rewrites, two
   versions to bump. (`django-upgrade` is NOT redundant — keep it.)
3. `skills-lock.json` pins a `playwright-best-practices` skill that is not
   vendored in `.agents/skills/` (verified: only django-celery-expert,
   django-expert, mcp-builder, postgres exist) — lockfile drift.
4. The Docker `base` stage installs `curl` + `uuid-runtime` into BOTH builder
   and runtime; `uuidgen` is build-only, `curl` is runtime-only (healthcheck).
   Each image carries a package it never uses.

## Important context: this is a cookiecutter template

- Project code lives under the literal `{{cookiecutter.project_slug}}/` dir —
  quote it in shell. Verification = bake + baked suite + docker build.

## Current state

- `{{cookiecutter.project_slug}}/pyproject.toml`:
  - `[project].dependencies` contains `"django-storages[s3]==1.14.6",` and
    `"whitenoise==6.12.0",`.
  - `[dependency-groups].prod` is currently
    `["django-stubs-ext==6.0.5", "gunicorn==26.0.0"]`.
- Their only references are string paths in
  `src/config/settings/environments/prod.py` (lines 9, 20, 35): the
  WhiteNoise middleware path, `storages.backends.s3.S3Storage`, and
  `whitenoise.storage.CompressedManifestStaticFilesStorage`. There are no
  `import whitenoise` / `import storages` statements anywhere
  (`grep -rn "import whitenoise\|import storages" '{{cookiecutter.project_slug}}/src'`
  → no matches).
- Contexts that load prod settings and what they need:
  - Docker prod build (`--build-arg UV_DEPENDENCY_GROUP=prod`) runs
    `collectstatic`, which **instantiates** the whitenoise staticfiles
    storage → whitenoise must be in the prod group. ✔ after the move.
  - CI deploy check (`tests.yaml`): `uv run --group=ci ... manage.py check
    --deploy --fail-level=WARNING --tag=security` — security-tag checks read
    settings values; they do not import middleware/storage classes. Expected
    to pass without whitenoise/storages installed — **Step 1 verifies this
    explicitly**.
- `{{cookiecutter.project_slug}}/.pre-commit-config.yaml:40-45`:

  ```yaml
  - repo: https://github.com/asottile/pyupgrade
    rev: v3.21.2
    hooks:
      - id: pyupgrade
        args:
          - --py314-plus
  ```

- `{{cookiecutter.project_slug}}/skills-lock.json:22-27` — the
  `playwright-best-practices` entry (source
  `currents-dev/playwright-best-practices-skill`).
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
| Deploy-check parity (inside bake) | Step 1 command | exit 0 |
| Docker build | `cd $BAKE/my-project && docker build -f .docker/Dockerfile --build-arg UV_DEPENDENCY_GROUP=prod .` | exit 0 |

## Scope

**In scope**:
- `{{cookiecutter.project_slug}}/pyproject.toml`
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
- Conventional commit, e.g. `build: move prod-only deps, drop pyupgrade, fix skills lock and image stages`
- Do NOT push or open a PR unless the operator instructed it.

## Steps

### Step 1: Move whitenoise + django-storages to the prod group

In `pyproject.toml`: remove both lines from `[project].dependencies`; add to
`[dependency-groups].prod` keeping it alphabetized:

```toml
prod = [
    "django-storages[s3]==1.14.6",
    "django-stubs-ext==6.0.5",
    "gunicorn==26.0.0",
    "whitenoise==6.12.0",
]
```

**Verify** (all inside a fresh bake):
1. `uv run pytest` → all pass (ci/dev never touch these).
2. Deploy-check parity — replicate the CI step exactly:

   ```
   env DJANGO_ENV=prod ALLOWED_HOSTS=example.com AWS_STORAGE_BUCKET_NAME=ci \
     CACHE_URL=locmemcache:// CSRF_TRUSTED_ORIGINS=https://example.com \
     DATABASE_URL=sqlite:///:memory: \
     SECRET_KEY=ci-secret-for-deploy-checks-0123456789-abcdefghijklmnopqrstuvwxyz \
     uv run --group=ci --locked --no-default-groups \
     python manage.py check --deploy --fail-level=WARNING --tag=security
   ```

   (Add `SENTRY_DSN`/`RESEND_API_KEY` dummies if Plans 007/009 landed.)
   → exit 0. **If this fails with a ModuleNotFoundError for whitenoise or
   storages, the audit's string-only analysis was wrong for this Django
   version — STOP, revert Step 1, and report which check imported it.**
3. `docker build ... --build-arg UV_DEPENDENCY_GROUP=prod .` → exit 0
   (collectstatic still finds whitenoise).

### Step 2: Drop the pyupgrade hook

Delete the `asottile/pyupgrade` block from `.pre-commit-config.yaml`. Do NOT
touch `django-upgrade`.

**Verify**: fresh bake → `git add -A && uv run pre-commit run --all-files` →
all pass (ruff-check with UP rules still active — spot-check with
`uv run ruff rule UP006` printing a rule description).

### Step 3: Reconcile skills-lock.json

Remove the entire `"playwright-best-practices": { ... }` object from
`skills-lock.json` (it pins a skill that is not vendored; the template is a
backend API — the playwright skill was evidently dropped from `.agents/` but
its lock entry survived). Keep the other four entries byte-identical.

**Verify**: `python -c "import json; d=json.load(open('{{cookiecutter.project_slug}}/skills-lock.json')); assert sorted(d['skills']) == ['django-celery-expert', 'django-expert', 'mcp-builder', 'postgres']"`
→ exits 0. (Run from the template root with the path quoted.)

### Step 4: Split the Docker apt packages by stage

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

### Step 5: Full verification loop

**Verify**: fresh bake → `uv run pytest` → all pass, 100%;
`git add -A && uv run pre-commit run --all-files` → all pass; docker build →
exit 0.

## Test plan

No new pytest tests — this plan changes packaging, not behavior. The
executable verifications are Step 1's three checks, Step 2's hook run, Step
3's JSON assertion, Step 4's image probes.

## Done criteria

- [ ] `grep -n "whitenoise\|django-storages" '{{cookiecutter.project_slug}}/pyproject.toml'` → both appear once, inside `[dependency-groups].prod` only
- [ ] `grep -n pyupgrade '{{cookiecutter.project_slug}}/.pre-commit-config.yaml'` → no matches
- [ ] skills-lock.json has exactly 4 skills matching `.agents/skills/` dirs
- [ ] Dockerfile: `base` has no apt layer; builder has uuid-runtime; runtime has curl
- [ ] Baked project: `uv run pytest` + `pre-commit run --all-files` + prod docker build all pass
- [ ] Step 1's deploy-check parity command exits 0
- [ ] No files outside the in-scope list modified (`git status`)
- [ ] `plans/README.md` status row updated

## STOP conditions

- Step 1's deploy-check parity fails with a missing-module error (see inline
  instruction: revert and report).
- The maintainer intended `playwright-best-practices` to be re-vendored
  rather than dropped — if you find any reference to playwright elsewhere in
  the repo (grep first), stop and ask instead of deleting the lock entry.
- Docker build cache behaves unexpectedly after the stage split (e.g. builder
  layer invalidation on every build) — report; do not reorder COPY/RUN lines
  beyond this plan's diff.

## Maintenance notes

- Rule of thumb this plan establishes: **string-path settings references may
  live in the prod group; real imports must be in main deps.** Plans 007/009
  follow the second half.
- Anyone running prod settings locally now needs `uv sync --group=prod`.
- If a dev-served-media story is ever added (whitenoise in dev), the group
  move must be revisited.
