# Plan 015: Give generated projects a real Docker boot smoke test and a dev-image build in their own CI

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving on. If
> anything in "STOP conditions" occurs, stop and report — do not improvise. When
> done, update this plan's status row in `plans/README.md` — unless a reviewer
> dispatched you and told you they maintain the index.
>
> **Drift check (run first)**:
> `git diff --stat ae42991..HEAD -- "{{cookiecutter.project_slug}}/.github/workflows/docker-build.yaml" .github/workflows/ci.yaml "{{cookiecutter.project_slug}}/.docker/compose/prod.yaml"`
> If any changed since this plan was written, compare "Current state" against the
> live files before proceeding; on a mismatch, STOP.

## Status

- **Priority**: P3
- **Effort**: M
- **Risk**: MED (adds CI surface to every generated project; must stay knob-agnostic)
- **Depends on**: none
- **Category**: dx
- **Planned at**: commit `ae42991`, 2026-07-07

## Repository context (read before anything else)

This is a **Cookiecutter template**. Source is under `{{cookiecutter.project_slug}}/`
— **quote it in shell**.

- `{{cookiecutter.project_slug}}/.github/workflows/*` is copied **without Jinja
  rendering** — the smoke workflow you add there **must not contain any
  `{{ cookiecutter.* }}` or `{%- if %}`**. It therefore has to work for *every*
  knob combination the project could have been baked with, using only
  knob-agnostic commands.
- The **repo-root** `.github/workflows/ci.yaml` already has a
  `docker-compose-smoke` job (lines ~173-261). It is the proven pattern to adapt:
  it installs a `pre_start`-capable Docker Compose, bakes, writes a prod `.env`
  with `uuidgen` placeholders, `up -d --build --wait`, probes
  `/api/health`+`/api/ready` **from inside the api container** (knob-agnostic),
  asserts no container has exited, dumps logs on failure, and tears down `-v`.
  You are porting a trimmed, knob-agnostic version of that into the *generated*
  project's own workflows.
- Verification means baking and running the generated workflow's logic by hand
  (you cannot run GitHub Actions here; run the equivalent shell steps against a
  bake), plus linting the tracked workflow copy with actionlint.

## Why this matters

A generated project's CI builds only the **prod** image and never boots
anything: `docker-build.yaml` runs one `build-push-action` with
`UV_DEPENDENCY_GROUP=prod` and stops. So a downstream team gets a green pipeline
on (a) an image that builds but fails to *boot* or serve `/api/ready`, and (b) a
`dev` Docker target that may be broken (it is never built). The template's own CI
catches both — but that safety net does not ship to the projects it generates.
Porting a knob-agnostic boot smoke + a dev-image build closes the gap so the
template's central promise ("Docker Compose is the deployment contract") is
enforced in the projects that inherit it.

## Current state

`{{cookiecutter.project_slug}}/.github/workflows/docker-build.yaml` (full file):

```yaml
name: Docker Build
on:
  pull_request:
  push:
    branches:
      - main
concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true
jobs:
  docker-build:
    name: Docker build
    runs-on: ubuntu-latest
    steps:
      - name: Checkout repository
        uses: actions/checkout@v6.0.3
      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v4.1.0
      - name: Build image
        uses: docker/build-push-action@v7.2.0
        with:
          context: .
          file: .docker/Dockerfile
          push: false
          cache-from: type=gha
          cache-to: type=gha,mode=max
          build-args: UV_DEPENDENCY_GROUP=prod
```

Reference (repo-root `ci.yaml` smoke job — knob-agnostic bits you will reuse):

- Install Compose with `pre_start` support (pin + sha256 — copy the exact block,
  it is not knob-dependent).
- `cp .env.example .env` then `sed` the required secrets to `uuidgen` values.
  **Caveat**: the generated project does not know which secrets exist (depends on
  `use_sentry`, `email_provider`, `use_s3_media`). Since the workflow is
  unrendered, it must set every *possibly-required* key defensively — see Step 2.
- `docker compose -f .docker/compose/prod.yaml --env-file=.env up -d --build --wait --wait-timeout=300`
- Probe from inside the api container:
  `docker compose … exec api curl -fsS http://127.0.0.1:8000/api/health` (and `/api/ready`).
- Assert no exited containers; dump logs on failure; `down -v` always.

**Conventions**: extended YAML block style; pin all actions to the exact
versions already used in the repo (`actions/checkout@v6.0.3`,
`docker/setup-buildx-action@v4.1.0`, `docker/build-push-action@v7.2.0`); the
smoke must be **knob-agnostic** (no Jinja).

## The unrendered-secrets problem (read before Step 2)

