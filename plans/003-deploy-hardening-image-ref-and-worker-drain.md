# Plan 003: Fix the GHCR image ref for uppercase usernames and let the Celery worker drain on deploy

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving to the
> next step. If anything in the "STOP conditions" section occurs, stop and
> report — do not improvise. When done, update the status row for this plan
> in `plans/README.md` — unless a reviewer dispatched you and told you they
> maintain the index.
>
> **Drift check (run first)**:
> `git diff --stat eee3978..HEAD -- '{{cookiecutter.project_slug}}/.docker/compose/prod.yaml' '{{cookiecutter.project_slug}}/README.md'`
> If any in-scope file changed since this plan was written, compare the
> "Current state" excerpts against the live code before proceeding; on a
> mismatch, treat it as a STOP condition.

## Status

- **Priority**: P2
- **Effort**: S
- **Risk**: LOW
- **Depends on**: none
- **Category**: bug / ops
- **Planned at**: commit `eee3978`, 2026-07-08

## Why this matters

Two deploy-path defects. (1) `prod.yaml` renders the GHCR image name from
`github_username` verbatim, but Docker rejects uppercase repository names and
the pre-gen hook explicitly allows uppercase usernames — a user named
`JohnDoe` gets a project where every `docker compose pull`/`up`, and therefore
`deploy.sh` and the backup scripts, fails outright. The release workflow
already lowercases its side (`ghcr.io/${GITHUB_REPOSITORY,,}`), so publish and
deploy silently disagree. (2) The `celery-worker` service has no
`stop_grace_period`, so Docker SIGKILLs it 10 seconds after SIGTERM while
tasks are allowed to run up to 330 seconds (`CELERY_TASK_TIME_LIMIT`) — every
deploy hard-kills in-flight tasks, which acks-late then redelivers and re-runs
from scratch. The `api` service already gets this right (35s, with a comment
explaining why).

## Current state

This repo is a **cookiecutter template**; `prod.yaml` contains Jinja and is
verified by baking. Always single-quote paths containing
`{{cookiecutter.project_slug}}` in shell commands.

`{{cookiecutter.project_slug}}/.docker/compose/prod.yaml` — three identical
image lines (api `:46`, celery-beat `:104`, celery-worker `:134`):

```yaml
    image: ghcr.io/{{ cookiecutter.github_username }}/{{ cookiecutter.project_slug }}:${APP_VERSION:-unreleased}
```

(`project_slug` is validated lowercase by `hooks/pre_gen_project.py`;
`github_username` is validated by
`GITHUB_USERNAME_PATTERN = ^[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})$` — uppercase
allowed. GitHub usernames are case-insensitive, so lowercasing is always
safe.)

The worker service (`prod.yaml:109-140`) ends:

```yaml
{% if cookiecutter.use_s3_media == "no" %}
    volumes:
      - media_data:/app/media
{% endif %}
    restart: unless-stopped
```

— no `stop_grace_period`. For contrast, the api service (`prod.yaml:82-86`)
has:

```yaml
    # Must exceed GUNICORN_GRACEFUL_TIMEOUT (.env, default 30s) so Docker
    # never SIGKILLs a still-draining gunicorn. ...
    stop_grace_period: 35s
```

Celery settings (`src/config/settings/components/celery.py:29-34`):
`CELERY_TASK_ACKS_LATE = True`, `CELERY_TASK_REJECT_ON_WORKER_LOST = True`,
`CELERY_TASK_SOFT_TIME_LIMIT = 300`, `CELERY_TASK_TIME_LIMIT = 330`. Celery's
warm shutdown (SIGTERM) stops consuming and finishes in-flight tasks, so the
grace period is a worst-case cap, not a fixed wait — `docker compose up`/
`docker stop` return as soon as the process exits.

The counterpart naming logic in the (non-Jinja, `_copy_without_render`)
release workflow, `{{cookiecutter.project_slug}}/.github/workflows/release.yaml:40-42`:

```yaml
      - name: Compute GHCR image name
        id: image
        run: echo "name=ghcr.io/${GITHUB_REPOSITORY,,}" >> "$GITHUB_OUTPUT"
```

