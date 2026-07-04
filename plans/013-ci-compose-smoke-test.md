# Plan 013: CI smoke test — bake, boot the prod compose stack, prove it serves

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving to the
> next step. If anything in the "STOP conditions" section occurs, stop and
> report — do not improvise. When done, update the status row for this plan
> in `plans/README.md` — unless a reviewer dispatched you and told you they
> maintain the index.
>
> **Drift check (run first)**: `git diff --stat 924bfba..HEAD -- .github/workflows/ci.yaml '{{cookiecutter.project_slug}}/.docker/' '{{cookiecutter.project_slug}}/.env.example' '{{cookiecutter.project_slug}}/src/'`
> This plan EXPECTS drift from plans 002/007/008/009 (health endpoint, env
> vars, beat service) — read `plans/README.md` status first and adapt the
> env/assertions to what actually landed (the steps call out each variant).

## Status

- **Priority**: P1 (the highest-leverage single test in the whole batch)
- **Effort**: M
- **Risk**: LOW (additive CI; flakiness risk handled via --wait timeouts)
- **Depends on**: 002 (health endpoint + healthcheck tuning). Adapts to: 007 (SENTRY_DSN), 008 (beat), 009 (RESEND_API_KEY), 003 (users migration).
- **Category**: tests
- **Planned at**: commit `924bfba`, 2026-07-04

## Why this matters

The template's whole promise is "bake it and it runs" — yet no workflow ever
*runs* it. The Docker image is built but never started; the four entrypoint
scripts, the compose healthchecks, the `pre_start` migration hook, the
SSL-redirect exemption that keeps the healthcheck alive, and the
readiness endpoint against real Postgres/Redis are all unexercised. The
audit's deploy-path findings (healthcheck Host trap, worker never starting)
would have been caught by exactly this job. This smoke test also closes the
"readiness handling is only tested against locmem+mocks" gap: in the booted
stack, `/api/ready` runs against real Redis and Postgres.

## Important context

- This plan edits the TEMPLATE-root workflow (`.github/workflows/ci.yaml`)
  only. The baked project's own workflows are not in scope (a baked project
  cannot bake itself).
- GitHub-hosted ubuntu runners ship Docker Engine + Compose v2 new enough for
  `pre_start` and `--wait` (Compose ≥ 2.30 required by the template; verify
  in the job with `docker compose version` as a first step so failures are
  self-diagnosing).
- The prod api service publishes NO ports (bring-your-own ingress), so all
  HTTP probes run **inside** the api container via `docker compose exec`.

## Current state

- Root `ci.yaml` jobs: `bake` (matrix), `docker-build` (+ after Plan 011:
  `bake-invalid`; after 012: `pre-commit`). Bake steps use
  `uvx cookiecutter . --no-input -o /tmp/bake`.
- `{{cookiecutter.project_slug}}/.env.example` — dev-oriented defaults:
  `ALLOWED_HOSTS=localhost,127.0.0.1`, postgres creds = slug-derived,
  `SECRET_KEY` = an insecure placeholder (prod boot REJECTS it after Plan
  002), `DJANGO_ENV=dev` (prod.yaml overrides via `environment:`), and — after
  007/009 — empty `SENTRY_DSN=` / `RESEND_API_KEY=` lines (prod boot rejects
  empty values).
- `{{cookiecutter.project_slug}}/.docker/compose/prod.yaml` — services api
  (healthcheck on `/api/health` after 002, `pre_start` migrations), worker
  (healthcheck `celery inspect ping`), postgres, redis (+ beat after 008, no
  healthcheck).
- AWS vars: prod storage requires `AWS_STORAGE_BUCKET_NAME` (any non-empty
  value works — S3 is never contacted unless media is used).

## Commands you will need

Local rehearsal (from template root; requires Docker):

| Purpose | Command | Expected on success |
|---------|---------|---------------------|
| Bake | `uvx cookiecutter . --no-input -o /tmp/smoke` | exit 0 |
| Env prep | Step 1's script run in `/tmp/smoke/my-project` | `.env` written |
| Boot | `docker compose -f .docker/compose/prod.yaml up -d --build --wait --wait-timeout 300` | exit 0, services healthy |
| Probe | `docker compose -f .docker/compose/prod.yaml exec api curl -fsS http://127.0.0.1:8000/api/ready` | `{"status": "ok"}` |
| Teardown | `docker compose -f .docker/compose/prod.yaml down -v` | exit 0 |

## Scope

**In scope**:
- `.github/workflows/ci.yaml` (template root — one new job)

**Out of scope**:
- Any file under `{{cookiecutter.project_slug}}/` — if the smoke test reveals
  a product bug, STOP and report; the fix belongs to the plan that owns that
  file.
- A dev-stack smoke job (dev is exercised by humans daily; prod is the blind
  spot).

## Git workflow

- Branch: `advisor/013-ci-compose-smoke-test`
- Conventional commit, e.g. `ci: smoke test the baked prod compose stack`
- Do NOT push or open a PR unless the operator instructed it.

## Steps

### Step 1: Write the job

Add to root `ci.yaml` (job order alphabetical; name `compose-smoke`):

