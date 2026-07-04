# Plan 002: Harden the production deploy path (liveness split, healthcheck traps, proxy contract, boot guards, Redis durability)

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving to the
> next step. If anything in the "STOP conditions" section occurs, stop and
> report — do not improvise. When done, update the status row for this plan
> in `plans/README.md` — unless a reviewer dispatched you and told you they
> maintain the index.
>
> **Drift check (run first)**: `git diff --stat 924bfba..HEAD -- '{{cookiecutter.project_slug}}/src/apps/api/' '{{cookiecutter.project_slug}}/src/config/settings/environments/prod.py' '{{cookiecutter.project_slug}}/.docker/' '{{cookiecutter.project_slug}}/.env.example' '{{cookiecutter.project_slug}}/README.md' '{{cookiecutter.project_slug}}/tests/'`
> If any in-scope file changed since this plan was written, compare the
> "Current state" excerpts against the live code before proceeding; on a
> mismatch, treat it as a STOP condition.

## Status

- **Priority**: P1
- **Effort**: M
- **Risk**: MED (touches container orchestration behavior; every change has a verification step)
- **Depends on**: none (001 recommended first so new code is honestly measured)
- **Category**: security / bug
- **Planned at**: commit `924bfba`, 2026-07-04

## Why this matters

The prod compose stack has verified first-deploy traps:

1. **Healthcheck vs ALLOWED_HOSTS**: the container healthcheck curls
   `http://127.0.0.1:8000/api/ready`, sending `Host: 127.0.0.1`. The moment an
   operator sets `ALLOWED_HOSTS=api.example.com` (as they should), Django
   returns 400 `DisallowedHost`, the api container goes unhealthy, and the
   worker — which `depends_on: api: service_healthy` — **never starts**.
2. **No liveness/readiness split**: the only probe is `/api/ready`, which does
   real DB + cache I/O. A transient DB blip marks the *container* unhealthy
   and gets a perfectly healthy process restarted. Liveness ("process is up")
   and readiness ("dependencies are up") need separate endpoints.
3. **Spoofable HTTPS detection**: `SECURE_PROXY_SSL_HEADER` makes Django trust
   `X-Forwarded-Proto`. Verified against gunicorn 26 source: gunicorn passes
   that header through to the WSGI environ even from peers **not** in
   `forwarded-allow-ips` (the allowlist only gates `wsgi.url_scheme`). No
   proxy ships in the stack to strip client-supplied values, and the required
   proxy contract is undocumented. Gunicorn natively honors a
   `FORWARDED_ALLOW_IPS` env var, so wiring is documentation + env, not code.
4. **Placeholder SECRET_KEY has no boot guard**: `.env.example` ships a
   `django-insecure-`-prefixed key; README says `cp .env.example .env`; CI's
   `check --deploy` runs with a *different* key so it cannot catch it.
5. **Healthcheck overhead**: every healthcheck in both compose files fires
   every 5s forever with no `start_period`; the worker probe cold-starts a
   full Django+Celery process per ping (~17k/day).
6. **Redis durability**: the broker/cache Redis runs with default RDB-only
   persistence; queued Celery tasks can be lost on a crash.

## Important context: this is a cookiecutter template

- Project code lives under the literal directory
  `{{cookiecutter.project_slug}}/` — always quote this path in shell commands.
- Files may contain Jinja placeholders (`{{ cookiecutter.* }}`) — preserve
  them verbatim.
- Verification happens by baking a project (`uvx cookiecutter . --no-input -o
  <dir>`) and running its suite; full-stack behavior additionally needs
  `docker compose` locally.

## Current state

- `{{cookiecutter.project_slug}}/src/apps/api/routes/ready.py` — readiness
  endpoint doing `cache.set/get` + `connections["default"].ensure_connection()`.
  Routes are declared like:

  ```python
  router = Router(tags=["ready"])

  @router.get("/ready", response={200: ReadyOkSchema, 503: ReadyErrorSchema})
  def ready(
      request: HttpRequest,  # noqa: ARG001
  ) -> Status[ReadyOkSchema] | Status[ReadyErrorSchema]:
  ```

- `{{cookiecutter.project_slug}}/src/apps/api/routes/__init__.py`:

  ```python
  from .ready import router as ready_router

  __all__ = ["ready_router"]
  ```

- `{{cookiecutter.project_slug}}/src/apps/api/api.py:8` — `api.add_router("", ready_router)`
- `{{cookiecutter.project_slug}}/src/apps/api/schemas/ready.py` — `ReadyOkSchema`
  is `status: Literal["ok"]`; schemas re-exported from `schemas/__init__.py`
  with an `__all__` list (alphabetical).
