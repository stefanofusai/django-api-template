# Plan 022: Release workflow + GHCR registry so production deploys are immutable artifacts and rollback is repointing a tag

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving on.
> **Read the "Design decisions" section before writing code** — two choices
> there are recommendations the maintainer may overrule. If anything in "STOP
> conditions" occurs, stop and report — do not improvise. When done, update
> this plan's status row in `plans/README.md` — unless a reviewer dispatched
> you and told you they maintain the index.
>
> **Drift check (run first)**:
> `git diff --stat ae42991..HEAD -- "{{cookiecutter.project_slug}}/.docker/compose/prod.yaml" "{{cookiecutter.project_slug}}/.github/workflows/" "{{cookiecutter.project_slug}}/.env.example" "{{cookiecutter.project_slug}}/README.md" "{{cookiecutter.project_slug}}/pyproject.toml"`
> If any changed since this plan was written, compare "Current state" against
> the live files before proceeding; on a mismatch, STOP. (Plans 009 and 015
> touch neighboring regions of `prod.yaml` / `docker-build.yaml` — reconcile
> if they landed first.)

## Status

- **Priority**: P2 (numbered 022 because plan numbers are frozen after the
  renumbering pass; the index table's row order, not the number, is the
  execution order for new plans)
- **Effort**: M
- **Risk**: MED (touches how prod sources its images; the default `up -d --build`
  path must keep working for CI smokes and first-boot)
- **Depends on**: none (sequence with 009 — same `prod.yaml`; and with 015 —
  same `docker-build.yaml` family)
- **Category**: dx / operations
- **Planned at**: commit `ae42991`, 2026-07-07

## Repository context (read before anything else)

This is a **Cookiecutter template**. Source is under
`{{cookiecutter.project_slug}}/` — **quote it in shell**.

- `{{cookiecutter.project_slug}}/.github/workflows/*` is copied **WITHOUT
  Jinja rendering** — the new `release.yaml` must contain **no**
  `{{ cookiecutter.* }}`; anything project-specific must come from GitHub's
  own context (`${{ github.repository }}`) at runtime.
- `{{cookiecutter.project_slug}}/.docker/compose/*` and `.env.example` ARE
  rendered — Jinja is allowed there.
- **The root pre-commit does NOT lint generated workflows** (it `exclude`s
  the whole template dir). The actionlint/check-github-workflows gate for the
  new workflow is the **baked** project's pre-commit run.
- Verification means baking (`uvx cookiecutter . --no-input -o /tmp/bake`)
  plus, for the compose change, `docker compose config` and a local boot
  (Docker + Compose ≥ 5.3.0). You cannot execute the release workflow here —
  its gate is actionlint + schema check + a dry-run of its version-match
  logic.

## Why this matters

Today a generated project has **no immutable deploy artifact**: the prod
compose builds all app containers from source on the host (`build:` blocks,
no `image:`), the CI's `docker-build.yaml` builds with `push: false` and
publishes nothing, and there is no release workflow or tagging convention.
Deploy is "pull the branch and `up -d --build`"; rollback is "checkout an
older commit and **rebuild**" — slow, non-atomic, and not byte-identical to
what was running before (the base image and apt layers are tag-pinned, not
digest-pinned, so a rebuild weeks later can differ).

Meanwhile the version concept already half-exists: `sentry.py` initializes
with `release=project_version`, read from `pyproject.toml [project] version`.
Releases are named — they just aren't tied to any artifact you can run.

The fix: a tag-triggered release workflow that builds once and pushes to
GHCR, and a prod compose that *consumes* that image by tag. Deploy becomes
`APP_VERSION=v1.2.3 → docker compose pull → docker rollout` (the README
already documents `docker rollout` for zero-downtime replacement); rollback
becomes repointing `APP_VERSION` at the previous tag — seconds, with the old
image typically still in the host cache.

## Current state

`{{cookiecutter.project_slug}}/.docker/compose/prod.yaml` — all three app
services build from source and have **no `image:` key**:

