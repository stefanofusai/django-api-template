# Plan 007: SPIKE — nonce-based CSP for script-src (verify admin and Swagger survive)

> **Executor instructions**: This is a VERIFY-THEN-MAYBE-CHANGE plan. Steps
> 1–3 are investigation with a hard decision gate; only proceed to Step 4
> (the actual change) if the gate passes. If the gate fails, the deliverable
> is the findings report in Step 5, with NO code change. Run every
> verification command and confirm the expected result. If anything in the
> "STOP conditions" section occurs, stop and report — do not improvise. When
> done, update the status row for this plan in `plans/README.md` — unless a
> reviewer dispatched you and told you they maintain the index.
>
> **Drift check (run first)**:
> `git diff --stat eee3978..HEAD -- '{{cookiecutter.project_slug}}/src/config/settings/components/csp.py' '{{cookiecutter.project_slug}}/tests/api/integration/csp_test.py' '{{cookiecutter.project_slug}}/README.md'`
> On drift, compare "Current state" excerpts before proceeding; on mismatch,
> STOP.

## Status

- **Priority**: P3
- **Effort**: M
- **Risk**: MED (a too-tight policy silently breaks admin/docs UI — hence the
  manual verification gate)
- **Depends on**: none
- **Category**: security / direction
- **Planned at**: commit `eee3978`, 2026-07-08

## Why this matters

The `use_csp=yes` knob ships `script-src 'self' 'unsafe-inline'` —
documented honestly as a "Swagger-compatible starter CSP", but
`unsafe-inline` on `script-src` means the policy provides almost no
script-injection protection, which is most of what a CSP is for. Django 6's
native CSP supports nonces (`CSP.NONCE`): the middleware generates a
per-request nonce and templates reference it, letting legitimate inline
scripts run while injected ones are blocked. If the two browser surfaces this
API-only template actually renders (django-unfold admin, django-ninja Swagger
docs) work under a nonce policy, the knob gets real teeth at zero cost to
users. If they don't, we document precisely why and keep the current policy —
either outcome is valuable.

## Current state

This repo is a **cookiecutter template**; verify by baking (always
single-quote `{{cookiecutter.project_slug}}` paths).

`{{cookiecutter.project_slug}}/src/config/settings/components/csp.py`
(entire file; renders only for `use_csp=yes`; deleted otherwise by the
post-gen hook):

```python
from django.utils.csp import CSP

SECURE_CSP = {
    "default-src": [CSP.SELF],
    "img-src": [CSP.SELF, "data:"],
    "script-src": [CSP.SELF, CSP.UNSAFE_INLINE],
    "style-src": [CSP.SELF, CSP.UNSAFE_INLINE],
}
```

The middleware (`django.middleware.csp.ContentSecurityPolicyMiddleware`) is
wired in `src/config/settings/components/middleware.py` directly after
SecurityMiddleware, guarded by the same knob. Tests:
`{{cookiecutter.project_slug}}/tests/api/integration/csp_test.py` asserts
header presence/content on responses. Docs surfaces: `/api/docs` and
`/api/v1/docs` (django-ninja Swagger UI; staff-gated in prod via
`API_DOCS_DECORATOR`, open in dev), admin at `/admin/` (django-unfold theme,
pinned `django-unfold==0.96.0` in the generated `pyproject.toml`). The root
README sells the knob as: "Enable a Swagger-compatible starter CSP for
browser-rendered surfaces" and "allows inline scripts and styles"
(README.md:101 and the What You Get list) — Step 4 must update this wording
if the policy changes.

Django 6 facts to verify (not assume) during the spike: `CSP.NONCE` placement
in `SECURE_CSP` lists; how Django template code opts in
(`request.csp_nonce` / context processor); whether contrib admin's inline
scripts are nonce-aware in Django 6, and whether unfold's and django-ninja's
bundled templates are. THE SPIKE'S CORE QUESTION is whether those third-party
templates attach the nonce; Django's own docs pages for
`SecurityMiddleware`/CSP and the unfold/django-ninja changelogs are the
sources.

**Scope split**: this spike targets `script-src` only. `style-src`
`unsafe-inline` stays (inline styles are pervasive in both surfaces and
style injection is far lower risk) — removing it is explicitly out of scope.

## Commands you will need

| Purpose | Command | Expected on success |
|---------|---------|---------------------|
| Bake | `uvx cookiecutter . -o /tmp/verify-007 --no-input use_csp=yes use_example_api=yes` | project generated |
| Boot dev stack (in bake) | `cp .env.example .env && docker compose -f .docker/compose/dev.yaml --env-file=.env up -d --build --wait` | api healthy on :8000 |
| Create staff user (in bake) | `docker compose -f .docker/compose/dev.yaml --env-file=.env exec api python manage.py createsuperuser --no-input --username=admin --email=admin@example.test` with `DJANGO_SUPERUSER_PASSWORD` env | user created |
| Probe docs | `curl -fsS http://localhost:8000/api/docs \| head -50` | HTML with script tags (inspect for nonce) |
| Suite (in bake) | `uv sync --locked && uv run pytest` (Postgres via dev compose) | all pass |
| Teardown | `docker compose -f .docker/compose/dev.yaml --env-file=.env down -v` | exit 0 |

Manual browser verification is REQUIRED for the gate (Step 3): a human (or
you, if you can drive a browser tool) must load `/admin/` and `/api/docs`
with DevTools console open and confirm zero CSP violation reports. curl can
show whether nonces are attached but cannot prove absence of runtime
violations.

