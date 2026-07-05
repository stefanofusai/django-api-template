# Plan 023: Add `postgres` and `redis` knobs — externally managed backing services

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving to the
> next step. If anything in the "STOP conditions" section occurs, stop and
> report — do not improvise. When done, update the status row for this plan
> in `plans/README.md` — unless a reviewer dispatched you and told you they
> maintain the index.
>
> **Drift check (run first)**: this plan was written at commit `a39b1f3`
> **while plan 022 was still executing** — it targets the POST-022 tree and
> must not start before 022 is DONE and committed. Verify:
>
> 1. `plans/README.md` shows 022 DONE, **and** `git status` is clean for
>    `cookiecutter.json`, `{{cookiecutter.project_slug}}/.docker/compose/prod.yaml`,
>    `{{cookiecutter.project_slug}}/README.md`, `.github/workflows/ci.yaml`
>    (a DONE index row does not prove the diff was committed). If either
>    check fails, STOP.
> 2. `grep -c "use_celery" cookiecutter.json` → 1 (022's knobs exist), and
>    `grep -c "postgres" cookiecutter.json` → 0 (this plan not already
>    applied — if it is, STOP and report).
> 3. The prod.yaml excerpts below (api `depends_on`, `postgres:` service,
>    `redis:` service, top-level volumes) match the live file. Plan 022
>    wrapped OTHER parts of prod.yaml in Jinja (`celery-*` services, traefik
>    labels/service, `traefik_data`/`media_data` volumes) — Jinja around
>    those parts is EXPECTED; the blocks THIS plan touches must match the
>    excerpts modulo surrounding Jinja and comment lines. Any other
>    mismatch is a STOP.

## Status

- **Priority**: P2
- **Effort**: S–M
- **Risk**: LOW–MED (compose-file Jinja nesting; no app-code changes)
- **Depends on**: plan 022 DONE and committed (hard — same files, and this
  plan extends its knob system); must run **before** plan 021 (which
  documents the final knob surface)
- **Category**: direction / dx
- **Planned at**: commit `a39b1f3`, 2026-07-05 (plan 022 in flight)

## Why this matters

Plan 022 made features optional at bake time. This plan does the same for
the two backing services: projects whose production Postgres is managed
(Aurora PostgreSQL, RDS, Neon, Supabase, PlanetScale for Postgres, …)
and/or whose production Redis is managed (ElastiCache, Upstash, Redis
Cloud, managed Valkey, …) currently get a bundled compose service they
must hand-strip — and they can't just ignore it, because the `api`
service's `depends_on` refuses to boot the stack without it. The app code
is already provider-agnostic: `DATABASE_URL`, `CACHE_URL`, and
`CELERY_BROKER_URL` are env-driven. Only the prod compose topology and the
docs are hardwired.

Maintainer decisions already made (do not re-litigate):

- Knobs: `postgres` (compose / external) and `redis` (compose / external),
  defaults `compose` — defaults must render byte-identical to the post-022
  default bake.
- **Production topology only.** The dev compose stack ALWAYS keeps its
  local `postgres` and `redis` services — the self-contained free dev loop
  is a template selling point. `{{cookiecutter.project_slug}}/.docker/compose/dev.yaml`
  is OUT OF SCOPE.
- **Protocol-compatible providers only**: external Postgres must speak the
  Postgres wire protocol (psycopg stays a main dependency in both modes;
  this is not a MySQL door), external Redis must speak the Redis protocol
  (django-redis and celery[redis] stay).
- No dependency changes, no settings changes, no `.env.example` changes,
  no hook changes. `POSTGRES_*` vars keep feeding the dev compose service
  in both modes; the dev-pointing defaults of `DATABASE_URL` / `CACHE_URL`
  / `CELERY_BROKER_URL` stay. Production guidance is README-only.

## Current state

Cookiecutter template repo: project code lives under the literal directory
`{{cookiecutter.project_slug}}/` (quote it in shell); files inside contain
Jinja that must stay valid. Verification = bake
(`uvx cookiecutter . --no-input -o <dir>`) + baked suite (`uv run pytest`,
100% coverage) + baked `git add -A && uv run pre-commit run --all-files`.
Root pre-commit excludes the template dir, so Jinja in template files does
not break root lint. Post-022, `cookiecutter.json` has six knobs
(`use_celery`, `email_provider`, `use_sentry`, `use_s3_media`,
`use_traefik`, `traefik_tls`) between `github_username` and
`_copy_without_render`, and plan 022 established the Jinja conventions
this plan reuses (leading-marker line tags: `{%- if ... %}` / `{%- endif %}`
alone on their lines; string comparisons, never Jinja truthiness).

Facts verified during planning (committed tree at `a39b1f3`):

- `src/config/settings/components/database.py`:
  `DATABASES = {"default": env.db("DATABASE_URL")}` plus
  `CONN_HEALTH_CHECKS`/`CONN_MAX_AGE` (default 60) lines — fully
  URL-driven, no change needed.
- `src/config/settings/components/cache.py`:
  `CACHES = {"default": env.cache("CACHE_URL")}` — URL-driven, no change
  needed. `rediss://` TLS URLs work through the same parser.
- `src/config/settings/components/celery.py:6`:
  `CELERY_BROKER_URL = env("CELERY_BROKER_URL", default="redis://redis:6379/1")`
  — the code default points at the compose service; with external Redis
  the operator MUST set `CELERY_BROKER_URL`. Document; do not change code.
  (When `use_celery=none`, 022 deleted this file — the redis knob then
  only affects the cache.)
- `src/apps/api/routes/ready.py` probes cache and database through Django
  abstractions — works identically against external services; no change.
- `.docker/compose/prod.yaml` (committed `a39b1f3`) — the blocks this plan
  touches:

  ```yaml
    api:
      ...
      depends_on:
        postgres:
          condition: service_healthy
        redis:
          condition: service_healthy
      ...
    postgres:
      env_file:
        - ../../.env
      healthcheck:
        test:
          - CMD-SHELL
          - pg_isready --dbname="$${POSTGRES_DB}" --username="$${POSTGRES_USER}"
        interval: 30s
        timeout: 5s
        retries: 3
        start_period: 10s
        start_interval: 2s
      image: postgres:18.4
      restart: unless-stopped
      volumes:
        - postgres_data:/var/lib/postgresql
    redis:
      command:
        - redis-server
        - --appendonly
        - "yes"
      healthcheck:
        test:
          - CMD
          - redis-cli
          - ping
        interval: 30s
        timeout: 5s
        retries: 3
        start_period: 10s
        start_interval: 2s
      image: redis:8.8.0
      restart: unless-stopped
      volumes:
        - redis_data:/data
  volumes:
    postgres_data:
    redis_data:
    traefik_data:
  ```

  (Post-022, `traefik_data:` is wrapped in a `use_traefik`/`traefik_tls`
  conditional and a `media_data:` conditional may exist — leave 022's
  wrapping exactly as you find it. Image pins may have moved — keep
  whatever is live.)
- The `celery-worker`/`celery-beat` services depend only on `api` — no
  change needed there.
- Baked `README.md` Production section (post-018/016, committed): contains
  a paragraph on generating secrets that mentions "set a strong
  `POSTGRES_PASSWORD`"; a paragraph "Persistent database connections
  default to 60 seconds with health checks. Set `CONN_MAX_AGE=0` when
  running behind PgBouncer in transaction mode."; and a Redis paragraph
  "Redis runs append-only for broker durability. Cache and broker share
  one Redis instance on databases 0 and 1. Under memory pressure, Redis's
  default `noeviction` policy rejects writes instead of evicting keys,
  which also blocks task enqueues. Split Redis instances if cache volume
  grows." Post-022 these may carry celery/knob conditionals — re-read the
  live file and layer, don't clobber.
- Root `.github/workflows/ci.yaml` post-022 has a `bake` job matrix
  (project-name entries plus knob-variant entries with `extra-args`), a
  `bake-invalid` job, `docker-build`, `docker-compose-smoke` (matrix:
  default + minimal), and `pre-commit`. The smoke variants boot the real
  prod stack — they MUST keep `postgres=compose redis=compose` (an
  external-mode stack cannot self-boot in CI: the api `pre_start`
  migrations would have no database).

## Commands you will need

| Purpose | Command | Expected on success |
|---|---|---|
| Baseline bake (post-022, pre-023) | `uvx cookiecutter . --no-input -o /tmp/ext/baseline` | exit 0 |
| Bake a variant | `uvx cookiecutter . --no-input -o /tmp/ext/<name> postgres=external ...` | exit 0 |
| Baked tests | `uv run pytest` (inside bake) | all pass, 100% coverage |
| Baked lint | `git add -A && uv run pre-commit run --all-files` (inside bake) | exit 0 |
| Compose parse | `docker compose -f .docker/compose/prod.yaml config` (inside bake) | exit 0 (interpolation warnings OK) |
| Invariance gate | `diff -r --exclude=.git --exclude=uv.lock /tmp/ext/baseline/my-project /tmp/ext/default/my-project` | no output |
| Leftover-Jinja gate | `grep -rn "cookiecutter\|{%-" <bake> --exclude-dir=.git --exclude-dir=.agents` | no matches |
| Root lint | `uvx pre-commit run --all-files` (repo root) | exit 0 |

Bake the baseline BEFORE your first edit.

## Scope

**In scope** (the only files you may modify):

- `cookiecutter.json` (two new knob entries)
- `{{cookiecutter.project_slug}}/.docker/compose/prod.yaml`
- `{{cookiecutter.project_slug}}/README.md` (Production + Local Setup
  wording, conditional)
- `README.md` (root — two Variables rows)
- `.github/workflows/ci.yaml` (root — bake-matrix entries only)
- `plans/README.md` (status row)

**Out of scope** (do NOT touch):

- `{{cookiecutter.project_slug}}/.docker/compose/dev.yaml` — dev always
  ships local postgres+redis.
- `.env.example`, `pyproject.toml`, `hooks/*`, any `src/` or `tests/`
  file, the Dockerfile, `.github/scripts/deploy-check.sh` — the app layer
  is already env-driven; its CI dummies use sqlite/locmem and are
  unaffected.
- The `docker-compose-smoke` job's variants — external modes must NOT be
  added there (see Current state).
- `plans/022-*.md` — do not edit another plan.

## Git workflow

- Branch: `advisor/023-external-backing-services`
- Conventional commits (e.g. `feat: add external backing-service knobs`).
- Do NOT push or open a PR unless the operator instructed it.

## Steps

### Step 0: Preconditions and baseline

Run the drift check from the header. Bake the baseline
(`/tmp/ext/baseline`) and confirm inside it: `uv sync --locked`,
`uv run pytest` → 100%.

### Step 1: Knob entries

In `cookiecutter.json`, append after 022's `traefik_tls` entry (first
element = default):

