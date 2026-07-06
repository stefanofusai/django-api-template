# Plan 004: Make production shutdown actually graceful (drop the SIGCONT trick)

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving to the
> next step. If anything in the "STOP conditions" section occurs, stop and
> report — do not improvise. When done, update the status row for this plan
> in `plans/README.md` — unless a reviewer dispatched you and told you they
> maintain the index.
>
> **Drift check (run first)**:
> `git diff --stat d333a73..HEAD -- '{{cookiecutter.project_slug}}/.docker/compose/prod.yaml' '{{cookiecutter.project_slug}}/README.md'`
> If any in-scope file changed since this plan was written, compare the
> "Current state" excerpts against the live code before proceeding; on a
> mismatch, treat it as a STOP condition.

## Status

- **Priority**: P1
- **Effort**: S–M (S if Docker rehearsal runs cleanly; M if rollout
  tuning is needed)
- **Risk**: MED — changes live-deploy replacement behavior; the rehearsal
  in Step 3 is the acceptance gate
- **Depends on**: none (serialize with 005/006/007 — same files)
- **Category**: bug
- **Planned at**: commit `d333a73`, 2026-07-05

## Why this matters

The prod `api` service sets `stop_signal: SIGCONT` with
`stop_grace_period: 5s`. SIGCONT is a no-op for gunicorn, so on every
stop/replacement gunicorn never begins a graceful shutdown — it keeps
running until Docker SIGKILLs it at the 5-second deadline. Consequences:
the `GUNICORN_GRACEFUL_TIMEOUT=30` knob shipped in `.env.example` is dead
config (the graceful path is unreachable), and any request still in
flight (allowed up to `GUNICORN_TIMEOUT=60`) is hard-truncated after 5s
during deploys and restarts. Two independent reviews flagged this as the
single most concerning behavior in the template. The fix lets gunicorn
receive SIGTERM and drain, with a grace period that covers the configured
graceful timeout — while keeping the Traefik/docker-rollout drain
mechanics (pre-stop hook, health-gated rotation) that already handle the
load-balancer side.

## Current state

Cookiecutter template; generated project under the literal
`{{cookiecutter.project_slug}}/` directory (quote in shell).

- `{{cookiecutter.project_slug}}/.docker/compose/prod.yaml:63-72` — the
  `api` service tail:

  ```yaml
      pre_start:
        - command:
            - /app/.docker/scripts/migrations.sh
  {%- if cookiecutter.use_s3_media == "no" %}
      volumes:
        - media_data:/app/media
  {%- endif %}
      restart: unless-stopped
      stop_grace_period: 5s
      stop_signal: SIGCONT
  ```

  Also relevant on the same service (Traefik knob branch, lines 37-58):
  `docker-rollout.pre-stop-hook=sleep 3` label, Traefik health check
  labels (`interval=1s`), and the retry middleware. When
  `use_traefik == "no"` the service publishes `127.0.0.1:8000:8000`
  instead.

- `{{cookiecutter.project_slug}}/.docker/scripts/gunicorn.sh` — full
  content:

  ```sh
  #!/bin/sh
  set -eu

  exec gunicorn \
      --access-logfile=- \
      --bind=0.0.0.0:8000 \
      --graceful-timeout="$GUNICORN_GRACEFUL_TIMEOUT" \
      --no-control-socket \
      --pythonpath=src \
      --timeout="$GUNICORN_TIMEOUT" \
      --workers="$GUNICORN_WORKERS" \
      config.wsgi
  ```

  `exec` means gunicorn is PID 1 and receives container signals
  directly. On SIGTERM gunicorn stops accepting new connections and
  gives workers up to `--graceful-timeout` seconds to finish in-flight
  requests before killing them.

- `{{cookiecutter.project_slug}}/.env.example:51-56` — defaults:
  `GUNICORN_GRACEFUL_TIMEOUT=30`, `GUNICORN_TIMEOUT=60`,
  `GUNICORN_WORKERS=5`.

- `{{cookiecutter.project_slug}}/README.md:220-226` (and the near-identical
  external-TLS branch at 235-240) currently document the SIGCONT trick:

  > During `docker rollout`, Traefik actively checks `/api/health`,
  > retries short backend selection races, waits briefly before stopping
  > the old API container, and keeps the old process alive for a short
  > drain window after Docker emits the stop event.