- `api` (lines 9-14): `build: context: ../.. / dockerfile: .docker/Dockerfile /
  args: UV_DEPENDENCY_GROUP: prod`
- `celery-beat` (lines 85-90, when `worker+beat`): identical build block
- `celery-worker` (lines 105-110, when celery enabled): identical build block

`{{cookiecutter.project_slug}}/.github/workflows/docker-build.yaml` (28
lines): single job, one `docker/build-push-action@v7.2.0` step with
`push: false` — CI proves the image builds and discards it.

`{{cookiecutter.project_slug}}/src/config/settings/components/sentry.py:21-23`:
`sentry_sdk.init(dsn=..., release=project_version, ...)` where
`project_version` comes from `src/config/pyproject.py:16`
(`project_metadata.get("version")` out of `pyproject.toml`).

`{{cookiecutter.project_slug}}/README.md` `## Production` (line 218+): start
command is `docker compose -f .docker/compose/prod.yaml --env-file=.env up -d
--wait`; the Traefik variants document `docker rollout` semantics (lines
238-244 / 253-259). No deploy-a-version or rollback runbook exists.

The **root** `.github/workflows/ci.yaml` `docker-compose-smoke` job boots the
prod compose with `up -d --build --wait` — it builds locally and must keep
working with no registry access (the baked project it boots has never
published a release).

Existing conventions: exact action pins (`actions/checkout@v6.0.3`,
`docker/setup-buildx-action@v4.1.0`, `docker/build-push-action@v7.2.0`);
`name:`/`on:`/`concurrency:` shapes as in the sibling workflows; gitlint
enforces Conventional Commits; `.env.example` contract ("Commented values are
optional overrides with safe code defaults"); `github_username` is a
cookiecutter knob (used by dependabot assignees).

## Design decisions (recommendations — confirm or overrule before coding)

1. **Hybrid `image:` + `build:`, not image-only.** Each app service gains
   `image: ghcr.io/{{ cookiecutter.github_username }}/{{ cookiecutter.project_slug }}:${APP_VERSION:-latest}`
   and **keeps** its `build:` block. Rationale: `docker compose up -d --build`
   (used by the root CI smoke, plan 015's generated smoke, and first-boot
   before any release exists) builds locally and tags the result with the
   `image:` name — no registry needed; while a release-based deploy uses
   `docker compose pull` + `up -d`/`docker rollout` and never builds. The cost
   is a documented footgun: an operator who habitually passes `--build` runs a
   source build instead of the released artifact — the README runbook must say
   "deploys never pass `--build`".
2. **Image name is rendered into compose; the workflow derives its own from
   `github.repository`.** The workflow (unrendered) pushes to
   `ghcr.io/<owner>/<repo>` (lowercased); compose (rendered) defaults to
   `ghcr.io/<github_username>/<project_slug>`. These coincide when the repo is
   named after the slug — the template's normal assumption. The README must
   state: if your repository name differs from the slug, align the `image:`
   lines. (Do NOT try to solve this with Jinja in the workflow — it is copied
   unrendered.)
3. **Versioning = git tag `vX.Y.Z`, gated to equal `pyproject.toml` version.**
   The release workflow fails if the pushed tag does not match
   `[project] version` — this keeps image tags and Sentry `release` names
   identical, so an error in Sentry names the exact image to roll back to.
   No release bot (release-please/git-cliff) in this first cut — Conventional
   Commits make that a natural follow-up, note it and move on.
4. **Deploy and rollback are one script, not a hand-typed runbook.**
   `.docker/scripts/deploy.sh <tag>` repoints `APP_VERSION` in `.env`, pulls,
   and replaces the containers; **rollback is the same script invoked with an
   earlier tag** — there is deliberately no separate rollback path to keep the
   two operations byte-identical and equally rehearsed. This follows the
   repo's own lesson (plan 002: the hand-typed `pg_restore` runbook shipped
   broken; scripts are the convention for critical operations —
   `postgres-backup.sh`/`postgres-restore.sh` are the precedent).

