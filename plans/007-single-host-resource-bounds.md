# Plan 007: Bound container logs and Redis memory on the single-host deploy

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving to the
> next step. If anything in the "STOP conditions" section occurs, stop and
> report — do not improvise. When done, update the status row for this plan
> in `plans/README.md` — unless a reviewer dispatched you and told you they
> maintain the index.
>
> **Drift check (run first)**:
> `git diff --stat d333a73..HEAD -- '{{cookiecutter.project_slug}}/.docker/compose/prod.yaml' '{{cookiecutter.project_slug}}/.env.example' '{{cookiecutter.project_slug}}/README.md'`
> If any in-scope file changed since this plan was written, compare the
> "Current state" excerpts against the live code before proceeding; on a
> mismatch, treat it as a STOP condition. (Plans 004/006 legitimately edit
> `prod.yaml`/README — integrate with their changes.)

## Status

- **Priority**: P2
- **Effort**: S
- **Risk**: LOW (log rotation) / LOW-MED (Redis bound — rejecting cache
  writes at the cap is the documented, intended failure mode)
- **Depends on**: none (serialize with 004/006 on shared files)
- **Category**: security (availability)
- **Planned at**: commit `d333a73`, 2026-07-05

## Why this matters

Two unbounded resources can take down the whole single-host stack:

1. **Container logs.** No service sets a `logging:` policy, so Docker's
   default `json-file` driver grows per-container logs without limit
   under `/var/lib/docker/containers/`. Gunicorn streams access logs to
   stdout (`--access-logfile=-`) and the app writes JSON logs to stdout,
   so a busy or misbehaving service eventually fills the disk — killing
   Postgres along with everything else.
2. **Redis memory.** The compose Redis runs with no `--maxmemory`, so
   cache growth is capped only by host RAM. The README already documents
   the `noeviction` tradeoff (writes are rejected under memory pressure
   rather than evicting broker data) but there is no memory *bound* to
   create that pressure point short of host OOM.

Both fixes are a few compose lines. Explicit per-service memory limits
were considered and are shipped as **documentation only** (a wrong
default limit OOM-kills legitimate workloads; sizing is
deployment-specific).

## Current state

Cookiecutter template; generated project under the literal
`{{cookiecutter.project_slug}}/` directory. Knobs relevant here:
`redis` ∈ `compose` | `external`; `postgres`, `use_celery`,
`use_traefik` gate which services exist.

- `{{cookiecutter.project_slug}}/.docker/compose/prod.yaml` — services
  (each conditionally present): `api`, `celery-beat`, `celery-worker`,
  `postgres`, `redis`, `traefik`. None has a `logging:` key. The Redis
  service:

  ```yaml
  {%- if cookiecutter.redis == "compose" %}
    redis:
      command:
        - redis-server
        - --appendonly
        - "yes"
      healthcheck: ...
      image: redis:8.8.0
      restart: unless-stopped
      volumes:
        - redis_data:/data
  {%- endif %}
  ```

- `{{cookiecutter.project_slug}}/.env.example:44-56` — the
  "Process sizing" block (always present):

  ```text
  # Process sizing
  {%- if cookiecutter.use_celery != "none" %}
  # Celery worker child process count.
  CELERY_WORKER_CONCURRENCY=2
  # Celery worker task recycle limit per child process.
  CELERY_WORKER_MAX_TASKS_PER_CHILD=100
  {%- endif %}
  # Gunicorn graceful shutdown timeout in seconds.
  GUNICORN_GRACEFUL_TIMEOUT=30
  ...
  ```

  Conventions: own-line comments; alphabetized within a block; env vars
  are allowed for "resource sizing" (AGENTS.md).

- Prod compose commands always run with `--env-file=.env`, so `${VAR}`
  interpolation in `prod.yaml` resolves from the root `.env` (this is
  how `${TRAEFIK_DOMAIN}` already works in the labels).

- `{{cookiecutter.project_slug}}/README.md:376-396` — the Redis
  paragraphs (four knob branches) documenting appendonly + `noeviction`.

- `dev.yaml` is deliberately untouched by this plan (dev disks are the
  developer's problem; keeping dev/prod diff small is nice but bounded
  logs matter in prod).

- Compose supports extension fields (`x-*`) and YAML anchors; top-level
  keys must not collide with service names.

## Commands you will need

| Purpose | Command | Expected on success |
|---------|---------|---------------------|
| Bake matrix | default; `use_celery=none email_provider=none use_sentry=no use_s3_media=no use_traefik=no` (minimal); `postgres=external redis=external use_traefik=no` (external-backing) | all bake |
| Render check | `docker compose -f .docker/compose/prod.yaml --env-file=.env config` in each baked project (after `cp .env.example .env`) | valid config; logging on every service |
| Boot smoke | `up -d --build --wait` on the default bake | healthy |
| Redis bound check | `docker compose ... exec redis redis-cli config get maxmemory` | the configured bytes |
| Root pre-commit | `pre-commit run --all-files` | exit 0 |

## Scope

**In scope**:

- `{{cookiecutter.project_slug}}/.docker/compose/prod.yaml`
- `{{cookiecutter.project_slug}}/.env.example` (one entry)
- `{{cookiecutter.project_slug}}/README.md` (Redis paragraphs + one new
  short passage)

**Out of scope** (do NOT touch):