- The `celery-worker`/`celery-beat`/`postgres`/`redis`/`traefik` services
  set no `stop_signal` (default SIGTERM) — they are already correct.

Design decision baked into this plan (maintainer direction via two
concurring reviews): replace the SIGCONT trick with standard SIGTERM
draining. LB-side draining is already covered by the Traefik health
check + `pre-stop-hook=sleep 3`; the retry middleware absorbs the small
race window. The grace period must exceed the graceful timeout so Docker
never SIGKILLs a still-draining gunicorn.

## Commands you will need

| Purpose | Command | Expected on success |
|---------|---------|---------------------|
| Bake | `uvx cookiecutter . --no-input -o /tmp/plan004` | baked |
| Env prep | `cd /tmp/plan004/my-project && cp .env.example .env` then the sed lines from `.github/workflows/ci.yaml:165-170` (SECRET_KEY, AWS_STORAGE_BUCKET_NAME, SENTRY_DSN, RESEND_API_KEY) | `.env` boot-ready |
| Boot prod stack | `docker compose -f .docker/compose/prod.yaml --env-file=.env up -d --build --wait --wait-timeout=300` | all healthy |
| Stop timing | `time docker compose -f .docker/compose/prod.yaml --env-file=.env stop api` | see Step 3 |
| Logs | `docker compose -f .docker/compose/prod.yaml --env-file=.env logs api` | see Step 3 |
| Teardown | `docker compose -f .docker/compose/prod.yaml --env-file=.env down -v` | exit 0 |

Note: on GitHub-runner-vintage Compose, `pre_start` may be rejected — on
a dev machine with Compose >= 5.3.0 it works as shipped. If your local
Compose rejects `pre_start`, apply the same temporary patch CI uses
(`.github/workflows/ci.yaml:177-200`) to the BAKED copy only.

## Scope

**In scope**:

- `{{cookiecutter.project_slug}}/.docker/compose/prod.yaml` — the `api`
  service's `stop_grace_period`/`stop_signal` lines only
- `{{cookiecutter.project_slug}}/README.md` — the two rollout paragraphs

**Out of scope** (do NOT touch):

- `gunicorn.sh`, `.env.example` — the knobs are correct; they become
  real.
- The `docker-rollout.pre-stop-hook` label and all Traefik labels.
- Other services' stop behavior (worker warm shutdown via default
  SIGTERM + `acks_late` redelivery is already the intended design).
- `dev.yaml` (dev uses runserver; default signals fine).

## Git workflow

- Work directly on `main`; do not create or switch to a plan branch unless the
  operator explicitly asks.
- Do NOT commit, push, or open a PR unless the operator explicitly instructs it.
- If asked to commit, use a conventional commit such as
  `fix: drain gunicorn with SIGTERM instead of SIGCONT hard-kill`.

## Steps

### Step 1: Replace the stop settings

In `prod.yaml`'s `api` service, delete the `stop_signal: SIGCONT` line
and change the grace period, with a comment stating the coupling (the
repo's comment policy: comments state constraints code can't show):

```yaml
    restart: unless-stopped
    # Must exceed GUNICORN_GRACEFUL_TIMEOUT (.env, default 30s) so Docker
    # never SIGKILLs a still-draining gunicorn. Traefik removes the
    # container from rotation before SIGTERM lands (pre-stop hook + 1s
    # health checks), so SIGTERM only has to finish in-flight requests.
    stop_grace_period: 35s
```

**Verify**: `grep -n "SIGCONT" '{{cookiecutter.project_slug}}/.docker/compose/prod.yaml'`
→ no matches; `grep -n "stop_grace_period" …` → one match, `35s`.

### Step 2: Rewrite the README rollout paragraphs

In the baked README, both Traefik branches (letsencrypt + external):
replace "keeps the old process alive for a short drain window after
Docker emits the stop event" with wording that matches the new
mechanics, e.g.:

