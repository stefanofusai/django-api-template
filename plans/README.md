# Implementation Plans

All 21 plans are baselined at commit `ae42991` (2026-07-07). Their history:
four plans came from a senior review graded against
saaspegasus/django-boilerplate, cookiecutter-django, and Django/DRF best
practices; eleven more from a deep audit (parallel category sweeps, every
finding vetted against the cited code); then a **deep review pass** the same
day re-verified every plan against the live code with fresh-context checkers
(fixing ~20 factual errors in place), re-ran the audit, and added six plans
from net-new findings. Finally the set was **renumbered by priority** — plan
number now equals recommended execution order (001 most important, 021
least). Former numbers, for git-history archaeology:
old 005→001, 016→002, 006→003, 001→004, 007→005, 019→006, 002→007, 008→008,
017→009, 009→010, 018→011, 015→012, 004→013, 003→014, 010→015, 020→016,
011→017, 021→018, 012→019, 013→020, 014→021. The headline stands: **this
template is top-tier** — the lists below are high-signal, not padding.

Execute in **table-row order** unless dependencies say otherwise (numbers
001-021 equal priority order from the renumbering pass; plans added later —
022 onward — take the next free number and are slotted into the table by
priority, so the table, not the number, is authoritative going forward). Each
executor: read the plan fully before starting, honor its STOP conditions, and
update your row when done.

Work directly on `main`. Do not create or switch to a branch, and do not commit,
push, or open a PR unless the operator explicitly says so.

**Context every executor needs**: this repo is a **Cookiecutter template**. The
project code lives under the literal directory `{{cookiecutter.project_slug}}/`
(quote it in shell); files inside contain Jinja placeholders that must stay
valid. `{{cookiecutter.project_slug}}/.github/workflows/*` and
`{{cookiecutter.project_slug}}/.agents/*` are copied **without rendering** —
never put Jinja or slug-derived values there. The **repo-root**
`.github/workflows/ci.yaml` is the template's *own* CI and is a normal editable
YAML file. `{{cookiecutter.project_slug}}/.docker/*` **is** rendered (Jinja OK).
Verification means **baking** a project
(`uvx cookiecutter . --no-input -o /tmp/bake [key=value …]`) and running the
baked checks: `uv run pytest` (needs a reachable `postgres:18.4`; 100% coverage
required), `git add -A && uv run pre-commit run --all-files`, plus the repo-root
`uvx pre-commit run --all-files`. Docker verification needs Compose ≥ 5.3.0
(the current release scheme; `pre_start` lifecycle hooks require it).
**There is no shellcheck hook in either pre-commit stack** (until plan 006
lands) — shell scripts are linted directly via
`uvx --from shellcheck-py shellcheck <file>`.

## Execution order & status

