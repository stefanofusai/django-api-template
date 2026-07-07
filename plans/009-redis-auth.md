# Plan 009: Require a password on the bundled Redis (cache + Celery broker)

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving on.
> **Read the "Design decision" note before writing code.** If anything in
> "STOP conditions" occurs, stop and report — do not improvise. When done,
> update this plan's status row in `plans/README.md` — unless a reviewer
> dispatched you and told you they maintain the index.
>
> **Drift check (run first)**:
> `git diff --stat ae42991..HEAD -- "{{cookiecutter.project_slug}}/.docker/compose/prod.yaml" "{{cookiecutter.project_slug}}/.docker/compose/dev.yaml" "{{cookiecutter.project_slug}}/.env.example" "{{cookiecutter.project_slug}}/README.md"`
> If any changed since this plan was written, compare "Current state" against
> the live files before proceeding; on a mismatch, STOP.

## Status

- **Priority**: P2
- **Effort**: S–M
- **Risk**: MED (touches cache and broker URLs every service reads; a missed consumer breaks boot)
- **Depends on**: none
- **Category**: security (defense-in-depth; internal-only exposure)
- **Planned at**: commit `ae42991`, 2026-07-07

## Repository context (read before anything else)

This is a **Cookiecutter template**. Source is under
`{{cookiecutter.project_slug}}/` — **quote it in shell**. `.docker/*` and
`.env.example` are **rendered** (Jinja allowed). The `redis` knob is
`["compose", "external"]`; the bundled Redis service exists only when
`redis=compose`. Verification means baking
(`uvx cookiecutter . --no-input -o /tmp/bake [key=value …]`) and, ideally, a
local compose boot (needs Docker + Compose ≥ 5.3.0).

## Why this matters

The bundled Postgres has a password (and plan 008 adds a prod guard on it);
the bundled Redis has **no authentication at all**. Any workload with a
foothold on the Compose network — a compromised dependency in the api/worker
container, or any future co-located service — can read/write the cache and,
on Celery bakes, inject or consume task messages, credential-free. Redis
publishes no host port in prod, so this is lateral-movement defense-in-depth
rather than an internet-facing hole — the same severity class as the DB
password, which the template does protect. Adding `--requirepass` closes the
asymmetry at near-zero operational cost.

## Design decision (confirm intent before coding)

This plan defaults `REDIS_PASSWORD` to the underscored project slug in
`.env.example` — the exact convention the Postgres block already uses (dev
works out of the box; production replacement is the operator's documented
job). It does NOT add a prod boot guard for the Redis password; if the
maintainer wants one, that is a follow-up mirroring plan 008. If the
maintainer would rather leave the compose-network-only Redis passwordless as
an accepted trade-off (documented instead), surface that and stop — but note
it would leave the Postgres/Redis posture inconsistent.

## Current state

`{{cookiecutter.project_slug}}/.docker/compose/prod.yaml:156-179` (the redis
service — no `--requirepass`; `dev.yaml` has the same shape):

```yaml
{%- if cookiecutter.redis == "compose" %}
  redis:
    command:
      - redis-server
      - --appendonly
      - "yes"
      - --maxmemory
      - ${REDIS_MAXMEMORY}
    healthcheck:
      test:
        - CMD
        - redis-cli
        - ping
      interval: 30s
      ...
    image: redis:8.8.0
    ...
{%- endif %}
```

`{{cookiecutter.project_slug}}/.env.example:37-42` (passwordless URLs — note
these are NOT gated on the `redis` knob; `redis=external` operators replace
the host):

```
# Django cache URL.
CACHE_URL=rediscache://redis:6379/0
{%- if cookiecutter.use_celery != "none" %}
# Celery broker URL.
CELERY_BROKER_URL=redis://redis:6379/1
{%- endif %}
```

`.env.example:57-60` shows the existing `redis == "compose"`-gated block
(`REDIS_MAXMEMORY`) — the pattern for the new `REDIS_PASSWORD` var. The
Postgres block (lines 22-29) shows the slug-default-password convention:
`{{ cookiecutter.project_slug.replace('-', '_') }}`.

**Conventions**: `.env.example` — comments own-line, alphabetized within each
block, "Empty uncommented values are required in production"; compose files
use extended YAML block style; add env vars only for secrets/topology/sizing
(a password is a secret — this qualifies).

## Commands you will need

