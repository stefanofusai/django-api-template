# Plan 003: Make readiness bounded, private, and authoritative for routing

> **Executor instructions**: Follow the steps in order; update the index on
> completion. Do not improvise past a STOP condition.
>
> **Drift check (run first)**: `rtk git diff --stat 20ec7c5..HEAD -- '{{cookiecutter.project_slug}}/src/apps/api/routes/ready.py' '{{cookiecutter.project_slug}}/src/config/settings/components/cache.py' '{{cookiecutter.project_slug}}/.docker/compose/prod.yaml' '{{cookiecutter.project_slug}}/.docker/scripts/deploy.sh' '{{cookiecutter.project_slug}}/tests/api/integration/ready_test.py' '.github/workflows/ci.yaml'`

## Status

- **Priority**: P1
- **Effort**: M
- **Risk**: MED
- **Depends on**: none
- **Category**: bug, security
- **Planned at**: commit `20ec7c5`, 2026-07-10

## Why this matters

The documented contract assigns `/api/health` to restart decisions and
`/api/ready` to load-balancer routing. Production Traefik currently checks
health instead, and `deploy.sh` waits only for that liveness result. Readiness
is also publicly reachable and performs cache, broker, and database I/O; cache
operations have no explicit network timeout. The result is both false-positive
deploy success and an avoidable public resource-amplification endpoint.

## Current state

- `prod.yaml:64-67` points Traefik's backend health check at `/api/health`.
- `deploy.sh:59-63` pulls, rolls out, and waits without probing readiness.
- `ready.py:24-36` reports named failing subsystems.
- `cache.py` accepts `CACHE_URL` without Redis connect/read timeouts.
- Keep the Docker container healthcheck on `/api/health`; dependency outages
  must not cause restart loops.
- Docker Desktop rewrites host requests through published ports to a non-loopback
  gateway source address inside Traefik. Do not authorize that unstable address
  or any hard-coded Compose subnet.

## Commands you will need

| Purpose | Command | Expected |
|---|---|---|
| Unit/integration | `rtk uv run pytest tests/api tests/config -q` | pass |
| Compose smoke | `rtk docker compose -f .docker/compose/prod.yaml --env-file=.env up -d --build --wait` | services healthy |
| Local ready probe | `rtk curl -fsS http://127.0.0.1:8082/api/ready` | 200 |
| Public ready probe | `rtk curl -fsS http://localhost/api/ready` | denied |
| Teardown | `rtk docker compose -f .docker/compose/prod.yaml --env-file=.env down -v` | exit 0 |

## Scope

**In scope**:
- `{{cookiecutter.project_slug}}/src/config/settings/components/cache.py`
- `{{cookiecutter.project_slug}}/src/apps/api/routes/ready.py`
- `{{cookiecutter.project_slug}}/.docker/compose/prod.yaml`
- `{{cookiecutter.project_slug}}/.docker/scripts/deploy.sh`
- related ready, prod-settings, deploy-script, and Docker smoke tests/docs

**Out of scope**:
- Changing liveness semantics.
- Adding authentication credentials to health checks.
- Making shared dependency failure restart containers.

## Git workflow

Do not commit or push unless explicitly requested.

## Steps

### Step 1: Add bounded cache configuration tests

Add tests asserting django-redis receives fixed socket connect and read
timeouts and that locmem test/dev cache configurations remain valid. Mock a
cache timeout in `ready_test.py` and assert a prompt 503 rather than an
uncaught exception.

**Verify**: new settings assertions fail before implementation.

### Step 2: Bound Redis cache I/O

After `env.cache`, add `SOCKET_CONNECT_TIMEOUT` and `SOCKET_TIMEOUT` only when
the selected backend is django-redis. Use fixed operational values consistent
with the broker's one-second readiness bound. Do not add empty environment
variables.

**Verify**: ready and settings tests pass for Redis and locmem bakes.

### Step 3: Enforce the routing contract

Keep the Compose container healthcheck on `/api/health`, but change Traefik's
load-balancer health path to `/api/ready`. Keep higher-priority exact-path
routers on the public `web` and `websecure` entrypoints with a loopback-only IP
allow-list so public and Docker-gateway requests are denied before reaching
Django. Add a dedicated `ready` Traefik entrypoint and exact-path router, and
publish that port as fixed host-local `127.0.0.1:8082:8082`. This loopback port,
not source-IP inference inside the container, is the operator access boundary.
Do not attach the public allow-list middleware to the dedicated entrypoint.
Document the behavior for bundled Traefik and BYO ingress separately.

**Verify**: Compose config renders; `127.0.0.1:8082/api/ready` succeeds, the
ordinary public HTTP/HTTPS entrypoints deny `/api/ready`, direct backend health
checks work, and ordinary API paths still route.

### Step 4: Make deploy success require readiness

After Compose `up --wait`, execute a bounded readiness curl inside the API
container. Extend the fake-Docker deploy tests to assert this command is last
and a failing probe makes the deploy nonzero.

**Verify**: deploy tests pass and deliberately failed readiness aborts.

### Step 5: Extend the production smoke gate

Update the root and generated Docker smoke jobs to test public liveness,
host-local readiness on port 8082, public readiness denial, and an ordinary API
route through Traefik.

**Verify**: default and external-backing smoke variants pass.

## Test plan

Cover healthy and failed broker/cache/database, Redis timeouts, locmem safety,
public denial, internal success, unchanged liveness, and deploy failure when
readiness is non-200.

## Done criteria

- [ ] Cache network calls are explicitly bounded.
- [ ] Traefik routes only ready backends while Docker restarts use liveness.
- [ ] Public callers cannot trigger detailed readiness checks through bundled
  Traefik; operators use only the host-loopback readiness port.
- [ ] Deploy exits nonzero when readiness fails.
- [ ] Default and external-backing production smoke tests pass.

## STOP conditions

- The host-loopback readiness port is reachable from a non-loopback host
  interface or requires a platform-dependent subnet exception.
- Traefik cannot distinguish the exact ready route without affecting direct
  backend health checks.
- Cache timeout options break locmem or non-Redis external cache providers.

## Maintenance notes

Review timeout budgets together with Traefik interval/timeout/retry settings.
Readiness may flap during a shared outage; that should remove traffic, not
restart containers. Port 8082 is a fixed operational constant and must remain
bound to host loopback only.