`GITHUB_REPOSITORY` is `<owner>/<repo-name>`, so publish and deploy only agree
when the GitHub repo is named exactly `project_slug`. The template's root
README already frames the slug as the repository name ("Repository and package
distribution name" in its Variables table); the generated project README's
Production section documents the deploy flow.

Repo conventions: compose keys within a service match the existing services'
order (the api service puts `stop_grace_period` directly after `restart` —
mirror it); comments explain constraints, not mechanics; conventional
commits.

## Commands you will need

| Purpose | Command | Expected on success |
|---------|---------|---------------------|
| Bake default | `uvx cookiecutter . -o /tmp/verify-003/default --no-input` | project generated |
| Render compose config (in bake) | `cp .env.example .env && docker compose -f .docker/compose/prod.yaml --env-file=.env config` | valid rendered YAML on stdout |
| Bake worker-only | `uvx cookiecutter . -o /tmp/verify-003/worker --no-input use_celery=worker` | project generated |
| Root checks | `uvx pre-commit run --all-files` | all hooks pass |

Note: `docker compose config` for the default bake needs `TRAEFIK_DOMAIN` etc.
from `.env` — `cp .env.example .env` provides them all.

## Scope

**In scope** (the only files you should modify):
- `{{cookiecutter.project_slug}}/.docker/compose/prod.yaml`
- `{{cookiecutter.project_slug}}/README.md` (one clarifying sentence, Step 3)

**Out of scope** (do NOT touch, even though they look related):
- `{{cookiecutter.project_slug}}/.github/workflows/release.yaml` — it is
  `_copy_without_render` (no Jinja allowed) and its lowercasing is already
  correct; do not try to inject the slug there.
- `hooks/pre_gen_project.py` — do NOT tighten the username pattern to
  lowercase-only; uppercase usernames are valid on GitHub and used in
  Dependabot assignees/badges where case is fine.
- `.docker/scripts/deploy.sh`, backup scripts — they operate through
  prod.yaml and need no change.
- `celery-beat` service — no long-running work; the 10s default is fine.

## Git workflow

- Branch: `advisor/003-deploy-hardening`
- Two commits, e.g. `fix: lowercase the GHCR owner in prod image refs` and
  `fix: let the celery worker drain before SIGKILL on deploy`.
- Do NOT push or open a PR unless the operator instructed it.

## Steps

### Step 1: Lowercase the GHCR owner segment

In `prod.yaml`, change all three image lines to:

```yaml
    image: ghcr.io/{{ cookiecutter.github_username | lower }}/{{ cookiecutter.project_slug }}:${APP_VERSION:-unreleased}
```

**Verify**:
`grep -c 'github_username | lower' '{{cookiecutter.project_slug}}/.docker/compose/prod.yaml'`
→ `3` (api, celery-beat, celery-worker; if the file drifted and has a
different count of image lines, STOP).

### Step 2: Add stop_grace_period to celery-worker

In the `celery-worker` service, add after `restart: unless-stopped`, matching
the api service's comment style (a constraint-explaining comment):

```yaml
    restart: unless-stopped
    # Must exceed CELERY_TASK_TIME_LIMIT (330s, settings/components/celery.py)
    # so a warm shutdown can finish the in-flight task instead of Docker
    # SIGKILLing it mid-run; acks_late would then redeliver and re-run it.
    # Warm shutdown exits as soon as running tasks finish, so this is a
    # worst-case cap, not a fixed wait.
    stop_grace_period: 335s
```

Keep the service's existing key order otherwise. Note the Jinja
`{% if use_s3_media == "no" %}` volumes block sits above `restart` — do not
disturb it.

**Verify** (rendered structure, default bake):
```
uvx cookiecutter . -o /tmp/verify-003/default --no-input
cd /tmp/verify-003/default/my-project && cp .env.example .env
docker compose -f .docker/compose/prod.yaml --env-file=.env config | grep 'stop_grace_period'
```
→ `config` exits 0 (valid compose file) and shows two `stop_grace_period`
entries (api 35s, worker 335s — compose may normalize to `5m35s`).

### Step 3: Document the repo-name requirement

In the generated project README's Production/release section (the part
describing tagging and `deploy.sh` — find it with
`grep -n 'APP_VERSION\|deploy.sh' '{{cookiecutter.project_slug}}/README.md'`),
add one sentence stating: the GitHub repository must be named
`{{ cookiecutter.project_slug }}` (the release workflow publishes to
`ghcr.io/<owner>/<repo-name>` while the Compose stack pulls
`ghcr.io/<owner>/{{ cookiecutter.project_slug }}`; they only match when repo
name = slug). Use surrounding prose style; wrap near 80 columns like the rest
of the file.