| Purpose | Command | Expected |
|---------|---------|----------|
| Bake default | `uvx cookiecutter . --no-input -o /tmp/bake` | rendered files to grep |
| Bake external-redis | `uvx cookiecutter . --no-input -o /tmp/bake-er redis=external` | no redis service; URLs still render |
| Compose config check | `cd /tmp/bake/my-project && cp .env.example .env && docker compose -f .docker/compose/prod.yaml --env-file=.env config` | exit 0, interpolated output shows the requirepass args |
| Boot smoke (if Docker available) | see Step 5 | `/api/ready` 200 |
| Baked tests | `cd /tmp/bake/my-project && DATABASE_URL=postgres://postgres:postgres@localhost:5432/postgres uv run pytest` | 100% cov (tests use locmem cache under ci — unaffected; confirm) |
| Baked + root pre-commit | as in other plans | exit 0 |

## Scope

**In scope**:
- `{{cookiecutter.project_slug}}/.docker/compose/prod.yaml` and `dev.yaml` —
  redis service: add `--requirepass`, fix the healthcheck for auth.
- `{{cookiecutter.project_slug}}/.env.example` — add `REDIS_PASSWORD` (gated
  `redis == "compose"`), embed the password in `CACHE_URL` /
  `CELERY_BROKER_URL`.
- `{{cookiecutter.project_slug}}/README.md` — one line in the Production
  section: replace `REDIS_PASSWORD` before deploy (alongside the
  `POSTGRES_PASSWORD` instruction).

**Out of scope**:
- A prod boot guard on the Redis password (follow-up mirroring plan 008 — note
  it in your report, do not build it here).