```json
    "postgres": ["compose", "external"],
    "redis": ["compose", "external"],
```

**Verify**: default bake → invariance gate passes;
`uvx cookiecutter . --no-input -o /tmp/ext/bad postgres=bogus` → non-zero
exit, no project directory created.

### Step 2: prod.yaml topology conditionals

All in `{{cookiecutter.project_slug}}/.docker/compose/prod.yaml`, using
022's line-tag convention. Conditions: compose-postgres ≙
`cookiecutter.postgres == "compose"`, compose-redis ≙
`cookiecutter.redis == "compose"`.

1. `api` service `depends_on` — the key itself must disappear when BOTH
   are external (an empty `depends_on:` mapping is invalid):

   ```text
   {%- if cookiecutter.postgres == "compose" or cookiecutter.redis == "compose" %}
       depends_on:
   {%- if cookiecutter.postgres == "compose" %}
         postgres:
           condition: service_healthy
   {%- endif %}
   {%- if cookiecutter.redis == "compose" %}
         redis:
           condition: service_healthy
   {%- endif %}
   {%- endif %}
   ```

2. Wrap the whole `postgres:` service block in compose-postgres.
3. Wrap the whole `redis:` service block in compose-redis.
4. Top-level volumes: wrap `postgres_data:` in compose-postgres and
   `redis_data:` in compose-redis — leave 022's wrapping of
   `traefik_data:`/`media_data:` untouched. Then guard the `volumes:` key
   itself against rendering empty: it must appear only when at least one
   volume line renders. Wrap it as:

   ```text
   {%- if cookiecutter.postgres == "compose" or cookiecutter.redis == "compose" or cookiecutter.use_traefik == "yes" or cookiecutter.use_s3_media == "no" %}
   volumes:
   {%- endif %}
   ```

   IMPORTANT: derive the exact condition from the LIVE post-022 file —
   list every volume entry present and OR together the conditions under
   which each renders (at planning time: `postgres_data` ⇔ compose-
   postgres, `redis_data` ⇔ compose-redis, `traefik_data` ⇔ traefik with
   letsencrypt, `media_data` ⇔ `use_s3_media == "no"`; 022 may have
   shaped traefik_data's condition as traefik+letsencrypt — mirror what
   you find). If the conditions you derive differ from the example above,
   use the derived ones.