**Verify**: bake default and confirm the sentence renders with the slug
substituted:
`grep -n 'must be named' /tmp/verify-003/default/my-project/README.md` → 1 match.

### Step 4: Full render + checks sweep

**Verify**:
```
uvx cookiecutter . -o /tmp/verify-003/worker --no-input use_celery=worker
cd /tmp/verify-003/worker/my-project && cp .env.example .env && docker compose -f .docker/compose/prod.yaml --env-file=.env config --quiet
```
→ exit 0. Then in the default bake, after `git add -A`:
`uv sync --locked && uv run pre-commit run --all-files`
→ all hooks pass except any failures documented as plan 001's known defects
(`ruff-format` on `tests/core/integration/admin_test.py` if 001 hasn't landed
— note it, don't fix it here). Root: `uvx pre-commit run --all-files` → pass.

## Test plan

No Python tests — this is compose/docs surface. The machine checks are the
rendered `docker compose config` validations above plus the generated
project's `yamllint`/pre-commit run in Step 4. The template CI smoke test
(`smoke-test-docker-compose` in root `.github/workflows/ci.yaml`) exercises
the changed prod.yaml end-to-end on push.

## Done criteria

Machine-checkable. ALL must hold:

- [ ] `grep -c 'github_username | lower' .../prod.yaml` → 3, and
      `grep -c 'ghcr.io/{{ cookiecutter.github_username }}/' .../prod.yaml` → 0
- [ ] Default and worker-only bakes: `docker compose -f .docker/compose/prod.yaml --env-file=.env config --quiet` → exit 0
- [ ] Default bake rendered config contains `stop_grace_period` for both `api` and `celery-worker`
- [ ] README sentence renders in the default bake (Step 3 grep)
- [ ] `git status --short` shows changes ONLY to the two in-scope files
- [ ] `plans/README.md` status row updated

## STOP conditions

Stop and report back (do not improvise) if:

- `prod.yaml` has other than three `image:` lines matching the excerpt.
- `docker compose config` fails on a bake for a reason unrelated to your edit
  (report the error; it's a pre-existing defect).
- You find yourself wanting to edit `release.yaml` or `deploy.sh` — the fix
  belongs in prod.yaml + README only.

## Execution note (2026-07-08)

Executed as commits `c7c1c26` (image lowercasing + README sentence) and
`04130f7` (worker `stop_grace_period`) on branch `advisor/003-deploy-hardening`
(not yet merged to `main`). Steps 1, 2, and 4 landed exactly as specified.

Step 3 needed one round of revision: the README already had a pre-existing
paragraph (this plan's "Current state" excerpt didn't know about it) telling
users what to do if the repo name differs from the slug. The executor's first
pass added the new sentence without touching it, producing two overlapping
explanations of the same repo-name/slug coupling ~24 lines apart. Reviewer
asked for consolidation: the new upfront sentence stays (states the
constraint and why), the older paragraph was trimmed to drop the repeated
"differs from `{{ project_slug }}`" framing and keep only the remedy +
unrelated GHCR-login sentence. Final wording verified rendered and clean on
review.

## Maintenance notes

- If a knob ever decouples the GitHub repo name from `project_slug`, the
  image-name contract in Step 3's sentence breaks — revisit both sides then.
- Reviewer: check the worker comment states the 330s source-of-truth
  (`CELERY_TASK_TIME_LIMIT`) so a future change to task limits prompts a
  matching grace-period update. `335s` is deliberately NOT an env var —
  AGENTS.md restricts env vars to secrets, topology, or sizing; this is an
  operational constant.
- Deferred deliberately: deriving both publish and pull image names from one
  source (would require Jinja in a `_copy_without_render` workflow or a
  compose-side env indirection — complexity not worth it while repo name =
  slug is documented).