- `{{cookiecutter.project_slug}}/src/config/settings/environments/prod.py:15-17`:

  ```python
  SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
  SECURE_REDIRECT_EXEMPT = [r"^api/ready$"]
  SECURE_SSL_REDIRECT = True
  ```

  (Note: `SECURE_REDIRECT_EXEMPT` patterns match `request.path.lstrip("/")` —
  the existing no-leading-slash form is correct; mirror it.)

- `{{cookiecutter.project_slug}}/src/config/settings/components/core.py:6` —
  `SECRET_KEY = env("SECRET_KEY")`.
- `{{cookiecutter.project_slug}}/.env.example:22` — placeholder key with the
  `django-insecure-` prefix (do not copy its value anywhere).
- `{{cookiecutter.project_slug}}/.docker/compose/prod.yaml` — api healthcheck:

  ```yaml
  healthcheck:
    test:
      - CMD
      - curl
      - -fsS
      - -o
      - /dev/null
      - http://127.0.0.1:8000/api/ready
    interval: 5s
    timeout: 5s
    retries: 5
  ```

  Same shape in `dev.yaml`; worker healthcheck is
  `celery -A config inspect ping --destination=worker@$$HOSTNAME --timeout=5`
  (CMD-SHELL, `$$` is compose escaping — preserve); redis service:

  ```yaml
  redis:
    healthcheck: [...]
    image: redis:8.8.0
    volumes:
      - redis_data:/data
  ```