| Plan | Title | Priority | Effort | Depends on | Status |
|------|-------|----------|--------|------------|--------|
| 001 | Make `postgres-backup.sh` fail safe + prune portably | P1 | S | — | DONE |
| 002 | Fix broken restore runbook + ship `postgres-restore.sh` | P1 | S | — | DONE |
| 003 | Prune `django-celery-expert` skill when `use_celery=none` | P1 | S | — | DONE |
| 004 | Add gitleaks secret scanner to baked pre-commit | P2 | S | — | DONE |
| 005 | Test-suite hygiene (dead test, vacuous assert, dangling ref, brittle metadata) | P2 | S | — | DONE |
| 006 | Add shellcheck to baked + root pre-commit stacks | P2 | S | — | DONE |
| 007 | Gate HTTPS-trust settings **and `FORWARDED_ALLOW_IPS`** on a `behind_proxy` knob | P2 | M | — | DONE |
| 008 | Reject the default (slug) DB password in production | P2 | S | — | DONE |
| 009 | Require a password on the bundled Redis | P2 | S–M | — | TODO |
| 010 | CI robustness: example-API-under-stripped-stack bake + Postgres image drift guard | P2 | S | — | DONE |
| 011 | Notes-slice hardening: pagination e2e, composite index, auth'd contract pass, Hypothesis profile | P2 | M | — | TODO |
| 012 | Vendor `django-safe-migration`, `django-perf-review`, `django-access-review` skills | P2 | S | — | DONE |
| 022 | Release workflow + GHCR registry: immutable deploys, tag-repoint rollback | P2 | M | — | TODO |
| 013 | Design spike: `api_auth` knob for token/API-key auth | P2 (spike) | M | — | TODO |
| 023 | `postgres-backup.sh` subcommands: `backup` / `verify` (restore rehearsal vs throwaway container) | P3 | S–M | 001 (hard) | DONE |
| 024 | `manage.sh` wrapper for prod management commands (`createsuperuser` day-one op) | P3 | S | — | TODO |
| 014 | `export_openapi_schema` command + schema-artifact CI job | P3 | S–M | — | TODO |
| 015 | Generated-project Docker boot smoke + dev-image build | P3 | M | — | TODO |
| 016 | CI/build hygiene: pre-commit cache, dockerignore `.agents/`, `$$POSTGRES_USER` fix | P3 | S | — | DONE |
| 017 | Scaffolding polish (`.editorconfig`, generated `SECURITY.md`, README arch map, `traefik_tls` prompt) | P3 | S | — | TODO |
| 018 | Remove dead mypy/django-stubs config (+ ty-needs-stubs experiment) | P3 | S | — | TODO |
| 019 | Browser-surface hardening: bound request ID + signal-dispatch test (do), CSP (spike) | P3 | S | — | TODO |
| 020 | Design spike: wire the example API to the task queue (enqueue-from-request) | P3 (spike) | M | — | TODO |
| 021 | Spike: enforce `skills-lock.json` hashes so `.agents/` skills can't drift | P3 (spike) | S | — | TODO |

Status values: TODO | IN PROGRESS | DONE | BLOCKED (one-line reason) |
REJECTED (one-line rationale).

## Recommended order & independence

Numeric order is the recommended order. No plan *hard*-blocks another, but
several touch the same files and should be sequenced to avoid clobbering:

1. **001, 002, 003** (P1) — smallest, self-contained, pure wins. 001 and 002
   both touch the backup/restore script family and the hook's
   `postgres != compose` removal list — land in either order, then re-check the
   other's excerpts.
2. **004, 005, 006** — small, independent. **005 and 003 both edit
   `hooks/post_gen_project.py`** (003 adds celery-skill pruning; 005 removes the
   `celery_test.py` entry from `REMOVED_PATHS`). Land one, then re-check the
   other's excerpt. 005 also *requires* the `celery_test.py` deletion + hook edit
   together (else a `use_celery=none` bake crashes on a missing file). **004 and
   006 both edit the baked pre-commit config and the root README tool
   inventory** — land one, re-check the other's insertion points.
3. **007, 010** — **both edit the repo-root `ci.yaml` `bake` matrix** (007 adds a
   `no-proxy` case; 010 adds an `example-minimal` case). Insert alphabetically and
   re-check the matrix after the first lands. 007 contains a maintainer *design
   decision* (should a plain-HTTP prod mode exist?) flagged as a STOP — resolve
   before implementing. **016 also edits `ci.yaml`** (cache steps + health-cmd),
   in different regions — same sequencing rule.
4. **008, 009, 011, 012** — 008 and 007 both edit `prod.py` (sequence them).
   009 is compose/env only. 011 needs a running Postgres and is Docker-free
   otherwise. **012 and 003 both affect `skills-lock.json` content** (012 edits
   the committed file; 003 edits it at bake time via the hook); prefer landing
   **003 first**, then 012 (which must re-confirm 003's default-bake
   byte-identity check against the post-012 file). 012 needs Node + network
   (`npx skills`).
5. **013, 020, 021** (spikes) — produce proposals + PoCs and STOP for maintainer
   decisions; start early if the direction matters, they block nothing. Each
   spike's deliverable is a NEW `plans/NNN-*-DESIGN.md` file — never overwrite
   the spike plan itself.
6. **014, 015, 016, 017, 018, 019** — DX/hardening; lowest urgency. 019's
   Part A (bound request ID + signal-dispatch test) is a clean small win
   independent of its Part B (CSP decision). 015 shares the Compose pin+sha with
   `ci.yaml`'s smoke (candidate for 010's drift-check pattern). 016 Part B and
   018 both edit `Dockerfile.dockerignore` (different lines; the
   `file-contents-sorter` hook keeps it sorted either way).