If the maintainer prefers image-only prod compose (no `build:`), or a
registry knob, STOP and surface the trade-offs above instead of building both.

## Commands you will need

| Purpose | Command | Expected |
|---------|---------|----------|
| Bake default | `uvx cookiecutter . --no-input -o /tmp/bake` | project |
| Compose interpolation | `cd /tmp/bake/my-project && cp .env.example .env && docker compose -f .docker/compose/prod.yaml --env-file=.env config` | exit 0; `image:` renders with `latest` default |
| Local boot (build path) | `docker compose -f .docker/compose/prod.yaml --env-file=.env up -d --build --wait --wait-timeout=300` (prod-safe env first) | boots exactly as today |
| Baked pre-commit (lints the new workflow) | `cd /tmp/bake/my-project && git add -A && uv run pre-commit run --all-files` | exit 0 (actionlint + check-github-workflows pass) |
| No Jinja in the workflow | `grep -c cookiecutter "{{cookiecutter.project_slug}}/.github/workflows/release.yaml"` | 0 |
| Deploy script parse check | (in a bake) `sh -n .docker/scripts/deploy.sh` | exit 0 (the template source contains Jinja — lint the RENDERED copy) |
| Deploy script shellcheck | (in a bake) `uvx --from shellcheck-py shellcheck .docker/scripts/deploy.sh` | exit 0 (no shellcheck hook exists until plan 006 lands) |
| Root pre-commit | (repo root) `uvx pre-commit run --all-files` | exit 0 |

## Scope

**In scope**:
- `{{cookiecutter.project_slug}}/.github/workflows/release.yaml` (create — NO
  Jinja).
- `{{cookiecutter.project_slug}}/.docker/scripts/deploy.sh` (create — rendered,
  knob-aware Jinja allowed; ships for ALL knobs, so no
  `hooks/post_gen_project.py` deletion rule is needed).
- `{{cookiecutter.project_slug}}/.docker/compose/prod.yaml` — add `image:` to
  the `api`, `celery-worker`, `celery-beat` services (keep `build:`).