**Verify** (each bake: `uv sync --locked && uv run pytest` → 100%;
`git add -A && uv run pre-commit run --all-files` → exit 0; compose parse
→ exit 0; leftover-Jinja gate → clean):

1. Default bake → invariance gate.
2. `postgres=external` → `grep -n "postgres" .docker/compose/prod.yaml` →
   0 matches; `grep -c "postgres" .docker/compose/dev.yaml` → ≥ 1 (dev
   untouched); `grep -n "redis:" .docker/compose/prod.yaml` → the service
   still present.
3. `redis=external` → `grep -n "redis" .docker/compose/prod.yaml` → 0
   matches; postgres service still present.
4. `postgres=external redis=external use_traefik=no` →
   `grep -cn "^volumes:" .docker/compose/prod.yaml` → 0 when no volume
   entry survives (with `use_s3_media` at its default `yes`);
   `grep -n "depends_on" .docker/compose/prod.yaml` → no match inside the
   api service (celery services, if present, keep theirs); compose parse
   → exit 0.

### Step 3: Baked README conditionals

Re-read the LIVE `{{cookiecutter.project_slug}}/README.md` first — 022
added knob conditionals; layer these inside/alongside them without
clobbering.

1. Production section, database guidance:
   - compose-postgres branch: keep today's text (strong
     `POSTGRES_PASSWORD` note; the existing `CONN_MAX_AGE=0`/PgBouncer
     sentence stays in BOTH branches — extend it in the external branch,
     don't duplicate it).
   - external branch (replaces the `POSTGRES_PASSWORD` sentence): set
     `DATABASE_URL` to the provider endpoint and append `?sslmode=require`
     (or the provider's stricter instructions — `verify-full` plus a CA
     bundle where supported); the `POSTGRES_*` variables only feed the
     LOCAL dev compose stack and are ignored in production; the provider
     owns backups, HA, and upgrades; when connecting through a
     transaction-mode pooler (RDS Proxy, PgBouncer, Neon's pooled
     endpoint) set `CONN_MAX_AGE=0`.