The root `ci.yaml` smoke can branch (`if: matrix.variant == 'default'`) because
it *bakes* with known args. The generated workflow cannot — it runs in a repo
already baked with unknown knobs. The prod boot guards require, at minimum, a
non-insecure `SECRET_KEY`; depending on knobs it may also require
`AWS_STORAGE_BUCKET_NAME`, `RESEND_API_KEY`/`EMAIL_HOST`, and `SENTRY_DSN`.

Two designs were considered. **Implement design (b)**:

- **(b) A generated helper script** `.docker/scripts/ci-smoke-env.sh` (this dir
  *is* rendered, so it CAN be knob-aware with Jinja) that writes a valid prod
  `.env`, invoked by the unrendered workflow. It keeps the knob knowledge where
  Jinja is allowed and the unrendered workflow trivial. No
  `hooks/post_gen_project.py` deletion rule is needed (the script is useful for
  all knobs).
- **(a) Defensive `sed` in the workflow** (`sed -i "s|^KEY=.*|KEY=placeholder|"`
  per possibly-required key — a no-op when the key is absent) is the FALLBACK,
  allowed only if (b) hits a concrete blocker: the rendered script cannot
  express some knob's env requirement, or shellcheck/Jinja interactions prove
  intractable. If you fall back, record the exact blocker in your report.

## Commands you will need

| Purpose | Command | Expected |
|---------|---------|----------|
| Bake default | `uvx cookiecutter . --no-input -o /tmp/bake` | project |
| Bake minimal | `uvx cookiecutter . --no-input -o /tmp/bake-min use_celery=none email_provider=none use_sentry=no use_s3_media=no use_traefik=no` | stripped project |
| actionlint the generated workflow | (repo root) `uvx pre-commit run actionlint check-github-workflows --all-files` | exit 0 (lints the tracked copy) |
| No Jinja in workflow | `grep -c cookiecutter "{{cookiecutter.project_slug}}/.github/workflows/docker-build.yaml"` | 0 |
| Manual boot smoke (default) | in `/tmp/bake/my-project`: write `.env`, `docker compose -f .docker/compose/prod.yaml --env-file=.env up -d --build --wait --wait-timeout=300`, then `exec api curl -fsS http://127.0.0.1:8000/api/ready` | `ok`-style 200; then `down -v` |
| Manual boot smoke (minimal) | same in `/tmp/bake-min/my-project` | 200 |
| Root pre-commit | (repo root) `uvx pre-commit run --all-files` | exit 0 |

You need a working Docker + a `pre_start`-capable Compose (≥ 5.3.0) locally to
run the manual smoke; `docker compose version` must show ≥ 5.3.0. If it does not,
that is a STOP (you cannot verify the boot).

## Scope

**In scope**:
- `{{cookiecutter.project_slug}}/.github/workflows/docker-build.yaml` — add a
  dev-image build step, and either add a `smoke` job here or create a sibling
  workflow (below). **No Jinja** in this file.
- If design (b): `{{cookiecutter.project_slug}}/.docker/scripts/ci-smoke-env.sh`
  (create — rendered, may use Jinja) that writes a valid prod `.env`.
- `{{cookiecutter.project_slug}}/README.md` — one line noting CI now boots the
  stack.