```yaml
  compose-smoke:
    name: Compose smoke test
    runs-on: ubuntu-latest
    steps:
      - name: Checkout repository
        uses: actions/checkout@v6.0.3
      - name: Set up Python
        uses: actions/setup-python@v6.2.0
        with:
          python-version: "3.14"
      - name: Set up uv
        uses: astral-sh/setup-uv@v8.2.0
      - name: Show compose version
        run: docker compose version
      - name: Bake project
        run: uvx cookiecutter . --no-input -o /tmp/smoke
      - name: Prepare production env file
        working-directory: /tmp/smoke/my-project
        run: |
          cp .env.example .env
          sed -i "s|^SECRET_KEY=.*|SECRET_KEY=$(python -c 'import secrets; print(secrets.token_urlsafe(64))')|" .env
          sed -i "s|^AWS_STORAGE_BUCKET_NAME=.*|AWS_STORAGE_BUCKET_NAME=smoke-test-bucket|" .env
      - name: Boot production stack
        working-directory: /tmp/smoke/my-project
        run: docker compose -f .docker/compose/prod.yaml up -d --build --wait --wait-timeout 300
      - name: Probe liveness and readiness from inside the api container
        working-directory: /tmp/smoke/my-project
        run: |
          docker compose -f .docker/compose/prod.yaml exec api curl -fsS http://127.0.0.1:8000/api/health
          docker compose -f .docker/compose/prod.yaml exec api curl -fsS http://127.0.0.1:8000/api/ready
      - name: Assert service states
        working-directory: /tmp/smoke/my-project
        run: |
          docker compose -f .docker/compose/prod.yaml ps
          test -z "$(docker compose -f .docker/compose/prod.yaml ps --status=exited -q)"
      - name: Dump logs on failure
        if: failure()
        working-directory: /tmp/smoke/my-project
        run: docker compose -f .docker/compose/prod.yaml logs
      - name: Tear down
        if: always()
        working-directory: /tmp/smoke/my-project
        run: docker compose -f .docker/compose/prod.yaml down -v
```

Adapt to what has landed (check `plans/README.md` status):
- **007 landed** → add to the env-prep step:
  `sed -i "s|^SENTRY_DSN=.*|SENTRY_DSN=https://00000000000000000000000000000000@sentry.example.com/1|" .env`
- **009 landed** → add:
  `sed -i "s|^RESEND_API_KEY=.*|RESEND_API_KEY=smoke-dummy|" .env`
- **008 landed** → beat has no healthcheck, so `--wait` doesn't gate on it;
  the `--status=exited` assertion catches a crash-looping beat. Additionally
  assert it's up:
  `docker compose -f .docker/compose/prod.yaml ps beat --format '{{.State}}' | grep -x running`
  (note: inside this workflow file the `{{.State}}` Go-template braces are
  fine — this file is NOT Jinja-rendered; it lives at the template root).
- **002 NOT landed** → probe `/api/ready` only (no `/api/health`), and expect
  the placeholder-SECRET_KEY sed to be strictly necessary anyway (ALLOWED_HOSTS
  default includes 127.0.0.1, so the healthcheck Host trap won't fire with the
  example env).

### Step 2: Local rehearsal

Run the full sequence from the commands table locally (Docker required).
Watch for: `pre_start` migrations completing (api logs), worker reaching
healthy, both probes returning `{"status": "ok"}`.

**Verify**: every command exits 0; teardown leaves no containers
(`docker ps` clean).

### Step 3: Validate the workflow file

**Verify**: root `uvx pre-commit run actionlint --all-files` (if Plan 012
landed) or `uvx --from actionlint-py actionlint` → no findings on ci.yaml.

## Test plan

The job IS the test. Its own failure modes are covered by: `--wait-timeout
300` (hung boots fail, not hang), the logs-on-failure step (diagnosable), and
`down -v` under `if: always()` (no runner pollution).

## Done criteria

- [ ] `compose-smoke` job present in root ci.yaml with boot/probe/assert/teardown steps
- [ ] Local rehearsal passed end-to-end (or, if no local Docker: state so and rely on the first CI run — get the operator's OK first)
- [ ] actionlint clean on the workflow
- [ ] No files outside the in-scope list modified (`git status`)
- [ ] `plans/README.md` status row updated

## STOP conditions

- The stack fails to boot for a reason in TEMPLATE code (healthcheck 400,
  missing env var, entrypoint typo) — that is a real product bug this test
  just caught: report it against the owning plan, do NOT patch product files
  here.
- `--wait` semantics differ on the runner's compose version (job fails on a
  healthy stack) — report versions; consider `--wait-timeout` bump once, then
  stop.
- The job takes > ~10 minutes in rehearsal — report; the image build likely
  isn't caching (interaction with Plan 012's buildx setup is a follow-up, not
  an improvisation).

## Maintenance notes

- Every future plan that adds a prod-required env var MUST extend the env-prep
  step (the pattern: one `sed` per var). The boot guard failures make
  forgetting loud — the smoke test is where they surface pre-merge.
- Every new compose service should get either a healthcheck (gated by
  `--wait`) or an explicit state assertion here (like beat's).
- When a reverse proxy is ever added to prod.yaml, probes can move from
  `exec` to host-published ports.
