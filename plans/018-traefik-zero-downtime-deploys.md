# Plan 018: Ship Traefik in prod.yaml and standardize zero-downtime deploys on docker-rollout

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving to the
> next step. If anything in the "STOP conditions" section occurs, stop and
> report — do not improvise. When done, update the status row for this plan
> in `plans/README.md` — unless a reviewer dispatched you and told you they
> maintain the index.
>
> **Drift check (run first)**: `git diff --stat 85e9cf8..HEAD -- '{{cookiecutter.project_slug}}/.docker/compose/prod.yaml' '{{cookiecutter.project_slug}}/.env.example' '{{cookiecutter.project_slug}}/README.md' .github/workflows/ci.yaml`
> Plans 007/008/009/013/016 legitimately touch these files — read
> `plans/README.md` status first and reconcile; on a mismatch in the api
> service shape versus "Current state", STOP.

## Status

- **Priority**: P2
- **Effort**: M
- **Risk**: MED (adds a routing hop in front of all prod traffic; every step has an empirical gate, ending in a live rollout rehearsal)
- **Depends on**: 002 (DONE — health endpoint + healthcheck tuning are prerequisites for rollouts). Serialize with 007/009/016 (shared `.env.example`) and adapt to 008 (beat service) / 013 (smoke workflow) if landed.
- **Category**: direction / dx
- **Planned at**: commit `85e9cf8`, 2026-07-04

## Why this matters

**This plan REVERSES a previously recorded tradeoff.** The prod stack was
deliberately "bring your own ingress" (api publishes no ports). The
maintainer has now decided (2026-07-04) to standardize the deployment story
instead: prod.yaml ships a Traefik reverse proxy, and deploys go through
[docker-rollout](https://github.com/wowu/docker-rollout) (v0.13, MIT, a
Docker CLI plugin implementing scale-up → health-gate → drain-old on
Compose).

The problem being solved: plain `docker compose up -d` with a new image
recreates the api container — a 5–30s window where nothing serves. The
existing design already satisfies docker-rollout's requirements *by
accident*: the api service has no `container_name`, publishes no ports, is
stateless in prod, and has a real liveness healthcheck (`/api/health`). What
is missing is (a) a proxy that discovers healthy api containers and
load-balances across them during the overlap window, and (b) a documented,
standardized deploy procedure.

Bonus: this properly closes the audit's `SECURE_PROXY_SSL_HEADER` spoofing
concern — Traefik overwrites client-supplied `X-Forwarded-*` headers by
default, and gunicorn is told to trust its compose-network peer.

## Important context: this is a cookiecutter template

- Project code lives under the literal `{{cookiecutter.project_slug}}/` dir —
  quote it in shell. Preserve Jinja placeholders and the `$$` escapes in
  compose files verbatim.
- Verification = bake + baked suite (no Python changes here, but run it) +
  Docker-based checks (this plan NEEDS local Docker; if unavailable, STOP —
  a routing layer cannot be verified by inspection).

## Critical Compose subtlety (read before editing)

`${VAR}` interpolation in compose files is resolved from the shell
environment and the `.env` located in the **project directory, which
defaults to the directory containing the compose file** —
`.docker/compose/` here, where no `.env` exists. The existing files never
use interpolation (the `$${POSTGRES_DB}` healthchecks are runtime shell
escapes, not interpolation). This plan introduces one interpolated variable
(`${TRAEFIK_DOMAIN}` in a label), so **every documented prod compose command
must carry `--env-file .env`** (run from the project root), and the deploy
recipe standardizes exactly that. Verify with `docker compose --env-file
.env -f .docker/compose/prod.yaml config` — the label must render with the
real domain, with no blank-variable warning.

## Current state

- `{{cookiecutter.project_slug}}/.docker/compose/prod.yaml` at `85e9cf8`:
  services `api`, `postgres`, `redis`, `worker` (alphabetical; `beat` joins
  after Plan 008). The api service: build args prod, `depends_on`
  postgres/redis healthy, `env_file: ../../.env`, `environment: DJANGO_ENV:
  prod`, healthcheck `curl -fsS -o /dev/null http://127.0.0.1:8000/api/health`
  (interval 30s, timeout 5s, retries 3, start_period 30s, start_interval 2s),
  `pre_start` migrations, `restart: unless-stopped`, **no ports, no
  container_name, no labels** — rollout-compatible as-is.
