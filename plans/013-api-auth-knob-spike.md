# Plan 013: Design spike — an `api_auth` bake knob for token/API-key auth (non-browser clients)

> **Executor instructions**: This is a **design/spike plan**, not a
> build-everything plan. Your deliverable is (1) a written design proposal and
> (2) a minimal, throwaway proof-of-concept that proves the leading option
> bakes and passes tests — **not** a production auth system merged into the
> template. Do NOT modify the template's committed source to ship a new auth
> mode; keep the prototype in a scratch bake or a clearly-marked worktree.
> Enumerate the decisions the maintainer must make and STOP for them. Update
> this plan's status row in `plans/README.md` when the proposal is written.
>
> **Drift check (run first)**:
> `git diff --stat ae42991..HEAD -- "{{cookiecutter.project_slug}}/src/apps/notes/routes.py" "{{cookiecutter.project_slug}}/src/config/settings/components/authentication.py" "{{cookiecutter.project_slug}}/pyproject.toml"`
> Compare "Current state" against the live code before starting; on a mismatch,
> note it in the proposal.
>
> **Naming caution**: your deliverable is a NEW file,
> `plans/013-api-auth-DESIGN.md`. Do not overwrite this plan file
> (`plans/013-api-auth-knob-spike.md`) — they share the number 013 by design.

## Status

- **Priority**: P2 (spike)
- **Effort**: M
- **Risk**: LOW (no committed files change; deliverable is a design doc + scratch PoC)
- **Depends on**: none
- **Category**: direction
- **Planned at**: commit `ae42991`, 2026-07-07 (re-verified against live code same day)

## Repository context (read before anything else)