**Out of scope**:
- The repo-root `ci.yaml` (its smoke already exists; do not duplicate).
- Any `src/` change; any Dockerfile change.
- Knob-conditional logic inside the unrendered workflow (impossible; use design
  (b)'s rendered script if knob-awareness is needed).

## Git workflow

- Work directly on `main`. Do NOT branch/commit/push/PR unless told. If asked to
  commit: Conventional Commits, e.g. `ci: boot-smoke and dev-image build in generated project CI`.

## Steps

### Step 1: Build the dev image too

In `docker-build.yaml`, give the existing prod build a distinct cache scope and
add a second build step for the dev target (mirroring the root `ci.yaml`
`docker-build` job which builds both with `scope=prod`/`scope=dev`):

```yaml
      - name: Build production image
        uses: docker/build-push-action@v7.2.0
        with:
          context: .
          file: .docker/Dockerfile
          push: false
          cache-from: type=gha,scope=prod
          cache-to: type=gha,mode=max,scope=prod
          build-args: UV_DEPENDENCY_GROUP=prod
      - name: Build development image
        uses: docker/build-push-action@v7.2.0
        with:
          context: .
          file: .docker/Dockerfile
          push: false
          cache-from: type=gha,scope=dev
          cache-to: type=gha,mode=max,scope=dev
          build-args: UV_DEPENDENCY_GROUP=dev
```

**Verify**: `uvx pre-commit run actionlint check-github-workflows --all-files`
exits 0; `grep -c cookiecutter …/docker-build.yaml` → 0.

### Step 2: Add the knob-agnostic boot smoke

Add a `smoke` job **in `docker-build.yaml`, after the `docker-build` job** (one
workflow keeps the generated project at six workflow files and groups the
Docker-related CI in one place; do not create a sibling workflow). Steps, all
knob-agnostic:

1. Checkout.
2. Install `pre_start`-capable Docker Compose — copy the exact
   pin+sha256+`chmod` block from the root `ci.yaml` smoke job verbatim (it is not
   knob-dependent). If that pin is stale by the time you run this, use the
   latest `docker/compose` release and update the sha — but match the version the
   compose files require (≥ 5.3.0).
3. Write a valid prod `.env`:
   - `cp .env.example .env && ./.docker/scripts/ci-smoke-env.sh` where the
     rendered script sets exactly the keys this bake needs to `uuidgen`
     placeholders (design (b)). Use two `uuidgen`s for `SECRET_KEY` (≥ 50
     chars, avoids the insecure-prefix guard) and a valid-shaped `SENTRY_DSN`.
     (Fallback (a) only per the criteria above: inline defensive `sed` for
     `SECRET_KEY`, `AWS_STORAGE_BUCKET_NAME`, `SENTRY_DSN`, `RESEND_API_KEY`,
     `EMAIL_HOST` — each a no-op if the key is absent.)
4. `docker compose -f .docker/compose/prod.yaml --env-file=.env up -d --build --wait --wait-timeout=300`.
5. Probe from inside the api container (works with or without Traefik):
   ```
   docker compose -f .docker/compose/prod.yaml --env-file=.env exec api curl -fsS http://127.0.0.1:8000/api/health
   docker compose -f .docker/compose/prod.yaml --env-file=.env exec api curl -fsS http://127.0.0.1:8000/api/ready
   ```
6. Assert no exited containers:
   `test -z "$(docker compose -f .docker/compose/prod.yaml --env-file=.env ps -q --status=exited)"`.
7. `if: failure()` → dump logs. `if: always()` → `down -v`.

Do NOT probe `http://localhost/...` (that only works when Traefik is enabled —
knob-dependent); the in-container probe is the knob-agnostic choice.

**Verify (manual, since CI can't run here)**: run steps 3-7 by hand against both
`/tmp/bake/my-project` (default) and `/tmp/bake-min/my-project` (minimal). Both
must reach `/api/ready` 200 and leave no exited containers. Then `down -v` both.

### Step 3: Document and lint

Add one line to `{{cookiecutter.project_slug}}/README.md` (Verification or CI
section): the project's CI builds prod+dev images and boots the prod stack,
probing liveness/readiness.

**Verify**: `uvx pre-commit run --all-files` (repo root) exits 0; if you added
`ci-smoke-env.sh`, it passes shellcheck and contains valid Jinja
(`uvx cookiecutter . --no-input -o /tmp/bake` still succeeds).

## Test plan

- No pytest — this is CI/ops. Verification is: actionlint clean, no-Jinja grep,
  and the **manual boot smoke against a default and a minimal bake** (Step 2).
- If design (b): confirm `ci-smoke-env.sh` writes exactly the required keys for
  default, minimal, and `email_provider=smtp` bakes (the env keys differ).

## Done criteria

ALL must hold:

- [ ] `docker-build.yaml` builds both prod and dev images (distinct cache scopes); contains no `cookiecutter` string; actionlint + check-github-workflows pass.
- [ ] A knob-agnostic `smoke` job exists in `docker-build.yaml`, probes `/api/health`+`/api/ready` from inside the api container, and asserts no exited containers.
- [ ] Manual boot smoke passes against a default bake AND a minimal bake (both reach `/api/ready` 200, no exited containers).
- [ ] If design (b): `ci-smoke-env.sh` renders correct `.env` keys across default/minimal/smtp bakes and passes shellcheck.
- [ ] README updated; root `uvx pre-commit run --all-files` exits 0; no Jinja in any unrendered workflow.
- [ ] No out-of-scope files modified (`git status`).
- [ ] `plans/README.md` status row updated.

## STOP conditions

Stop and report (do not improvise) if:

- Local Docker/Compose cannot boot the prod stack (Compose < 5.3.0 or no Docker)
  — you cannot verify the smoke.
- The minimal-bake boot fails where default succeeds — investigate whether it is
  a real defect (report) vs. a missing env key in your smoke env (fix design (a)/(b)).
- Making the smoke knob-agnostic proves impossible without Jinja (report; the
  rendered `ci-smoke-env.sh` in design (b) is the escape hatch — use it).

## Maintenance notes

- The generated smoke and the root `ci.yaml` smoke share the Compose pin+sha —
  when one is bumped, bump both (candidate for the plan-010 drift-check pattern).
- If a new prod boot guard adds a required env key (e.g. plan 008's DB-password
  guard uses the compose default, which the smoke's bundled Postgres satisfies),
  confirm the smoke's `.env` still boots.
- A reviewer should confirm the in-container probe (not `localhost`) so the smoke
  stays valid for `use_traefik=no` bakes, and that the dev image build actually
  exercises the dev dependency group.