- `{{cookiecutter.project_slug}}/.env.example` — byte-sorted
  (file-contents-sorter hook); contains a commented `# FORWARDED_ALLOW_IPS=`
  line added by Plan 002 (superseded by this plan — removed in Step 3);
  `CSRF_TRUSTED_ORIGINS=https://example.com,...` is the precedent for
  example.com-style deployment values.
- `{{cookiecutter.project_slug}}/README.md` — has a `## Production` section
  (Plan 002) stating the api publishes no ports and an external
  TLS-terminating proxy is required, with `FORWARDED_ALLOW_IPS` guidance.
  This plan rewrites those paragraphs.
- `{{cookiecutter.project_slug}}/src/config/settings/environments/prod.py` —
  `SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")`,
  `SECURE_SSL_REDIRECT = True`, `SECURE_REDIRECT_EXEMPT` covering
  `api/health` and `api/ready`. **Unchanged by this plan** — Django keeps
  doing the HTTP→HTTPS redirect (with probe exemptions), so Traefik must NOT
  add its own blanket redirect (a Traefik-level redirect would break
  plain-HTTP probes and the CI smoke test).
- Traefik latest stable verified at planning time: **v3.7.6** (2026-06-30).
  Pin the latest v3 at execution time; Dependabot's docker-compose ecosystem
  tracks it afterward.
- docker-rollout: v0.13 (2025-07-25), installed as a CLI plugin file. Its
  requirements: target service has healthcheck (ours does), no
  `container_name`/`ports` (ours has neither), a proxy that routes only to
  healthy containers (this plan adds it).
- Traefik behavior this design relies on (verify empirically in Step 6):
  the Docker provider only routes to containers whose Docker health status
  is healthy, and entrypoints overwrite client-supplied `X-Forwarded-*`
  headers by default.

## Commands you will need

Run from the BAKED project root (`$BAKE/my-project`) unless noted.

| Purpose | Command | Expected on success |
|---------|---------|---------------------|
| Bake | `uvx cookiecutter . --no-input -o $BAKE` (template root) | exit 0 |
| Tests | `uv run pytest` | all pass, 100% |
| Hooks | `git add -A && uv run pre-commit run --all-files` | all pass |
| Render check | `docker compose --env-file .env -f .docker/compose/prod.yaml config` | renders; TRAEFIK_DOMAIN label resolved |
| Boot | `docker compose --env-file .env -f .docker/compose/prod.yaml up -d --build --wait` | exit 0, services healthy |
| Host probe | `curl -fsS http://localhost/api/health` | `{"status": "ok"}` |
| Install rollout | see Step 5 | `docker rollout --help` prints usage |
| Teardown | `docker compose --env-file .env -f .docker/compose/prod.yaml down -v` | exit 0 |

## Scope

**In scope**:
- `{{cookiecutter.project_slug}}/.docker/compose/prod.yaml`
- `{{cookiecutter.project_slug}}/.env.example`
- `{{cookiecutter.project_slug}}/README.md`
- `.github/workflows/ci.yaml` (template root — only if Plan 013's
  compose-smoke job exists; one added probe step)

**Out of scope**:
- `dev.yaml` — dev keeps direct `:8000`; no proxy needed locally.
- `prod.py` / gunicorn.sh — no settings or script changes; trust is
  expressed via the `FORWARDED_ALLOW_IPS` env var on the api service.
- Kamal, Swarm, or Kubernetes manifests — docker-rollout on Compose is the
  decided strategy.
- Traefik dashboard/API — keep disabled (no `--api.insecure`); enabling it
  safely is its own decision.
- TLS for the worker/beat/postgres/redis — internal services, never routed.

## Git workflow