- The `redis=external` path beyond keeping its URLs valid (external Redis auth
  is the operator's).
- Any settings-component change — django-environ parses credentials out of the
  URLs; no Python changes should be needed (STOP if that proves false).

## Git workflow

- Work directly on `main`. Do NOT branch/commit/push/PR unless told. If asked
  to commit: Conventional Commits, e.g.
  `feat: require a password on the bundled redis`.

## Steps

### Step 1: Add `REDIS_PASSWORD` to `.env.example`

In the existing `{%- if cookiecutter.redis == "compose" %}` block (next to
`REDIS_MAXMEMORY`, alphabetized), add:

```
# Redis password required by the bundled Compose service.
REDIS_PASSWORD={{ cookiecutter.project_slug.replace('-', '_') }}
```

### Step 2: Embed the credential in the URLs

Redis URLs carry the password as `redis://:PASSWORD@host:port/db` (empty
username, colon, password). The URLs must only embed the bundled service's
password when the bundled service exists, so gate on the knob:

```
# Django cache URL.
{%- if cookiecutter.redis == "compose" %}
CACHE_URL=rediscache://:{{ cookiecutter.project_slug.replace('-', '_') }}@redis:6379/0
{%- else %}
CACHE_URL=rediscache://redis:6379/0
{%- endif %}
```

and the same treatment for `CELERY_BROKER_URL` (which is additionally inside
the existing `use_celery != "none"` gate — nest carefully and re-check the
rendered whitespace in both knob states).

### Step 3: Require the password in both compose files

In `prod.yaml` and `dev.yaml`, extend the redis `command` (keep the existing
arg style — one list item per token):

```yaml
      - --maxmemory
      - ${REDIS_MAXMEMORY}
      - --requirepass
      - ${REDIS_PASSWORD}
```

Fix the healthcheck: `redis-cli ping` fails with `NOAUTH` once requirepass is
on. Use the env-var form (avoids the password appearing in `ps` output the
way `-a` would):

```yaml
    environment:
      REDISCLI_AUTH: ${REDIS_PASSWORD}
    healthcheck:
      test:
        - CMD
        - redis-cli
        - ping
```

(Keep key order within the service alphabetized as the file already does —
`command`, `environment`, `healthcheck`, `image`, …)

**Verify** (after Steps 1-3):
```
uvx cookiecutter . --no-input -o /tmp/bake
grep -c "requirepass" /tmp/bake/my-project/.docker/compose/prod.yaml   # 1
grep -c "requirepass" /tmp/bake/my-project/.docker/compose/dev.yaml    # 1
grep -c "rediscache://:" /tmp/bake/my-project/.env.example             # 1
uvx cookiecutter . --no-input -o /tmp/bake-er redis=external
grep -c "requirepass" /tmp/bake-er/my-project/.docker/compose/prod.yaml || true  # 0 (no redis service at all)
grep -c "rediscache://redis:6379/0" /tmp/bake-er/my-project/.env.example         # 1 (passwordless external placeholder)
cd /tmp/bake/my-project && cp .env.example .env && docker compose -f .docker/compose/prod.yaml --env-file=.env config >/dev/null && echo CONFIG_OK
```
→ counts as annotated; `CONFIG_OK`.

### Step 4: Document it

In `{{cookiecutter.project_slug}}/README.md`'s Production section, alongside
the existing "set a strong `POSTGRES_PASSWORD`" instruction, add
`REDIS_PASSWORD` to the replace-before-deploy list (and mention the password
now lives inside `CACHE_URL`/`CELERY_BROKER_URL` too — all three places must
agree).

**Verify**: root `uvx pre-commit run markdownlint --all-files` exits 0.

### Step 5: Boot smoke (requires Docker + Compose ≥ 5.3.0)

```
cd /tmp/bake/my-project
cp .env.example .env
docker compose -f .docker/compose/prod.yaml --env-file=.env up -d --build --wait --wait-timeout=300 || true
docker compose -f .docker/compose/prod.yaml --env-file=.env exec api curl -fsS http://127.0.0.1:8000/api/ready
docker compose -f .docker/compose/prod.yaml --env-file=.env down -v
```

Before `up`, set the required prod env values the same way
`.github/scripts/deploy-check.sh` / the root `ci.yaml` smoke do (`SECRET_KEY`
via two `uuidgen`s, etc.). **Verify**: `/api/ready` returns 200 — this proves
the app authenticates to Redis through `CACHE_URL` (the ready probe does a
real cache round-trip) and the healthcheck passes under requirepass. If
Docker is unavailable, that is a STOP (the compose-level change cannot be
verified by grep alone).

Also run the baked pytest suite and both pre-commit runs (Commands table) as
regression.

## Test plan

- No new pytest — the test suite runs under `DJANGO_ENV=ci` with a locmem
  cache (confirm: grep `CACHE_URL` in the ci environment/test config) and
  never touches the compose Redis; `AGENTS.md` forbids config-only tests.
- The verification is the bake-grep matrix (Step 3), the `docker compose
  config` interpolation check, and the boot smoke (Step 5) on a default bake
  plus, if celery is available in your default bake, confirming the worker
  container reaches healthy (its broker URL carries the same credential).

## Done criteria

ALL must hold:

- [ ] Default bake: both compose files pass `--requirepass ${REDIS_PASSWORD}` and the healthcheck authenticates via `REDISCLI_AUTH`; `.env.example` has `REDIS_PASSWORD` (slug default) and credentialed `CACHE_URL`/`CELERY_BROKER_URL`.
- [ ] `redis=external` bake: no redis service, passwordless placeholder URLs unchanged.
- [ ] `docker compose config` exits 0 on the default bake.
- [ ] Boot smoke: `/api/ready` 200 with requirepass active; no unhealthy/exited containers; (celery bakes) worker healthy.
- [ ] README lists `REDIS_PASSWORD` in the replace-before-deploy instructions.
- [ ] Baked pytest 100%; baked + root pre-commit exit 0; no out-of-scope files modified.
- [ ] `plans/README.md` status row updated.

## STOP conditions

Stop and report (do not improvise) if:

- The maintainer's intent (password vs. documented passwordless trade-off)
  cannot be confirmed — see Design decision.
- django-environ fails to parse the `rediscache://:pass@host` form for
  `CACHE_URL` (settings change would be needed — out of scope; report the
  parse behavior you observed).
- Docker/Compose is unavailable — the boot smoke cannot run, and grep-only
  verification is insufficient for this change.
- The celery worker cannot authenticate with the same URL credential form
  (broker URL parsing differs — report the exact error).

## Maintenance notes

- **Follow-up candidate**: a prod boot guard rejecting the slug-default
  `REDIS_PASSWORD`, mirroring plan 008's DB-password guard — decide after 008
  lands.
- The password now lives in three `.env` lines (`REDIS_PASSWORD`, `CACHE_URL`,
  `CELERY_BROKER_URL`); a reviewer should confirm the README says they must be
  rotated together.
- If a future knob adds a second Redis consumer, it inherits the credentialed
  URL automatically — nothing else to wire.