- `dev.yaml`.
- Actual `deploy.resources.limits` values in compose — docs only (see
  Why).
- The `noeviction` policy itself — documented maintainer decision.
- Traefik/gunicorn/celery flags.

## Git workflow

- Work directly on `main`; do not create or switch to a plan branch unless the
  operator explicitly asks.
- Do NOT commit, push, or open a PR unless the operator explicitly instructs it.
- If asked to commit, use a conventional commit such as
  `feat: bound container logs and redis memory in prod`.

## Steps

### Step 1: Add a shared logging policy to prod.yaml

At the top of `prod.yaml` (before `services:`), add:

```yaml
# Bounds json-file logs per container (~50 MB) so a chatty service
# cannot fill the host disk. Sizes are fixed operational constants.
x-default-logging: &default-logging
  driver: json-file
  options:
    max-file: "5"
    max-size: 10m
```

Then add `logging: *default-logging` to EVERY service (`api`,
`celery-beat`, `celery-worker`, `postgres`, `redis`, `traefik`),
respecting each service's alphabetical-ish key ordering (place `logging:`
between `labels:`/`image:` and `ports:`/`pre_start:` consistently with
the surrounding keys). Mind the Jinja conditionals — the anchor is
unconditional (top-level extension fields are ignored by compose even if
no service references them, so it is safe when few services render).

**Verify**: for each of the three bake variants, `docker compose -f
.docker/compose/prod.yaml --env-file=.env config` renders and every
rendered service shows the logging options. (If Docker is unavailable,
`yamllint` each rendered file and grep for `max-size` per service — but
prefer the compose render.)

### Step 2: Bound Redis memory

In the `redis` service command list, append two items after the
appendonly pair:

```yaml
      command:
        - redis-server
        - --appendonly
        - "yes"
        - --maxmemory
        - ${REDIS_MAXMEMORY}
```

And in `.env.example`'s "Process sizing" block, alphabetically after the
`GUNICORN_*` entries, gated on the compose knob:

```text
{%- if cookiecutter.redis == "compose" %}
# Redis memory ceiling; writes are rejected at the cap (noeviction).
REDIS_MAXMEMORY=256mb
{%- endif %}
```

Note: this is compose-file interpolation (like `${TRAEFIK_DOMAIN}`), so
it requires the `--env-file=.env` convention already used by every
documented prod command. The dev compose does not reference the
variable, so dev is unaffected.

**Verify**: default bake, boot the stack, then
`docker compose ... exec redis redis-cli config get maxmemory` →
`268435456`. External-backing bake: `.env.example` has no
`REDIS_MAXMEMORY` and prod.yaml has no redis service.

### Step 3: Update the README

- In each compose-Redis branch of the Redis paragraphs, add one
  sentence: memory is bounded by `REDIS_MAXMEMORY` (default 256mb); at
  the cap Redis rejects writes (`noeviction`), which surfaces as cache
  write errors{% raw %} — and, when Celery is enabled, blocked enqueues
  — {% endraw %}rather than silent eviction or host OOM; raise the value
  or split instances as cache volume grows. (Adapt wording per branch;
  the celery/non-celery branches differ.)
- Add a short "Resource bounds" passage in the Production section (near
  the Redis paragraphs): container logs are capped at ~50 MB per
  container via the compose logging policy; per-service memory limits
  are deliberately NOT set — show a commented example snippet
  (`deploy: resources: limits: memory: …`) and tell the operator to size
  it to their host if they want kernel-enforced caps.

**Verify**: bake default + minimal; rendered README reads correctly in
both; baked pre-commit (markdownlint) passes.

### Step 4: Full verification

Boot smoke on the default bake (`up -d --build --wait`, probe
`/api/health` in-container, `down -v`), plus root
`pre-commit run --all-files` and one baked
`git add -A && uv run pre-commit run --all-files`.

**Verify**: all exit 0.

## Test plan

No pytest changes. Gates: compose `config` render on three knob
variants, the live `redis-cli config get maxmemory` check, and the boot
smoke.

## Done criteria

- [ ] Every rendered prod service (all three bake variants) carries the
      json-file rotation options
- [ ] Live Redis reports maxmemory 268435456 on the default bake
- [ ] `REDIS_MAXMEMORY` present in `.env.example` only when
      `redis=compose`
- [ ] README updated (Redis branches + resource-bounds passage)
- [ ] Root + baked pre-commit exit 0; `git status` clean outside scope
- [ ] `plans/README.md` status row updated

## STOP conditions

- `docker compose config` rejects the `x-default-logging` anchor or the
  interpolated `${REDIS_MAXMEMORY}` in a command list — report the exact
  error (compose version matters) rather than inlining values.
- Any bake variant renders a service without `logging:` and you cannot
  see why — Jinja conditional interaction; report.
- You are tempted to set actual memory limits on services — explicitly
  out of scope here.

## Maintenance notes

- Any NEW service added to `prod.yaml` by a future plan must reference
  `*default-logging` — reviewers should check this.
- `REDIS_MAXMEMORY` sizing guidance lives in the README; if cache and
  broker are ever split into two Redis services, each needs its own
  bound.
- Deferred (recorded in `plans/README.md`): shipped `deploy.resources`
  memory limits keyed to the sizing knobs; a `/metrics` observability
  surface that would make these bounds observable before they bite.