2. Production section, Redis paragraph:
   - compose-redis branch: today's append-only/`noeviction`/split-
     instances paragraph.
   - external branch: set `CACHE_URL` (and `CELERY_BROKER_URL`, only
     inside 022's celery-on conditional) to the provider's TLS endpoint —
     `CACHE_URL=rediss://:<password>@<host>:<port>/0` and
     `CELERY_BROKER_URL=rediss://:<password>@<host>:<port>/1?ssl_cert_reqs=required`
     (celery requires the `ssl_cert_reqs` parameter on `rediss://`
     brokers); the broker database must use a `noeviction` policy at the
     provider or task enqueues can be silently dropped under memory
     pressure; keep cache and broker on separate databases (or separate
     instances) as with the bundled setup.
3. Local Setup: the sentence stating the dev stack runs local
   PostgreSQL/Redis containers is TRUE in all modes — leave it
   unconditional. If any sentence claims the PRODUCTION stack includes
   postgres/redis, wrap it in the matching compose-mode condition.

**Verify**: default bake → invariance gate; `postgres=external` bake →
`grep -in "sslmode" README.md` → ≥ 1 match, `grep -in "POSTGRES_PASSWORD" README.md`
→ only the dev-stack mention (if any); `redis=external` bake →
`grep -in "rediss://" README.md` → ≥ 1, `grep -in "append-only\|appendonly" README.md`
→ 0.

### Step 4: Root README + CI lanes

1. Root `README.md` Variables table: add two rows — `postgres` (default
   `compose`; "run production Postgres as a bundled compose service, or
   point DATABASE_URL at an external/managed Postgres-compatible
   database") and `redis` (default `compose`; same shape for
   CACHE_URL/CELERY_BROKER_URL and Redis-protocol providers). Keep the
   table consistent with 022's six knob rows.
2. Root `.github/workflows/ci.yaml` `bake` job matrix: add two entries
   (match the post-022 entry shape exactly):
   - `external-postgres`: `extra-args: postgres=external`, slug
     `my-project`.
   - `external-backing`: `extra-args: postgres=external redis=external use_traefik=no`,
     slug `my-project` (this lane exercises the empty-`depends_on` and
     empty-`volumes` edge).
   Do NOT touch the `docker-compose-smoke` job.

**Verify**: root `uvx pre-commit run --all-files` → exit 0 (actionlint,
yamllint, markdownlint).

### Step 5: Full sweep + index

| # | extra-args | pytest | pre-commit | compose config | Jinja grep |
|---|---|---|---|---|---|
| 1 | (default) + invariance gate | ✔ | ✔ | ✔ | ✔ |
| 2 | `postgres=external` | ✔ | ✔ | ✔ | ✔ |
| 3 | `redis=external` | ✔ | ✔ | ✔ | ✔ |
| 4 | `postgres=external redis=external use_traefik=no` | ✔ | ✔ | ✔ | ✔ |

Then update this plan's row in `plans/README.md`.

## Test plan

No new pytest tests — the app layer is untouched and each variant's baked
suite (100% coverage) plus the two new CI bake lanes are the regression
net. The compose-parse checks are the topology gate.

## Done criteria

- [ ] Default bake byte-identical to the pre-023 baseline (excluding
      `.git`/`uv.lock`).
- [ ] All four sweep variants pass pytest/pre-commit/compose-parse/Jinja
      grep; variant 4 renders no api `depends_on` and no empty top-level
      `volumes:` key.
- [ ] `dev.yaml` is bit-identical in every variant (`git diff` shows no
      change to it; every bake contains its postgres and redis services).
- [ ] `postgres=bogus` bake fails with non-zero exit.
- [ ] Root README Variables table has 14 rows' worth of variables (6 base
      + 8 knobs); CI matrix has the two new lanes.