## Scope

**In scope** (only IF the Step 3 gate passes):
- `{{cookiecutter.project_slug}}/src/config/settings/components/csp.py`
- `{{cookiecutter.project_slug}}/tests/api/integration/csp_test.py`
- `README.md` (root — the two knob descriptions) and
  `{{cookiecutter.project_slug}}/README.md` if it describes the CSP contents
  (grep for `unsafe-inline`/`CSP`)
- `cookiecutter.json` — the `use_csp` prompt text ("allows inline scripts and
  styles" must not survive a policy that no longer allows inline scripts)

**Out of scope**:
- `style-src` (stays `unsafe-inline` — see Current state)
- Any vendored template overrides for unfold/ninja — if nonce support
  requires overriding third-party templates, that is a gate FAILURE, not an
  invitation to maintain template forks.
- The CSP middleware wiring/order.

## Git workflow

- Branch: `advisor/007-nonce-csp`
- Single commit if the gate passes, e.g. `feat: use nonce-based CSP for scripts`;
  no commit otherwise (report only).
- Do NOT push or open a PR unless the operator instructed it.

## Steps

### Step 1: Establish current behavior (baseline)

Bake with `use_csp=yes use_example_api=yes`, boot the dev stack, and record:
the exact `Content-Security-Policy` header on `/api/docs`, `/admin/login/`,
and one API JSON response; whether the served docs/admin HTML contains inline
`<script>` blocks (curl + grep `<script>` without `src=`).

**Verify**: header present on all three; findings recorded in your report.

### Step 2: Determine nonce support in the three layers

Consult (a) Django 6 CSP docs for `CSP.NONCE` semantics, (b) django-unfold
0.96 (changelog/source: does its admin templates' inline scripts use
`{{ '{{' }} request.csp_nonce {{ '}}' }}` or Django's nonce-aware admin
blocks?), (c) django-ninja's `docs.html`-equivalent template for Swagger UI.
Conclude, per surface: nonce-attached / not nonce-attached / no inline
scripts at all.

**Verify**: three explicit verdicts with source citations in your report.

### Step 3: DECISION GATE — live nonce trial

Edit csp.py **in the baked copy only** (`/tmp/verify-007/...`):
`"script-src": [CSP.SELF, CSP.NONCE]`. Restart the api container
(`docker compose ... restart api` — dev mounts `src/`, check
`.docker/compose/dev.yaml` for whether a restart or rebuild is needed).
Load `/admin/` (log in, view a changelist, open a form) and `/api/docs`
(expand an endpoint, execute a try-it-out request) in a browser with the
console open.

**Gate passes** iff: zero CSP violations on both surfaces and both are fully
functional. **Gate fails** on any violation → skip to Step 5 (report), make
no template-repo change.

### Step 4 (gate passed only): Apply to the template

- csp.py: `"script-src": [CSP.SELF, CSP.NONCE],`
- `csp_test.py`: update assertions — the header now carries a per-request
  `'nonce-…'` token in script-src, so exact-match assertions must become
  pattern assertions; assert `unsafe-inline` is ABSENT from script-src and
  still PRESENT in style-src.
- Update root `README.md` knob wording (line ~101 and the What You Get
  bullet), the `use_csp` prompt in `cookiecutter.json`, and any generated
  README mention (grep first).

**Verify**: in fresh `use_csp=yes` and `use_csp=yes use_cors=yes` bakes:
`uv run pytest` all pass; `uvx ruff@0.15.16 format --check . && uvx ruff@0.15.16 check .`
exit 0; repeat the Step 3 browser check once on the final bake.

### Step 5: Report

Whether the gate passed or failed, write the outcome into your completion
report AND into this plan's status row: policy adopted, or the precise
violation (surface, blocked resource, source of the inline script) that
blocks it, plus — on failure — the recommended follow-up (e.g. "revisit when
unfold ships nonce support; watch its changelog").

## Test plan

- Gate-pass path: updated `csp_test.py` covers (1) script-src contains a
  nonce and not unsafe-inline, (2) style-src still contains unsafe-inline,
  (3) header present on docs and API responses. Model on the existing
  assertions in the same file.
- Gate-fail path: no tests; the report is the deliverable.

## Done criteria

- [ ] Step 2 verdicts with citations delivered
- [ ] Gate decision recorded with browser-verification evidence
- [ ] If passed: bakes green (pytest + ruff), README/cookiecutter.json wording updated, `git status` clean outside in-scope files
- [ ] If failed: no template changes (`git status` clean), report filed
- [ ] `plans/README.md` status row updated (DONE with outcome, either way)

## STOP conditions

- You cannot perform or delegate the browser verification — curl-only
  evidence is insufficient for the gate; report and stop rather than shipping
  an unverified policy.
- Nonce support would require overriding unfold/ninja templates (gate
  failure by definition — report).
- The dev stack fails to boot for reasons unrelated to CSP (pre-existing
  issue; report).

## Maintenance notes

- If the gate fails on unfold or ninja, add a watch item: both projects
  actively evolve; re-run this spike on their next major bumps.
- If it passes, future template additions that render HTML must use
  nonce-attached scripts — note this in the generated AGENTS.md only if a
  future plan adds HTML surfaces (deliberately not done now).
- Dependabot bumps of unfold/ninja could regress nonce compatibility
  silently; the csp tests assert header shape, not runtime execution — the
  residual risk is accepted (documented here for the reviewer).