This is a **Cookiecutter template**. Source is under `{{cookiecutter.project_slug}}/`
(**quote in shell**). Files contain Jinja. The template's philosophy is
deliberate minimalism, documented in two places: the **repo-root**
`README.md:57` ("The template deliberately ships no CORS or throttling
defaults; add them when a real consumer and policy exist") and the generated
`AGENTS.md:93-95` ("The API has no default auth. Endpoints requiring
protection must add ninja auth … never ship a mutating endpoint
unauthenticated"). Respect that stance — the goal here is to make token auth
an **opt-in, worked example**, not to impose it.

- Bake variables live in `cookiecutter.json` (+ `__prompts__`). File deletion by
  knob happens in `hooks/post_gen_project.py`.
- The baked project enforces **100% coverage** — any shipped code needs tests.
- **`.github/workflows/*` and `.agents/*` are copied without rendering.**
- Verification means baking: `uvx cookiecutter . --no-input -o /tmp/bake`.

## Why this matters

This is a template for a **Django Ninja API service**, yet the only
demonstrated authentication is `django_auth` (session cookie + CSRF), used by
the example notes router (`apps/notes/routes.py:16`,
`router = Router(auth=django_auth, tags=["notes"])`). Session+CSRF auth is designed for
browser clients sharing a cookie jar and origin. The *primary* consumers of an
API service — mobile apps, CLIs, backend-to-backend integrations — cannot
easily use it: they have no cookie jar and no CSRF token. Peer templates close
this gap (cookiecutter-django ships DRF + allauth; SaaS Pegasus ships full auth
plus API keys). django-ninja has first-class building blocks for token auth
(`ninja.security.HttpBearer`, `APIKeyHeader`) and mature ecosystem options
(`django-ninja-jwt`, `django-ninja-extra`). The absence of *any* token/API-key
example is the single most notable capability gap for this template's stated
purpose. The value of this spike is a clear, evidence-based recommendation the
maintainer can accept or reject — not a large speculative build.

## Current state (the facts the proposal must build on)

- `apps/notes/routes.py` uses `from ninja.security import django_auth` and
  `Router(auth=django_auth, tags=["notes"])`. Endpoints scope to
  `owner=request.user` (ownership checks already correct).
- `tests/conftest.py` provides `authenticated_v1_api_client` via
  `tests/utils.py`'s `AuthenticatedTestClient(v1_api_client, user)` — it
  authenticates by attaching a `user` to the ninja `TestClient` request, not by
  issuing a real token. A token-auth example needs a parallel client fixture.
- `authentication.py` component sets `AUTH_USER_MODEL = "core.User"` (custom
  user, unique email), Argon2 hashers, standard validators. No token model,
  no DRF, no JWT dependency in `pyproject.toml`.
- `apps/api/api.py` builds `v1_api` with no global `auth=`. Per `AGENTS.md`:
  "add ninja auth (global `auth=` on the API instance, or per-router/per-
  operation); never ship a mutating endpoint unauthenticated."
- The Schemathesis contract test (`schema_test.py`) calls every operation; any
  auth scheme must keep the schema valid and the contract test green (note it
  already handles `401`/`403` responses for the notes routes).

## The design questions this spike must answer

The proposal (deliverable 1) must make a recommendation on each, with rationale
grounded in the constraints above:

1. **Which mechanism**, as the default `api_auth` example:
   - `ninja.security.HttpBearer` with app-issued opaque DB-backed tokens
     (simplest; a small `Token` model + issue/revoke; no new dependency).
   - JWT via `django-ninja-jwt` (stateless, refresh tokens; adds a dependency
     and key-management surface).
   - `APIKeyHeader` API keys (service-to-service; hashed keys, prefix lookup).
   - Evaluate against: dependency weight (the template pins exact versions and
     avoids speculative abstractions), statelessness vs revocation, and fit with
     the existing custom-user model.
2. **Knob shape**: `api_auth: [none, token, jwt, api-key]`? Or a single
   `token`/`none` to stay minimal? What is the default (recommend `none` or
   `session`, preserving today's behavior for existing bakes)?
3. **How it composes with the notes example** (`use_example_api`): does the
   notes router switch to the chosen scheme when `api_auth != none`, or stay on
   `django_auth`? What does the matrix of (`use_example_api` × `api_auth`) look
   like, and which combinations does CI need to cover?
4. **Credential provisioning**: is a token-issue endpoint / management command
   in scope, or out (see related direction note in `plans/README.md`)? A token
   scheme is useless without a way to mint a token.
5. **Testing**: the shape of a real-token client fixture (issue a token, send
   `Authorization: Bearer …`), and how the Schemathesis contract test
   authenticates (or is exempted) so it stays green.
6. **Dependencies & migrations**: exact packages/versions if any; whether a new
   model + migration is introduced and in which app (`core` vs a new `tokens`
   app); coverage implications (100% gate).

## Deliverables

1. **`plans/013-api-auth-DESIGN.md`** (create): the proposal — recommendation
   per question above, the proposed `cookiecutter.json` knob + `__prompts__`
   text, the file inventory a follow-up build plan would touch, the
   `hooks/post_gen_project.py` deletions the knob implies, the CI matrix
   additions, and an explicit "open questions for the maintainer" list.
2. **A throwaway proof-of-concept** proving the leading option is real: in a
   **scratch bake** (`/tmp/bake-poc/my-project`) — NOT in the template's
   committed files — implement the minimal version (e.g. `HttpBearer` + a
   `Token` model + one authenticated route + one test issuing and using a
   token) and show it bakes, migrates, and passes `uv run pytest` at 100%
   coverage. Capture the exact diffs/files in the DESIGN doc as the concrete
   basis for a future build plan.

## Commands you will need

| Purpose | Command | Expected |
|---------|---------|----------|
| Bake for PoC | `uvx cookiecutter . --no-input -o /tmp/bake-poc use_example_api=yes` | scratch project to prototype in |
| Read django-ninja auth | inspect `.venv/.../site-packages/ninja/security/` in the bake | confirm `HttpBearer`/`APIKeyHeader` API |
| PoC tests | `cd /tmp/bake-poc/my-project && DATABASE_URL=postgres://postgres:postgres@localhost:5432/postgres uv run pytest` | all pass, 100% cov (needs postgres:18.4) |
| Check ecosystem option | (if evaluating JWT) confirm latest `django-ninja-jwt` release + Django 6 compatibility | note version + compat in DESIGN |

## Scope

**In scope**:
- `plans/013-api-auth-DESIGN.md` (create — the proposal).
- A scratch proof-of-concept under `/tmp/` (not committed to the template).
- Updating this plan's status row in `plans/README.md`.

**Out of scope** (explicitly — do NOT do these in this spike):
- Modifying any committed file under `{{cookiecutter.project_slug}}/` to ship a
  new auth mode. That is the follow-up build plan, written only after the
  maintainer accepts the design.
- Adding a dependency to the template's `pyproject.toml`.
- Changing `apps/notes/routes.py`, `authentication.py`, `api.py`, or
  `cookiecutter.json` in the committed template.

## Steps

### Step 1: Survey the options against the constraints

Read django-ninja's `security` module in a bake's venv to confirm the exact
`HttpBearer` / `APIKeyHeader` interfaces. Check the latest `django-ninja-jwt`
release and whether it declares Django 6 / Python 3.14 support. Record findings.

**Verify**: DESIGN doc has a filled comparison table (mechanism × dependency
weight × statelessness × revocation × user-model fit).

### Step 2: Build the minimal proof-of-concept for the leading option

In `/tmp/bake-poc/my-project` (scratch), implement the smallest real version of
the recommended mechanism: a `Token` model (if DB-backed) or the JWT wiring, a
custom `HttpBearer` (or scheme) that resolves `request.user`, one protected
example route, and one test that **issues a token and calls the route with
it**. Keep it faithful to the template's conventions (model `__str__`,
`Meta.ordering`, admin registration and `extra_checks` requirements; ruff
`ALL`; test naming) so the PoC doubles as the build plan's reference.

**Verify**: `uv run pytest` in the scratch bake passes at 100% coverage;
`git add -A && uv run pre-commit run --all-files` in the scratch bake exits 0.

### Step 3: Write the design proposal

Populate `plans/013-api-auth-DESIGN.md` with: the recommendation and why; the
proposed knob + prompts; the (`use_example_api` × `api_auth`) composition
decision; the full file inventory + hook deletions a build plan would need; the
CI matrix additions; the PoC diffs as an appendix; and the **open questions for
the maintainer** (default value, whether provisioning endpoints are in scope,
whether to replace or complement `django_auth` in the notes example).

**Verify**: a reader who has not seen this session can, from the DESIGN doc
alone, decide yes/no and — if yes — hand a follow-up build plan to an executor.

### Step 4: STOP and present

Do not proceed to modify the committed template. Report the recommendation and
the open questions. The maintainer's answers become the inputs to a follow-up
build plan (a new `plans/0NN-…` file at the next free number).

## Done criteria

ALL must hold:

- [ ] `plans/013-api-auth-DESIGN.md` exists and answers all six design questions with a clear recommendation.
- [ ] A scratch PoC exists and its `uv run pytest` passes at 100% coverage (paste the command output into the DESIGN doc).
- [ ] The DESIGN doc lists the exact file inventory + hook deletions + CI matrix a build plan would need.
- [ ] The DESIGN doc has an explicit "open questions for the maintainer" section.
- [ ] **No committed file under `{{cookiecutter.project_slug}}/` or `cookiecutter.json` was modified** (`git status` shows only `plans/` changes).
- [ ] `plans/README.md` status row updated.

## STOP conditions

Stop and report (do not improvise) if:

- The recommended mechanism would require a dependency that lacks Django 6 /
  Python 3.14 support — report the compatibility wall and fall back to the
  no-dependency `HttpBearer` option.
- The PoC cannot reach 100% coverage without contortion — report why; it informs
  the knob/design.
- You find yourself wanting to edit the committed template — that is out of
  scope for a spike; STOP.
- The maintainer's intent (whether token auth belongs in the template at all,
  given its minimalism stance) is unclear — surface it as the first open
  question rather than assuming.

## Maintenance notes

- This spike's output is a decision aid. The actual implementation is a separate
  build plan, written only after the maintainer chooses among the open
  questions.
- Related direction finding (credential provisioning: registration / login /
  password-reset endpoints) is tracked separately in `plans/README.md`'s
  direction notes; question 4 here scopes how much of it this knob must pull in.
- Keep the recommendation honest about the minimalism trade-off: the maintainer
  may legitimately decide the template should stay auth-agnostic and document
  patterns instead of shipping a knob. Present that as a valid outcome.