> …waits briefly before stopping the old API container, then delivers
> SIGTERM: gunicorn stops accepting connections and finishes in-flight
> requests for up to `GUNICORN_GRACEFUL_TIMEOUT` seconds while Traefik
> has already removed the backend from rotation.

Keep both branches textually consistent as they are today.

**Verify**: bake and read the rendered Production section for both
`traefik_tls` values (`uvx cookiecutter . --no-input -o /tmp/plan004tls
traefik_tls=external` for the second).

### Step 3: Live shutdown rehearsal (acceptance gate)

Boot the baked default prod stack (see commands table), then:

1. `time docker compose -f .docker/compose/prod.yaml --env-file=.env stop api`
2. `docker compose -f .docker/compose/prod.yaml --env-file=.env logs api | tail -40`

**Verify**:

- The logs show gunicorn's graceful sequence: `Handling signal: term`,
  worker exits, `Shutting down: Master` — and NO
  `Worker ... was sent SIGKILL!`.
- The `stop` completes in well under 35s (idle gunicorn exits in ~1-2s;
  the 35s ceiling only matters under load).
- `docker inspect` of the stopped container shows `ExitCode` 0.

Restart (`up -d`) and, if `docker rollout` is installable on this
machine (install snippet is in the baked README Production section), run
a rollout rehearsal while hammering the API:

```shell
( while true; do
    curl -fsS -o /dev/null -w '%{http_code}\n' http://localhost/api/health || echo FAIL
    sleep 0.1
  done ) > /tmp/plan004-probe.log &
PROBE=$!
docker rollout -f .docker/compose/prod.yaml --env-file=.env api
sleep 3; kill $PROBE
sort /tmp/plan004-probe.log | uniq -c
```

**Verify**: the uniq output contains only `200` lines — no `FAIL`, no
5xx. Tear the stack down afterward.

### Step 4: Repeat Step 3's stop-timing check on the no-Traefik variant

Bake with `use_traefik=no` (api publishes `127.0.0.1:8000:8000`; prepare
`.env` with only the SECRET_KEY sed plus the default knobs' required
values), boot, and repeat Step 3 items 1-2. This variant has no LB drain
at all, so graceful SIGTERM is its ONLY protection — confirm the same
log signature.

**Verify**: same expected gunicorn graceful sequence; teardown clean.

### Step 5: Repo checks

`pre-commit run --all-files` at the root; in one baked project:
`git add -A && uv run pre-commit run --all-files` (yamlfmt/yamllint
cover the compose edit).

**Verify**: exit 0.

## Test plan

No pytest changes — the behavior is process-level. The acceptance
evidence is Step 3/4 log output; paste the gunicorn shutdown log lines
and the probe uniq-count into the completion report.

## Done criteria

- [ ] `SIGCONT` absent from the template; `stop_grace_period: 35s` with
      the coupling comment present
- [ ] Step 3 logs show `Handling signal: term` and no SIGKILL, exit 0
- [ ] Rollout probe log (if docker-rollout available) shows only 200s
- [ ] Both README branches rewritten and rendered correctly
- [ ] Root + baked pre-commit exit 0; `git status` clean outside scope
- [ ] `plans/README.md` status row updated

## STOP conditions

- The rollout probe records ANY non-200 — the SIGCONT trick may have
  been load-bearing for a race this plan misjudged. Capture the probe
  log + traefik/api logs and report; do not tune values on your own.
- Gunicorn logs show SIGKILL during a plain `stop` — something other
  than the grace period is cutting the drain short; report.
- Docker is unavailable — this plan cannot be verified without the live
  rehearsal; report rather than shipping unverified signal changes.
- You find documentation (docker-rollout upstream, a template comment,
  or a git-log rationale) explicitly requiring SIGCONT — surface it to
  the maintainer before proceeding.

## Maintenance notes

- `stop_grace_period` (35s) and `GUNICORN_GRACEFUL_TIMEOUT` (30) are
  coupled by convention, not mechanism; anyone raising the env default
  must raise the compose value. The comment in Step 1 records this.
- If a future plan adds long-running/streaming endpoints, revisit both
  values together with `GUNICORN_TIMEOUT`.
- Plan 005 (CI tests the shipped prod.yaml unpatched) should run after
  this one so CI exercises the final stop semantics.