- [ ] No files outside Scope modified (`git status`).
- [ ] `plans/README.md` row updated.

## STOP conditions

- The header drift check fails (022 not DONE, not committed, or this plan
  already applied).
- The api `depends_on`, `postgres:`/`redis:` service blocks, or top-level
  volumes in the live prod.yaml don't match the excerpts (beyond 022's
  documented Jinja and comment lines).
- You cannot derive an empty-safe `volumes:` condition from the live file
  (022 shaped the volume conditionals differently than documented) —
  report what you found.
- Any sweep variant cannot reach 100% coverage or requires touching an
  out-of-scope file.

## Maintenance notes

- **Deferred: external-mode compose smoke.** A CI smoke of
  `postgres=external` would need a host-run "external" Postgres/Redis
  (e.g. `docker run` containers reached via the docker host gateway) and
  `DATABASE_URL`/`CACHE_URL` rewrites in the env-prep step. Add only if
  external-mode compose regressions ever occur; the bake lanes + compose
  parse are the current guards.
- **`CELERY_BROKER_URL` code default** (`redis://redis:6379/1` in
  `components/celery.py`) silently points at a nonexistent host when
  `redis=external` and the operator forgets to set the variable. The
  README documents it; if this bites users, a follow-up could make the
  default bake-time-conditional. Deliberately not done here (no settings
  changes).
- **Plan 021** documents the final knob surface — after this plan, that's
  8 knobs; 021's Variables-table step should count accordingly.
- Any future plan adding a compose volume must extend the empty-safe
  `volumes:` key condition from Step 2.4.
- Knob interactions: `redis=external` + `use_celery != none` is the only
  cross-term (broker URL guidance riding inside celery conditionals in the
  README); variant 3's grep set covers it when celery defaults on.