- `{{cookiecutter.project_slug}}/.docker/scripts/gunicorn.sh` — no
  forwarded-allow-ips flag (gunicorn 26 default `127.0.0.1,::1`, overridable
  via the `FORWARDED_ALLOW_IPS` env var, verified in gunicorn's `config.py`).
- README (`{{cookiecutter.project_slug}}/README.md`) has no Production
  section; `prod.yaml` is never mentioned. The prod api service publishes no
  ports (bring-your-own ingress — deliberate but undocumented).
- Conventions: AGENTS.md — routes resource-oriented; curl healthchecks use
  `-fsS -o /dev/null`; alphabetical ordering of list items/env vars; tests
  named `test_<subject>_<expected>_when_<condition>`; `# Utils` section for
  private helpers.

## Commands you will need

| Purpose | Command | Expected on success |
|---------|---------|---------------------|
| Bake | `uvx cookiecutter . --no-input -o $BAKE` | exit 0 |
| Tests | `cd $BAKE/my-project && uv run pytest` | all pass, 100% |
| Hooks | `cd $BAKE/my-project && git add -A && uv run pre-commit run --all-files` | all pass |
| Stack (local, needs Docker) | `cd $BAKE/my-project && cp .env.example .env && docker compose -f .docker/compose/dev.yaml up -d --wait` | exits 0, all services healthy |
| Stack teardown | `docker compose -f .docker/compose/dev.yaml down -v` | exit 0 |

## Scope

**In scope**:
- `{{cookiecutter.project_slug}}/src/apps/api/routes/health.py` (create)
- `{{cookiecutter.project_slug}}/src/apps/api/routes/__init__.py`
- `{{cookiecutter.project_slug}}/src/apps/api/schemas/health.py` (create)
- `{{cookiecutter.project_slug}}/src/apps/api/schemas/__init__.py`
- `{{cookiecutter.project_slug}}/src/apps/api/api.py`
- `{{cookiecutter.project_slug}}/src/config/settings/environments/prod.py`
- `{{cookiecutter.project_slug}}/.docker/compose/dev.yaml` and `prod.yaml`
- `{{cookiecutter.project_slug}}/.env.example`
- `{{cookiecutter.project_slug}}/README.md`
- `{{cookiecutter.project_slug}}/tests/integration/api/health_test.py` (create)

**Out of scope**:
- `gunicorn.sh` — no flag changes; `FORWARDED_ALLOW_IPS` works as an env var.
- Adding a reverse proxy service — decided tradeoff (bring your own ingress).
- CORS and throttling — explicitly rejected by the maintainer.
- The `/api/ready` endpoint logic itself.

## Git workflow

- Branch: `advisor/002-prod-deploy-hardening`
- Conventional commits, e.g. `feat: add liveness endpoint and harden prod deploy path`
- Do NOT push or open a PR unless the operator instructed it.

## Steps

### Step 1: Add the liveness endpoint

Create `{{cookiecutter.project_slug}}/src/apps/api/schemas/health.py`:

```python
from typing import Literal

from ninja import Schema


class HealthOkSchema(Schema):
    status: Literal["ok"]
```

Re-export it from `schemas/__init__.py` (keep `__all__` alphabetical).

Create `{{cookiecutter.project_slug}}/src/apps/api/routes/health.py` —
mirror `ready.py`'s structure, but with **no I/O**:

```python
from django.http import HttpRequest
from ninja import Router, Status

from apps.api.schemas import HealthOkSchema

router = Router(tags=["health"])


@router.get("/health", response={200: HealthOkSchema})
def health(
    request: HttpRequest,  # noqa: ARG001
) -> Status[HealthOkSchema]:
    return Status(200, HealthOkSchema(status="ok"))
```

Export `health_router` from `routes/__init__.py` (alphabetical) and mount it
in `api.py` next to `ready_router`.

**Verify**: bake, `uv run pytest` → fails coverage (new module untested) —
expected until Step 2.

### Step 2: Test the liveness endpoint

Create `tests/integration/api/health_test.py`, modeled on
`tests/integration/api/ready_test.py` (fixture `api_client: TestClient` comes
from `tests/conftest.py`):

```python
from http import HTTPStatus
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ninja.testing import TestClient


def test_health_endpoint_returns_ok_without_touching_dependencies(
    api_client: TestClient,
) -> None:
    response = api_client.get("/health")

    assert response.status_code == HTTPStatus.OK
    assert response.data == {"status": "ok"}
```

No `pytest.mark.django_db` — that is the point: it must pass with no database.

**Verify**: `uv run pytest` in a fresh bake → all pass, 100%.

### Step 3: Exempt /api/health from the SSL redirect and add the SECRET_KEY boot guard

In `src/config/settings/environments/prod.py`:

1. Change `SECURE_REDIRECT_EXEMPT` to cover both probes:

   ```python
   SECURE_REDIRECT_EXEMPT = [r"^api/health$", r"^api/ready$"]
   ```

2. At the top of the file (after the existing imports), add the boot guard.
   `SECRET_KEY` is defined by `components/core.py` in the split-settings
   namespace, so it needs the same suppression pattern the file already uses:

   ```python
   from django.core.exceptions import ImproperlyConfigured

   if SECRET_KEY.startswith("django-insecure-"):  # noqa: F821  # ty: ignore[unresolved-reference]
       msg = "SECRET_KEY must be replaced with a securely generated value in production."
       raise ImproperlyConfigured(msg)
   ```

**Verify** in a fresh bake (quote paths; run from the baked project root):

```
env DJANGO_ENV=prod ALLOWED_HOSTS=example.com AWS_STORAGE_BUCKET_NAME=b \
  CACHE_URL=locmemcache:// CSRF_TRUSTED_ORIGINS=https://example.com \
  DATABASE_URL=sqlite:///:memory: SECRET_KEY=django-insecure-nope \
  uv run python manage.py check
```
→ fails with `ImproperlyConfigured`. Re-run with `SECRET_KEY=some-long-random-value`
→ exits 0.

### Step 4: Point container healthchecks at /api/health, add start_period, relax intervals

In **both** `dev.yaml` and `prod.yaml`:

- api service: healthcheck URL → `http://127.0.0.1:8000/api/health`; set
  `interval: 30s`, `timeout: 5s`, `retries: 3`, `start_period: 30s`,
  `start_interval: 2s`.
- postgres and redis: keep their tests; set `interval: 30s`,
  `start_period: 10s`, `start_interval: 2s` (keep `timeout: 5s`, `retries: 5`
  or tighten to 3 — pick one and apply consistently).
- worker: keep the celery ping test verbatim (including `$$HOSTNAME`); set
  `interval: 60s`, `timeout: 10s`, `retries: 3`, `start_period: 30s`,
  `start_interval: 5s`.

`start_interval` requires Docker Engine ≥ 25 / Compose ≥ 2.30 — the same
floor the existing `pre_start` hooks already require, so no new requirement.
Note the semantics preserved: api's healthcheck still implies "migrations
completed" for the worker, because `pre_start` blocks the api container's
start until `migrations.sh` exits.

**Verify**: `docker compose -f .docker/compose/dev.yaml config` (in the baked
project, after `cp .env.example .env`) → renders without errors and shows the
new values. If Docker is available: `docker compose -f .docker/compose/dev.yaml
up -d --wait` → all services healthy; then
`curl -fsS http://localhost:8000/api/health` → `{"status": "ok"}`;
`curl -fsS http://localhost:8000/api/ready` → `{"status": "ok"}`; tear down
with `down -v`.

### Step 5: Redis durability + FORWARDED_ALLOW_IPS + ALLOWED_HOSTS notes

1. In both compose files, give redis an explicit append-only config:

   ```yaml
   redis:
     command:
       - redis-server
       - --appendonly
       - "yes"
   ```

   (Keep every other key of the service unchanged.)

2. In `.env.example`, add two commented lines (commented = optional, matching
   the existing AWS pattern; the file is sorted by the `file-contents-sorter`
   pre-commit hook — insert in byte-sort order, `#` lines sort first):

   ```
   # FORWARDED_ALLOW_IPS=
   ```

   and a comment above/beside ALLOWED_HOSTS is not possible (sorter) — so the
   127.0.0.1 requirement is documented in the README instead (next step).

**Verify**: bake; `git add -A && uv run pre-commit run --all-files` → the
`file-contents-sorter` hook does not modify `.env.example` (i.e., you placed
the line in sorted position).

### Step 6: Write the Production section of the README

Append a `## Production` section to `{{cookiecutter.project_slug}}/README.md`
(before `## Testing`), covering exactly these points — keep the file's plain,
imperative tone:

- Start command: `docker compose -f .docker/compose/prod.yaml up -d --wait`.
- The `api` service publishes **no ports**: production expects your own
  ingress/reverse proxy in front. The proxy MUST terminate TLS, set
  `X-Forwarded-Proto: https` on forwarded requests, and **strip or overwrite**
  any client-supplied `X-Forwarded-Proto`; set `FORWARDED_ALLOW_IPS` to the
  proxy's address so Gunicorn trusts it. Without such a proxy,
  `SECURE_PROXY_SSL_HEADER` is unsafe and `SECURE_SSL_REDIRECT` will loop.
- Before deploying, generate real secrets: a fresh `SECRET_KEY`
  (`uv run python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"`)
  and a strong `POSTGRES_PASSWORD`; the prod stack reads the same `.env` file
  as dev. The prod boot refuses `django-insecure-` keys.
- Keep `127.0.0.1` in `ALLOWED_HOSTS` alongside your domain — the container
  healthcheck probes over localhost.
- `/api/health` is liveness (process up, used by the container healthcheck);
  `/api/ready` is readiness (DB + cache reachable, for load-balancer routing).
- Redis runs append-only for broker durability; cache and broker share one
  instance (databases 0/1) — under memory pressure Redis's default
  `noeviction` policy rejects writes rather than evicting, which also blocks
  task enqueues; split instances if cache volume grows.
- The admin at `/admin/` is exposed wherever the api is routed — restrict it
  at the proxy (IP allowlist) or route only `/api/` publicly.

Also update `## Quickstart` requirements: "Docker with Compose lifecycle hook
support" → "Docker Compose ≥ 2.30 (lifecycle hooks and start_interval)".

**Verify**: `uv run pre-commit run markdownlint --all-files` in the baked
project → passes.

### Step 7: Full verification loop

**Verify**:
- Fresh bake → `uv run pytest` → all pass, 100%
- `git add -A && uv run pre-commit run --all-files` → all pass
- If Docker available: dev stack `up -d --wait` → healthy; `down -v`.

## Test plan

- New: `tests/integration/api/health_test.py` (one test, no DB marker) —
  pattern: `ready_test.py`.
- The SECRET_KEY guard is verified by the Step 3 `manage.py check` runs (it
  lives in `prod.py`, which is coverage-omitted per Plan 001 and exercised by
  the CI deploy check — see `tests.yaml`; that CI key does not start with
  `django-insecure-`, so CI stays green).
- Compose changes are verified by `compose config` + (locally) `up -d --wait`,
  and permanently by Plan 013's CI smoke test.

## Done criteria

- [ ] Baked project: `uv run pytest` → all pass, 100% coverage
- [ ] Baked project: `uv run pre-commit run --all-files` → all pass
- [ ] `curl` healthchecks in both compose files reference `/api/health`; every healthcheck has `start_period` and `start_interval`
- [ ] `grep -n 'django-insecure' '{{cookiecutter.project_slug}}/src/config/settings/environments/prod.py'` → the guard is present
- [ ] `manage.py check` with a `django-insecure-` key under `DJANGO_ENV=prod` fails; with a random key passes
- [ ] README has the Production section with the proxy contract and secret-rotation steps
- [ ] No files outside the in-scope list modified (`git status`)
- [ ] `plans/README.md` status row updated

## STOP conditions

Stop and report back if:

- `docker compose config` rejects `start_interval` or the redis `command`
  shape — report the compose version and the error instead of downgrading the
  healthcheck design silently.
- The CI deploy-check workflow (`tests.yaml`) turns out to use a
  `django-insecure-` SECRET_KEY (it should not — verify before assuming).
- Adding the health route breaks `schema_test.py` (schemathesis) in any way
  other than trivially including the new endpoint.
- You are tempted to modify `gunicorn.sh` or add a proxy service — out of
  scope.

## Maintenance notes

- Plan 013 (CI compose smoke test) depends on `/api/health` existing and on
  `up -d --wait` semantics from the healthchecks tuned here.
- Plans 007/009 add more prod-required env vars; they append to the same
  README Production section and `.env.example`.
- If the team later adds an ingress service to prod.yaml, revisit
  `FORWARDED_ALLOW_IPS` guidance (set it to the proxy container's network) and
  consider removing the README warning about missing proxies.