- Branch: `advisor/018-traefik-zero-downtime-deploys`
- Conventional commit, e.g. `feat: ship traefik and standardize zero-downtime deploys`
- Do NOT push or open a PR unless the operator instructed it.

## Steps

### Step 1: Add the traefik service to prod.yaml

Insert alphabetically (after `redis`, before `worker`; after Plan 008 the
order is api, beat, postgres, redis, traefik, worker):

```yaml
  traefik:
    command:
      - --certificatesresolvers.letsencrypt.acme.email=${TRAEFIK_ACME_EMAIL}
      - --certificatesresolvers.letsencrypt.acme.httpchallenge.entrypoint=web
      - --certificatesresolvers.letsencrypt.acme.storage=/letsencrypt/acme.json
      - --entrypoints.web.address=:80
      - --entrypoints.websecure.address=:443
      - --ping=true
      - --providers.docker=true
      - --providers.docker.exposedbydefault=false
    healthcheck:
      test:
        - CMD
        - traefik
        - healthcheck
        - --ping
      interval: 30s
      timeout: 5s
      retries: 3
      start_period: 10s
      start_interval: 2s
    image: traefik:v3.7.6
    ports:
      - "80:80"
      - "443:443"
    restart: unless-stopped
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:ro
      - traefik_data:/letsencrypt
```

Add `traefik_data:` to the top-level `volumes:` (alphabetical). Note
`${TRAEFIK_ACME_EMAIL}` is also interpolation — covered by the same
`--env-file .env` convention.

### Step 2: Route the api service

Add to the existing `api` service in prod.yaml (keys in the file's existing
alphabetical style — `labels` sorts after `healthcheck`; add
`FORWARDED_ALLOW_IPS` under the existing `environment` block):

```yaml
    environment:
      DJANGO_ENV: prod
      FORWARDED_ALLOW_IPS: "*"
    labels:
      - traefik.enable=true
      - traefik.http.routers.api-web.entrypoints=web
      - traefik.http.routers.api-web.rule=PathPrefix(`/`)
      - traefik.http.routers.api-websecure.entrypoints=websecure
      - traefik.http.routers.api-websecure.rule=Host(`${TRAEFIK_DOMAIN}`)
      - traefik.http.routers.api-websecure.tls.certresolver=letsencrypt
      - traefik.http.services.api.loadbalancer.server.port=8000
```

Design rationale, inline so the reviewer has it: `FORWARDED_ALLOW_IPS: "*"`
is safe here *because* the api container publishes no ports — its only
network peers are compose-network services, and Traefik overwrites
client-supplied `X-Forwarded-*`; gunicorn honors this env var natively (its
`forwarded_allow_ips` default reads it). The port-80 router is a catch-all
so probes and the CI smoke test work without a domain; Django itself
redirects non-probe HTTP to HTTPS (`SECURE_SSL_REDIRECT` with the probe
exemptions), which is why **no Traefik-level redirect middleware is added**.
The 443 router carries the ACME certresolver and needs the real domain.

**Verify**: in a bake with `.env` created:
`docker compose --env-file .env -f .docker/compose/prod.yaml config` →
renders; the websecure rule shows the literal domain from `.env`; no
"variable is not set" warning.

### Step 3: Environment variables

In `{{cookiecutter.project_slug}}/.env.example` (byte-sorted; the
pre-commit sorter validates):

- Add `TRAEFIK_ACME_EMAIL={{ cookiecutter.author_email }}` — rendered by
  cookiecutter, matching how author email is templated elsewhere.
- Add `TRAEFIK_DOMAIN=example.com` — matching the `CSRF_TRUSTED_ORIGINS`
  example.com precedent.
- Remove the commented `# FORWARDED_ALLOW_IPS=` line if present (Plan 002
  added it; prod.yaml now sets the variable explicitly — the commented
  escape hatch is superseded).

**Verify**: bake → `git add -A && uv run pre-commit run --all-files` → the
sorter leaves `.env.example` unmodified.

### Step 4: Boot and probe through Traefik

