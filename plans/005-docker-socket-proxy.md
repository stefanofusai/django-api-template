# Plan 005: Isolate Traefik from the Docker daemon socket

> **Executor instructions**: Follow every step, verification, and STOP
> condition. Update `plans/README.md` when complete.
>
> **Drift check (run first)**: `rtk git diff --stat b367191..HEAD -- '{{cookiecutter.project_slug}}/.docker/compose/prod.yaml' '{{cookiecutter.project_slug}}/.github/scripts/docker-smoke.sh' '.github/workflows/ci.yaml' '{{cookiecutter.project_slug}}/README.md'`

## Status

- **Priority**: P1
- **Effort**: M
- **Risk**: MED
- **Depends on**: 003
- **Category**: security
- **Planned at**: commit `b367191`, 2026-07-10

## Why this matters

The internet-facing Traefik container mounts `/var/run/docker.sock` directly.
The `:ro` mount flag does not restrict requests sent through a Unix socket, so
a Traefik compromise can become Docker-daemon and host compromise. Traefik's
own documentation recommends an authorization proxy for this boundary.

## Current state

- `prod.yaml:206` enables the Docker provider.
- `prod.yaml:229` mounts the raw daemon socket into Traefik.
- The provider needs read access to events, container metadata, networks,
  ping, and version; it does not need POST or container lifecycle access.
- `tecnativa/docker-socket-proxy` v0.4.2 is the currently vetted proxy family;
  use its GHCR image with an immutable digest, not `latest`.

## Commands you will need

| Purpose | Command | Expected |
|---|---|---|
| Render Compose | `rtk docker compose -f .docker/compose/prod.yaml --env-file=.env config` | exit 0 |
| Smoke | `rtk docker compose -f .docker/compose/prod.yaml --env-file=.env up -d --build --wait` | routes discovered |
| Inspect mounts | `rtk docker inspect <traefik-container>` | no docker.sock mount |

## Scope

**In scope**:
- `{{cookiecutter.project_slug}}/.docker/compose/prod.yaml`
- `{{cookiecutter.project_slug}}/.github/scripts/docker-smoke.sh`
- `.github/workflows/ci.yaml`
- `{{cookiecutter.project_slug}}/README.md`
- image-pin consistency tests if required

**Out of scope**:
- Exposing the proxy port on the host.
- Enabling Docker POST, secrets, exec, auth, or lifecycle APIs.
- Swarm/Kubernetes support.

## Git workflow

Do not commit or push unless explicitly requested.

Start from the approved Plan 003 versions of `prod.yaml`, root `ci.yaml`, and
the generated README so the private readiness boundary remains intact while
this plan changes the same surfaces.

## Steps

### Step 1: Add the restricted proxy service

For `use_traefik=yes`, add a private `docker-socket-proxy` service using the
GHCR v0.4.2 image pinned by immutable digest. Mount the Docker socket only
there. Permit GET/HEAD plus the minimum read sections Traefik needs
(`CONTAINERS`, `EVENTS`, `NETWORKS`, `PING`, `VERSION`); explicitly keep `POST`
and all unrelated sections disabled. Put Traefik and the proxy on a dedicated
internal network.

**Verify**: rendered Compose shows no published proxy port and no raw socket
mount on Traefik.

### Step 2: Point Traefik at the proxy

Add `--providers.docker.endpoint=tcp://docker-socket-proxy:2375` and a healthy
dependency on the proxy. Keep `exposedbydefault=false`. Do not add TLS because
the network is Compose-internal and never published.

**Verify**: Traefik starts, discovers the API labels, and `/api/health` routes.

### Step 3: Test denied API surface

Extend smoke CI to assert Traefik has no socket mount, a permitted Docker
metadata request through the proxy succeeds, and a POST/lifecycle request
returns 403. Do not include a runnable host-compromise demonstration.

**Verify**: default production smoke passes and the denial assertion is green.

### Step 4: Document and pin maintenance

Explain the trust boundary and add the proxy image to Dependabot/invariant
coverage. Record which API sections Traefik requires so future additions are
reviewable.

**Verify**: pre-commit and all Docker smoke variants pass.

## Test plan

Test service discovery, socket-mount absence, unexposed proxy networking, a
permitted read endpoint, and a denied mutation endpoint.

## Done criteria

- [ ] Traefik cannot open the host Docker socket directly.
- [ ] Docker POST and sensitive API groups are denied.
- [ ] Route discovery and production smoke still work.
- [ ] Proxy image is version/digest pinned and tracked.

## STOP conditions

- Traefik requires a Docker API group not listed above; capture the exact GET
  endpoint before granting it.
- The proxy image lacks a multi-architecture digest required by supported hosts.
- Compose networking would expose port 2375 outside the private network.

## Maintenance notes

Never broaden proxy permissions to fix an unexplained 403. Identify the exact
read endpoint and document why Traefik needs it.