- `{{cookiecutter.project_slug}}/.env.example` — add a commented
  `# APP_VERSION=v0.1.0` optional override (Django block? No — it is
  process/deploy sizing; put it in the "Process sizing" block or a new
  "Release" block, alphabetized; follow the file's grouping conventions).
- `{{cookiecutter.project_slug}}/README.md` — deploy-a-release + rollback
  runbook in `## Production`, including the migration-compatibility caveat.

**Out of scope**:
- `docker-build.yaml` (unchanged — it remains the PR-time "does it build"
  check; plan 015 extends it separately).
- The **dev** compose (keeps building from source — correct for the dev loop).
- Release automation bots, changelog generation, cosign/SBOM/provenance —
  follow-ups, note them in Maintenance.
- Any `src/` change (Sentry already reads the version).
- The root `ci.yaml` (its smoke keeps working via the hybrid design — verify,
  don't edit).

## Git workflow

- Work directly on `main`. Do NOT branch/commit/push/PR unless told. If asked
  to commit: Conventional Commits, e.g.
  `feat: publish releases to ghcr and deploy by image tag`.

## Steps

### Step 1: Add `image:` to the three app services

In `prod.yaml`, on each of `api`, `celery-beat`, `celery-worker`, add (keeping
the service's keys alphabetized — `build`, `command`, `depends_on`,
`env_file`, `environment`, `healthcheck`, `image`, …; check where `image`
sorts among the existing keys and match the file's ordering):

```yaml
    image: ghcr.io/{{ cookiecutter.github_username }}/{{ cookiecutter.project_slug }}:${APP_VERSION:-latest}
```

All three services share one image (same build context/args today), so one
pull serves all.

**Verify**:
```
uvx cookiecutter . --no-input -o /tmp/bake
grep -c "image: ghcr.io/johndoe/my-project" /tmp/bake/my-project/.docker/compose/prod.yaml   # 3 (default bake, celery worker+beat)
uvx cookiecutter . --no-input -o /tmp/bake-nc use_celery=none
grep -c "image: ghcr.io/johndoe/my-project" /tmp/bake-nc/my-project/.docker/compose/prod.yaml # 1
cd /tmp/bake/my-project && cp .env.example .env && docker compose -f .docker/compose/prod.yaml --env-file=.env config | grep "image: ghcr" | head -3
```
→ counts as annotated; `config` shows `:latest` interpolated (no `APP_VERSION`
set) and exits 0.

### Step 2: Confirm the build path still works (the CI-smoke contract)

With Docker available, boot the default bake exactly the way the root CI
smoke does (write the prod-safe `.env` the way `ci.yaml`'s smoke job does —
`uuidgen` placeholders), using `up -d --build --wait`. Compose must **build**
(not attempt a registry pull) and tag the local image with the `image:` name.

**Verify**: stack reaches healthy, `docker image ls ghcr.io/johndoe/my-project`
shows a local `latest`, no `pull access denied` errors anywhere in the output.
Then `down -v`. If Docker is unavailable this is a STOP (the hybrid behavior
cannot be verified by grep).

### Step 3: Create `release.yaml`

Create `{{cookiecutter.project_slug}}/.github/workflows/release.yaml` — plain
YAML, no Jinja. Shape (match sibling workflows' style; pin exact action
versions used elsewhere in the repo; `docker/login-action` and
`docker/metadata-action` are new to this repo — pin their latest exact
releases and note the pins in your report):

```yaml
name: Release
on:
  push:
    tags:
      - v*
concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
permissions:
  contents: read
  packages: write
jobs:
  release:
    name: Build and push release image
    runs-on: ubuntu-latest
    steps:
      - name: Checkout repository
        uses: actions/checkout@v6.0.3
      - name: Verify tag matches pyproject version
        run: |
          tag="${GITHUB_REF_NAME#v}"
          version="$(python3 -c 'import tomllib; print(tomllib.load(open("pyproject.toml","rb"))["project"]["version"])')"
          if [ "$tag" != "$version" ]; then
            echo "tag v$tag does not match pyproject version $version" >&2
            exit 1
          fi
      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v4.1.0
      - name: Log in to GHCR
        uses: docker/login-action@<pinned>
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}
      - name: Compute image name
        id: image
        run: echo "name=ghcr.io/${GITHUB_REPOSITORY,,}" >> "$GITHUB_OUTPUT"
      - name: Build and push
        uses: docker/build-push-action@v7.2.0
        with:
          context: .
          file: .docker/Dockerfile
          push: true
          build-args: UV_DEPENDENCY_GROUP=prod
          cache-from: type=gha,scope=prod
          tags: |
            ${{ steps.image.outputs.name }}:${{ github.ref_name }}
            ${{ steps.image.outputs.name }}:latest
```

Notes: `${GITHUB_REPOSITORY,,}` lowercases (GHCR requires lowercase; the
bash-4 idiom works on ubuntu runners). Reusing `cache-from: scope=prod` warms
from `docker-build.yaml`'s PR builds; do not write `cache-to` here (releases
are rare; keep the PR cache authoritative). No `concurrency.cancel-in-progress`
— never cancel a half-pushed release.

**Verify**:
```
grep -c cookiecutter "{{cookiecutter.project_slug}}/.github/workflows/release.yaml"   # 0
cd /tmp/bake/my-project && git add -A && uv run pre-commit run actionlint check-github-workflows --all-files
```
→ 0 and exit 0 (remember: the BAKED pre-commit is the lint gate — the root
config excludes the template dir). Also dry-run the version-match logic
locally: run the `Verify tag` script body in the bake with
`GITHUB_REF_NAME=v0.1.0` → exits 0 (pyproject ships `version = "0.1.0"` —
confirm the actual value first and adjust) and with `GITHUB_REF_NAME=v9.9.9`
→ exits 1.

### Step 4: Add `APP_VERSION` to `.env.example`

Add a commented optional override with an own-line comment, in the
appropriate block per the file's grouping/alphabetization rules:

```
# Release image tag the prod stack runs; deploys and rollbacks repoint this.
# The v-prefixed tag of a published release (the workflow guarantees v<X.Y.Z>
# equals that release's pyproject version, which is what Sentry reports).
# APP_VERSION=v0.1.0
```

(Relationship to make explicit here and in the runbook: `pyproject.version`
is the source of truth for *what a release is*; `APP_VERSION` is per-host
deployment state for *which release runs now*. They match at release time by
the workflow's gate — modulo the `v` prefix — and intentionally diverge
during a rollback, when the running image's own baked-in `pyproject` keeps
Sentry's `release` accurate for the code actually serving traffic.)

**Verify**: `grep -c "APP_VERSION" /tmp/bake/my-project/.env.example` → ≥ 1
after re-bake; baked pre-commit exits 0.

### Step 5: Create `deploy.sh` — one script for deploy AND rollback

Create `{{cookiecutter.project_slug}}/.docker/scripts/deploy.sh`, mode 0755
(the baked `check-shebang-scripts-are-executable` hook enforces the bit).
This file is **rendered** — knob-aware Jinja is allowed and required. Target
shape (match the sibling scripts' conventions: `#!/bin/sh`, `set -eu`,
`${1:?usage}` argument handling as in `postgres-backup.sh`):

```sh
#!/bin/sh
set -eu

# Deploys a published release by repointing APP_VERSION in .env, pulling the
# image, and replacing the running containers. Rollback IS this script run
# with an earlier tag. Run from the project root. Note: the database schema
# is not rolled back — keep migrations backward-compatible one release back
# (see README, Production).

APP_VERSION=${1:?usage: deploy.sh <tag, e.g. v1.2.3>}

case $APP_VERSION in
    v[0-9]*.[0-9]*.[0-9]*) ;;
    *) echo "tag must look like v<major>.<minor>.<patch>" >&2; exit 2 ;;
esac

[ -f .env ] || { echo "no .env here; run from the project root" >&2; exit 2; }

if grep -q '^APP_VERSION=' .env; then
    # sed -i needs a suffix arg on BSD/macOS; -i.bak + rm is the portable form.
    sed -i.bak "s/^APP_VERSION=.*/APP_VERSION=$APP_VERSION/" .env
    rm -f .env.bak
else
    printf 'APP_VERSION=%s\n' "$APP_VERSION" >> .env
fi

docker compose -f .docker/compose/prod.yaml --env-file=.env pull
{%- if cookiecutter.use_traefik == "yes" %}
docker rollout -f .docker/compose/prod.yaml --env-file=.env api
{%- endif %}
docker compose -f .docker/compose/prod.yaml --env-file=.env up -d --wait
```

Knob notes the executor must preserve:
- **Traefik bakes** replace `api` zero-downtime via `docker rollout` (the
  README already documents its semantics), then `up -d --wait` reconciles the
  remaining services (worker/beat get a brief restart — they are stateless).
  Decide (and record) how to handle a missing `docker-rollout` plugin: a
  `command -v docker-rollout`-style guard with a clear error is preferred over
  silently degrading to `up -d`.
- **Non-Traefik bakes** cannot use rollout at all (the `api` service binds
  `127.0.0.1:8000:8000`, so a second replica can't start) — plain
  `up -d --wait` with its brief blip is correct there; do not render the
  rollout line.
- No `--build` anywhere in this script — that is the point of it.

**Verify** (on bakes of BOTH `use_traefik` states):
```
uvx cookiecutter . --no-input -o /tmp/bake
uvx cookiecutter . --no-input -o /tmp/bake-nt use_traefik=no
for d in /tmp/bake /tmp/bake-nt; do
  sh -n "$d/my-project/.docker/scripts/deploy.sh"
  uvx --from shellcheck-py shellcheck "$d/my-project/.docker/scripts/deploy.sh"
done
grep -c "docker rollout" /tmp/bake/my-project/.docker/scripts/deploy.sh      # 1
grep -c "docker rollout" /tmp/bake-nt/my-project/.docker/scripts/deploy.sh   # 0
test -x /tmp/bake/my-project/.docker/scripts/deploy.sh && echo EXEC_OK
```
→ parse + shellcheck clean in both states; rollout line present only for the
Traefik bake; `EXEC_OK`. Also smoke the `.env`-rewrite half without Docker:
in a scratch dir with a fake `.env`, run the script body's sed/append logic
for both cases (existing `APP_VERSION=` line, absent line) and confirm the
resulting file — one line, correct value, nothing else touched.

### Step 6: Write the deploy/rollback runbook

In `{{cookiecutter.project_slug}}/README.md` `## Production`, after the
start-the-stack intro, add a "Releases and rollback" passage covering:

1. **Cut a release**: bump `[project] version` in `pyproject.toml`, commit,
   tag `v<version>`, push the tag — CI publishes
   `ghcr.io/<owner>/<repo>:v<version>` (the workflow refuses a tag that does
   not match `pyproject.toml`, keeping Sentry `release` names aligned with
   image tags).
2. **Deploy a release**: `./.docker/scripts/deploy.sh v<version>` from the
   project root. State what it does (repoints `APP_VERSION` in `.env`, pulls,
   replaces containers) so operators trust it. **Never deploy with
   `up -d --build`** — that runs a source build instead of the published
   artifact.
3. **Rollback is the same command with the previous tag**:
   `./.docker/scripts/deploy.sh v<previous>`. Usually seconds — the prior
   image is still in the host cache, so the pull is a no-op. Finding the
   previous tag: `git tag --sort=-v:refname | head`, or the GHCR package
   page.
4. **The migration caveat** (do not soften this): rolling back the image does
   NOT roll back the database — the api's `pre_start` runs `migrate` on boot,
   so the schema stays at the newer version. Rollback is safe only while
   migrations remain backward-compatible one release back; write reversible,
   additive migrations and squash/clean up later. (If the vendored
   `django-safe-migration` skill is present — plan 012 — point at it.)
5. The name-mismatch note from Design decision 2: if the GitHub repository is
   not named `<project_slug>`, update the `image:` lines in
   `.docker/compose/prod.yaml` to match `ghcr.io/<owner>/<repo>`. Also note
   GHCR package visibility: for private repos the pulling host needs a PAT
   with `read:packages` (`docker login ghcr.io`) — one sentence, don't build
   tooling for it.

**Verify**: root `uvx pre-commit run markdownlint --all-files` exits 0 —
plus re-bake and run the baked pre-commit (markdownlint sees the rendered
README there).

### Step 7: Full regression

Default bake AND `use_celery=none` bake: baked `uv run pytest` (unaffected —
confirm), baked pre-commit, `docker compose config`, and the Step 2 boot on
the default bake. Root pre-commit. Also confirm Dependabot behavior: the new
`image:` lines carry a variable tag (`${APP_VERSION:-latest}`) — check
`.github/dependabot.yaml`'s `docker-compose` ecosystem does not choke on it
(inspect config only; note in your report that the first Dependabot run after
merge should be watched — it must keep bumping `postgres`/`redis`/`traefik`
and skip the variable-tagged app image).

## Test plan

- No pytest (deploy/CI config; `AGENTS.md` forbids config-only tests). Gates:
  the bake-grep matrix (Step 1), the `--build` boot proving the smoke contract
  (Step 2), baked actionlint/check-github-workflows on the new workflow
  (Step 3), the tag-match dry-run both ways (Step 3), and the full regression
  (Step 6). The end-to-end push can only be proven on GitHub after merge —
  state that explicitly in your report (first tag push is the real test).

## Done criteria

ALL must hold:

- [ ] Default bake: 3 `image: ghcr.io/...` lines in `prod.yaml` (1 in a `use_celery=none` bake), all with `${APP_VERSION:-latest}`; `docker compose config` exits 0.
- [ ] `up -d --build` on a default bake still boots with **no** registry pull (Step 2).
- [ ] `release.yaml` exists, contains no `cookiecutter` string, passes the baked actionlint + check-github-workflows, has `packages: write`, is tag-triggered, and its version-match gate passes/fails correctly in the dry-run.
- [ ] `.env.example` documents `APP_VERSION` as a commented optional override.
- [ ] `deploy.sh` exists, mode 0755, passes `sh -n` + shellcheck on BOTH `use_traefik` bakes, renders `docker rollout` only for Traefik bakes, contains no `--build`, and its `.env`-rewrite logic handles both the existing-line and absent-line cases (scratch smoke).
- [ ] README's runbook invokes `deploy.sh` for BOTH deploy and rollback (no hand-typed multi-command sequence), and includes the migration-compatibility caveat and the never-`--build` warning.
- [ ] Baked pytest unaffected; baked + root pre-commit exit 0; no out-of-scope files modified (`git status`).
- [ ] `plans/README.md` status row updated.

## STOP conditions

Stop and report (do not improvise) if:

- The maintainer overrules a Design decision (image-only compose, registry
  knob, different tag scheme) — surface trade-offs, don't build both.
- Docker/Compose is unavailable — Step 2's hybrid-behavior check cannot run
  and grep-only verification is insufficient here.
- Compose's `image:`+`build:` semantics don't behave as described on the
  pinned Compose version (e.g. `up -d` without `--build` attempts a pull and
  hard-fails when the registry has no image AND no local build exists — if
  the observed first-boot UX is worse than documented, report it; a
  `pull_policy` tweak may be needed and that is a design change).
- The root `ci.yaml` smoke breaks in any way (it must not — it uses `--build`).
- shellcheck demands a bashism in `deploy.sh` (shebang must stay `/bin/sh`),
  or the portable `sed -i.bak` idiom misbehaves on the target platform.
- You cannot settle the missing-`docker-rollout` handling for Traefik bakes
  (hard error vs. degrade) from the README's existing rollout prose — report
  both options instead of picking silently.
- `check-github-workflows` rejects `pre_start`-era schema or the new workflow
  shape for reasons you cannot fix by matching sibling workflows — report.

## Maintenance notes

- **Follow-ups deliberately deferred**: changelog/semver automation (gitlint
  already enforces Conventional Commits, so release-please/git-cliff slot in
  cleanly); image signing/SBOM/provenance attestations; digest-pinning the
  released tag in `.env` for maximum immutability.
- `docker-build.yaml` (PR check) and `release.yaml` (tag publish) share the
  Dockerfile and the `scope=prod` build cache — if the Dockerfile's build args
  change, update both.
- A reviewer should scrutinize: the three `image:` lines stay identical to
  each other; the workflow has no Jinja and no `cancel-in-progress`; the
  runbook's rollback section keeps the migration caveat prominent; `deploy.sh`
  has no `--build` and its Jinja renders valid sh in both `use_traefik`
  states.
- Once plan 006 (shellcheck hook) lands, `deploy.sh` is linted automatically
  on every commit — the hand-run shellcheck here is interim.
- Released images accumulate on the host over time (one per deployed tag).
  Do NOT auto-prune in `deploy.sh` — the previous tag IS the rollback
  candidate. The runbook may note a manual, occasional
  `docker image prune -a --filter "until=<period>"` once a release is old
  enough to never roll back to.
- If plan 015 lands, its generated smoke also boots with `--build` — the
  hybrid design covers it; re-confirm after both are merged.