In the bake: `cp .env.example .env`, replace `SECRET_KEY` with a long random
value (the prod boot guard rejects the placeholder), set any other
prod-required vars that exist by now (`SENTRY_DSN`/`RESEND_API_KEY` dummies
per plans 007/009 if landed). Then:

1. `docker compose --env-file .env -f .docker/compose/prod.yaml up -d --build --wait`
   → exits 0 (traefik healthy via its ping check; expect ACME errors in
   traefik logs for example.com — harmless, port 80 routing is unaffected).
2. `curl -fsS http://localhost/api/health` → `{"status": "ok"}` — the first
   host-level probe this stack has ever had (previously exec-only).
3. `curl -fsS http://localhost/api/ready` → `{"status": "ok"}`.
4. `curl -s -o /dev/null -w '%{http_code}' http://localhost/api/docs` →
   `301` (Django's SSL redirect on a non-exempt path — proves the redirect
   division of labor).

### Step 5: Install docker-rollout and rehearse a zero-downtime deploy

Install (pin the release, don't track main):

```
mkdir -p ~/.docker/cli-plugins
curl -fsSL https://raw.githubusercontent.com/wowu/docker-rollout/v0.13/docker-rollout \
  -o ~/.docker/cli-plugins/docker-rollout
chmod +x ~/.docker/cli-plugins/docker-rollout
docker rollout --help
```

Rehearsal, with the stack from Step 4 still up:

1. In one terminal, a continuous probe:
   `while true; do curl -fsS -o /dev/null http://localhost/api/health || echo "FAIL $(date +%T.%N)"; sleep 0.2; done`
2. In another, trigger a rollout:
   `docker rollout --env-file .env -f .docker/compose/prod.yaml api`
   (verify the flag spelling with `docker rollout --help`; if it does not
   support `--env-file`, export the file first: `set -a && . ./.env && set +a`
   then `docker rollout -f .docker/compose/prod.yaml api`).
3. Expected: rollout scales api to 2, waits for the new container's
   healthcheck, removes the old one — and the probe loop prints **zero FAIL
   lines**. `docker compose --env-file .env -f .docker/compose/prod.yaml ps`
   shows a single healthy api afterward.
4. Note what happened with `pre_start`: the new replica runs migrations
   before starting. With one-at-a-time replacement this cannot race; the
   deploy recipe (Step 6) still serializes migrations explicitly for
   determinism.

Tear down with `down -v` when done.

### Step 6: Rewrite the README deployment story

Replace the bring-your-own-ingress paragraphs of `## Production` with the
standardized procedure:

- **Topology**: Traefik terminates TLS (Let's Encrypt via
  `TRAEFIK_ACME_EMAIL` + `TRAEFIK_DOMAIN`), routes to healthy api
  containers, and overwrites client forwarded headers;
  `FORWARDED_ALLOW_IPS=*` is safe because the api is reachable only on the
  compose network. Port 80 serves probes and redirects; 443 serves traffic.
- **One-time host setup**: install docker-rollout (the pinned curl from
  Step 5).
- **Every deploy** (all from the project root):

  ```shell
  git pull
  docker compose --env-file .env -f .docker/compose/prod.yaml build
  docker compose --env-file .env -f .docker/compose/prod.yaml run --rm --no-deps api /app/.docker/scripts/migrations.sh
  docker rollout --env-file .env -f .docker/compose/prod.yaml api
  docker compose --env-file .env -f .docker/compose/prod.yaml up -d
  ```

  (build → serialized migrations → zero-downtime api swap → converge the
  remaining services; worker/beat restarts are brief and buffered by the
  queue — `acks_late` re-delivers any task killed mid-flight.)
- **The discipline the tooling cannot provide**: migrations must be N-1
  compatible — the old code serves while the new schema is live during the
  overlap window. Additive migrations first; destructive changes ship one
  deploy later.
- **Security note**: Traefik holds a read-only mount of the Docker socket —
  root-equivalent on the host if Traefik is compromised; standard for
  single-host Docker proxies, but worth knowing.
- Update the `--env-file .env` convention wherever the README shows prod
  compose commands (including the ones Plan 002 wrote).

**Verify**: `uv run pre-commit run markdownlint --all-files` in the bake →
passes.

### Step 7: Extend the CI smoke test (if it exists)

If Plan 013's `compose-smoke` job is present in `.github/workflows/ci.yaml`:
switch its compose invocations to the `--env-file .env` form, and add a
host-level probe step after the exec probes:

```yaml
      - name: Probe through traefik
        working-directory: /tmp/smoke/my-project
        run: |
          curl -fsS http://localhost/api/health
          curl -fsS http://localhost/api/ready
```

(Do NOT add a rollout rehearsal to CI in this plan — it needs plugin
installation and doubles job time; note it in the index as an optional
follow-up.) If 013 hasn't run yet, add a one-line note to its index row that
prod compose commands now require `--env-file .env` and a traefik host probe
is expected.

### Step 8: Full verification loop

**Verify**: fresh bake → `uv run pytest` → all pass, 100% (no Python
changed); `git add -A && uv run pre-commit run --all-files` → all pass;
Steps 4–5 outcomes recorded in the PR description (including the zero-FAIL
rollout probe).

## Test plan

No pytest changes — the deliverable is infrastructure. The executable
verifications are: the render check (Step 2), the sorted `.env.example`
(Step 3), the four boot probes (Step 4), the live rollout rehearsal with a
zero-failure probe loop (Step 5), and the CI smoke extension (Step 7).

## Done criteria

- [ ] prod.yaml contains the traefik service (pinned v3.x) and the api labels; `docker compose --env-file .env -f .docker/compose/prod.yaml config` renders with the domain resolved
- [ ] `curl http://localhost/api/health` through Traefik → 200; `/api/docs` over HTTP → 301
- [ ] `docker rollout ... api` completes with zero failed probes in the 0.2s loop
- [ ] `.env.example` has TRAEFIK_ACME_EMAIL + TRAEFIK_DOMAIN, no commented FORWARDED_ALLOW_IPS, and passes the sorter
- [ ] README Production section documents the standardized deploy recipe incl. N-1 migration discipline and the `--env-file .env` convention
- [ ] Baked project: `uv run pytest` + `pre-commit run --all-files` all pass
- [ ] No files outside the in-scope list modified (`git status`)
- [ ] `plans/README.md` status row updated (and the bring-your-own-ingress reversal noted)

## STOP conditions

- No local Docker available — this plan cannot be executed by inspection;
  hand it back.
- The rollout rehearsal prints ANY probe failures — the health-gating chain
  (Traefik ↔ Docker health status ↔ rollout) is not behaving as designed on
  the installed versions; capture `docker compose ps` + traefik logs and
  report rather than tuning blindly.
- Traefik routes to the api container BEFORE Docker reports it healthy
  (visible as 502s during the rehearsal) — the docker-provider/health
  assumption failed; report the Traefik version and behavior.
- `docker rollout` errors on the compose lifecycle hooks (`pre_start`) or on
  `--env-file` with no working fallback — report the exact error; do not
  fork the script.
- Anything requires publishing ports on the api service — that breaks the
  rollout precondition; the design is wrong somewhere, stop.

## Maintenance notes

- **This plan reverses the recorded "bring your own ingress" tradeoff** —
  future audits must not re-flag the Traefik service or the docker.sock
  mount as unexpected (the socket note lives in the README).
- Every future plan that adds a prod-required env var must ALSO update the
  README deploy recipe if a new step is implied, and keep using the
  `--env-file .env` convention.
- When Plan 008's beat service exists: it is deliberately NOT rolled — beat
  must be a singleton; the `up -d` convergence step restarts it with a brief,
  harmless gap.
- Traefik and docker-rollout versions: Dependabot tracks the traefik image;
  docker-rollout is host-installed and pinned in the README — bump it
  manually and re-run the rehearsal when doing so.
- If the project outgrows single-host Compose, the migration path is
  Kubernetes (probes, statelessness, and process separation already
  translate); the Traefik labels are the only compose-proxy-specific piece.