## Dependency & interaction notes

- **001 ↔ 002**: same script family + same hook removal-list entry. Sequence;
  re-run the drift check after the first.
- **003 ↔ 005**: both edit `hooks/post_gen_project.py`. Sequence; re-run the
  drift check after the first.
- **004 ↔ 006**: both edit the baked `.pre-commit-config.yaml` and the
  repo-root `README.md:16` tool inventory. Sequence.
- **007 ↔ 010 ↔ 016**: all edit the root `ci.yaml` (007/010: bake matrix;
  016: cache steps + health-cmd). Sequence; keep matrix cases alphabetized by
  `case:`.
- **007 ↔ 008**: both edit `prod.py`. Sequence; re-check excerpts.
- **003 → 012**: 012 must re-confirm 003's default-bake `skills-lock.json`
  byte-identity check once the three new skills are committed. 003's celery-off
  pruning keeps working (it pops only `django-celery-expert`).
- **008 → 009 follow-up**: if 008's DB-password guard is accepted, a matching
  prod guard for `REDIS_PASSWORD` is the natural follow-up (noted in 009).
- **013 → 011 Part B**: if the token-auth knob ever ships, the authenticated
  Schemathesis pass should switch from session+CSRF injection to a token
  header (far simpler) — noted in 011.
- **020 ↔ rejected `/ready`-broker finding**: if 020 ships (endpoints enqueue
  tasks), the broker becomes a request-path dependency and the readiness-probe
  rejection below is worth revisiting.
- **015 ↔ 010**: the generated smoke and `ci.yaml`'s smoke share the Compose
  pin+sha — a future drift-check (010's pattern) could cover it.
- **016 ↔ 018**: both edit `Dockerfile.dockerignore` (add vs. remove lines);
  either order, the sorter hook normalizes.
- **022 ↔ 009**: both edit `prod.yaml` (022: `image:` on the app services;
  009: the redis service). Different regions; sequence and re-check excerpts.
- **022 ↔ 015/016**: 022 adds `release.yaml` next to `docker-build.yaml`
  (which 015 extends) and reuses the `scope=prod` build cache 016 touches in
  the root CI; land in any order but re-verify the cache scopes and workflow
  inventory afterward. If 015's smoke lands, 022's hybrid `image:`+`build:`
  design keeps it working (`--build` never pulls).
- **008 → 022 runbook**: 022's release runbook lives in the same README
  `## Production` prose 008 (and 002/009) edit — re-check after each lands.
- **001 → 023 (HARD)**: 023 changes `postgres-backup.sh`'s CLI to
  `backup`/`verify` subcommands, superseding 001's "CLI unchanged" done
  criterion — 001 must land first, and the README cron example moves with
  023.
- **002 ↔ 023**: restore (live DB) and verify (throwaway container) are
  different operations by design; both edit the same README backup/restore
  passage — sequence and re-check.
- **022/023/024 script family**: all add/extend `.docker/scripts/` operator
  scripts and touch README `## Production`; land in any order but re-check
  the README prose after each. Once 006 (shellcheck hook) lands, all are
  linted automatically.

## Findings considered and rejected (so they aren't re-audited)

- **`COMPOSE_MIN_VERSION = (5, 3, 0)` is an "impossible" version**: **retracted.**
  Docker Compose uses a 5.x release scheme as of 2026 (`docker compose version` →
  `v5.3.1` on the maintainer's machine; `ci.yaml`'s smoke installs `v5.3.0`). The
  constant and the README's "Compose ≥ 5.3.0" requirement are **correct**; the
  guard fires only on genuinely-old Compose. This was a false finding from stale
  version knowledge (training data caps Compose at 2.x). Re-confirmed by the
  2026-07-07 review pass — do not re-report.
- **`/ready` does not check the Celery broker**: correct by design — the web
  readiness probe gates on what the request path needs (DB + cache), not the
  worker's broker. (Revisit only if plan 020 lands — see interaction note.)
- **No CORS / throttling / default auth**: deliberate, documented design
  decisions (**repo-root** `README.md:57` for CORS/throttling; generated
  `AGENTS.md:93-95` for auth). Token auth as an *opt-in example* → plan 013.
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
