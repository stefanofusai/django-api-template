# Remaining Design Spikes

The implementation plans from the July 2026 audit have been completed and
removed from this directory. Only unresolved design-spike material remains.

## Spike Index

| Plan | Topic | Design output | Status |
|------|-------|---------------|--------|
| [013](013-api-auth-knob-spike.md) | `api_auth` knob for token/API-key auth | [013-api-auth-DESIGN.md](013-api-auth-DESIGN.md) | DONE |
| [020](020-async-example-spike.md) | Example API task-queue integration | [020-async-example-DESIGN.md](020-async-example-DESIGN.md) | DONE |

## Related Design Output

- [019-csp-DESIGN.md](019-csp-DESIGN.md) records the CSP decision from the
  browser-surface hardening work.
  CSP is scoped as a *decision*, not an assumed defect → plan 019 Part B.
- **`DEFAULT_AUTO_FIELD` not set anywhere**: not a bug. The `core` migration
  freezes `BigAutoField` for `User.id` and the migration-drift CI gate is green.
- **`update_note` uses full `save()` not `save(update_fields=…)`**: negligible on
  a 3-field model; not worth a plan.
- **`deploy-check.sh` runs `check --deploy --tag=security` only**: standard
  recommendation; the full `--deploy` set adds W-series noise. Fine as-is.
- **`.env.example` ships `localhost` in `ALLOWED_HOSTS` and a `django-insecure-`
  `SECRET_KEY`**: well-handled — prod boot-guard rejects the insecure prefix, and
  the file is documented as replace-before-deploy. (The DB password gap → plan
  008; the Redis password gap → plan 009.)
- **Example `send_email` non-idempotent under global `acks_late`**: example code,
  document-level only; consider a one-line caveat if plan 020's async example
  ships.
- **Bake matrix single-knob coverage / CI uv caching / dependency freshness /
  100%-coverage-gate genuineness / no Makefile**: all checked and clean. The
  residual test-matrix gap was notes × stripped-stack → plan 010. (CI *uv*
  caching is clean; CI *pre-commit* caching was the real gap → plan 016 Part A.)
- **Actions/hooks/images pinned by version tag, not digest** (2026-07-07 audit):
  rejected as a plan. Everything is consistently exact-tag-pinned and
  Dependabot-maintained; the one binary fetch (Compose in the smoke job) is
  already SHA-256-verified. Digest-pinning everything is maintainer taste, not
  a defect.
- **Request logs capture client IP / user-agent; gunicorn access log duplicates
  structlog request logs** (2026-07-07 audit, MED confidence): a real
  data-retention/PII consideration but a policy decision, not a defect — many
  operators want IPs in logs. Noted for the maintainer: a structlog redaction
  processor and/or dropping gunicorn's `--access-logfile=-` are the levers if a
  GDPR posture requires it. No plan unless the maintainer wants one.
- **Sessions use the DB backend while Redis sits mostly idle** (2026-07-07
  audit): plausible optimization (`SESSION_ENGINE = cached_db`) but a
  behavior-tradeoff decision on example-grade traffic; noted, not planned.
- **`GUNICORN_WORKERS=5` static default**: tuning knob already env-driven;
  a one-line CPU-sizing comment in `.env.example` is the most this warrants.
- **No debugpy/IDE-attach path in the dev loop**: Werkzeug via `runserver_plus`
  covers most cases; opt-in debugpy noted as a possible DX nicety, not planned.
- **No `/metrics` endpoint**: observability triad (Sentry errors/traces,
  structlog logs) is complete; a Prometheus surface is adjacent-possible but
  ungrounded in repo intent and cuts against documented minimalism. Rejected
  (revisit on real consumer demand).
- **Ready-probe tests patch private helpers / assert on mocks**: tolerated —
  the observable-behavior coverage is real; the coupling is a refactor-friction
  smell, not a correctness gap. Not worth a plan.
- **`hooks/post_gen_project.py` fallback branches untested; missing-artifact
  gaps only incidentally covered**: the 11-case bake matrix catches every
  *wrong* `REMOVED_PATHS` entry loudly (unlink raises); a *missing* entry for a
  non-`src` artifact is the residual gap. Accepted for now — a "no leftover
  artifacts" post-bake assertion is a possible future CI step.
- **Repeated `uv sync --group=ci` incantations / duplicated Postgres service
  blocks / dev-prod compose duplication / knob-Jinja sprawl / split-settings
  noqa cost / two pre-commit run idioms**: all reviewed (2026-07-07 debt
  audit); each is idiomatic-or-tolerated with the bake matrix as the safety
  net. Recorded here so they aren't re-audited; none planned.
- **Further production-host operator scripts beyond deploy/verify/manage**
  (2026-07-07 review): `status.sh`/`logs.sh` (one-liners — `compose ps`,
  `logs -f` — don't clear the script bar), a pre-deploy "env doctor" (prod
  boot guards + `deploy-check.sh` already fail fast with clear messages),
  automated image pruning (dangerous — the previous tag IS the rollback
  candidate; manual `docker image prune` note lives in plan 022), cert
  tooling (Let's Encrypt is automatic; external certs are operator-owned).
  The bar: a script must be multi-step + critical + error-prone — that's
  022/023/024; the rest stay documentation.
- **An `api_framework` knob (django-ninja / DRF / django-bolt /
  django-modern-rest)** (maintainer idea, 2026-07-07): rejected as a knob.
  The framework is the skeleton, not a module — ninja is load-bearing in
  `apps/api` (NinjaAPI instances, pagination subclass, Pydantic schemas),
  the notes example, the test-client fixtures, and the Schemathesis contract
  wiring; a knob would mean N parallel implementations of all of it, an
  exploded bake matrix, and per-framework re-verification of every dependency
  bump — dissolving the template's opinionated-and-verified value ("A Django
  Ninja API service"). If real demand appears, the honest shape is a sibling
  template (or, at most, a narrow DRF-only feasibility spike with explicit
  kill criteria: contract-test + 100%-coverage preservable? matrix growth?
  who wants this template but not ninja?). Do not re-propose as a knob.

## Direction notes (options for the maintainer, not defects)

- **Credential provisioning** (registration / login / token-issue /
  password-reset endpoints): the custom user model exists but the only way to
  mint a credential is `createsuperuser`/admin. Tightly coupled to plan 013 —
  question 4 of that spike scopes how much of this the auth knob should pull in.
  Not planned separately until 013's direction is chosen.
- **Wire the async slice end-to-end** (enqueue `send_email` from a notes
  endpoint): the task and the README's `.delay(...)` docs exist but nothing calls
  `.delay()` in shipped code → scoped as spike **020**.
- **Enforce vendored-skill integrity**: `skills-lock.json` records hashes nothing
  verifies → scoped as spike **021** (with a real caveat about `computedHash`
  reliability).
- **Restore story**: the backup script now has a documented-and-scripted inverse
  → plan **002** (was a broken hand-typed runbook command).
