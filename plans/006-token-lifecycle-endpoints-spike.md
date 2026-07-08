# Plan 006: SPIKE — design token lifecycle endpoints (evaluate django-allauth headless first)

> **Executor instructions**: This is a DESIGN/INVESTIGATION plan, not a build
> plan. The deliverable is a written design document — you must NOT modify any
> file outside `plans/`. Follow the steps, answer every question in the
> deliverable template, and STOP at the decision point. When done, update the
> status row for this plan in `plans/README.md` — unless a reviewer dispatched
> you and told you they maintain the index.
>
> **Drift check (run first)**:
> `git diff --stat eee3978..HEAD -- '{{cookiecutter.project_slug}}/src/apps/core/models.py' '{{cookiecutter.project_slug}}/src/apps/api/auth.py' '{{cookiecutter.project_slug}}/src/apps/core/admin.py'`
> On drift, re-read those files before writing the design.

## Status

- **Priority**: P3
- **Effort**: M (investigation + design doc; implementation is a future plan)
- **Risk**: LOW (no code changes)
- **Depends on**: plans/002-token-auth-inactive-users.md (soft — the design
  must assume its `is_active` semantics)
- **Category**: direction
- **Planned at**: commit `eee3978`, 2026-07-08

## Why this matters

When the template is baked with `api_auth=token`, there is **no way to mint a
usable token except `Token.issue()` in a Django shell**: the notes controller
only consumes tokens, and `TokenAdmin`
(`src/apps/core/admin.py`) is a plain ModelAdmin — creating a Token row
through it stores whatever digest the operator types, which authenticates
nothing (real digests are SHA-256 of a `pat_<prefix>_<secret>` string only
`Token.issue()` can produce, and the raw token must be shown exactly once).
Every real project baked from this template must immediately hand-roll token
management. The maintainer wants a design for first-class lifecycle endpoints
— and explicitly asked to first check whether **django-allauth's headless
mode** (https://docs.allauth.org/en/dev/headless/) already provides this
before designing anything bespoke.

## Current state (facts to design against)

- `Token` model (`{{cookiecutter.project_slug}}/src/apps/core/models.py`,
  rendered for `use_example_api=yes api_auth=token`): fields `expires_at`
  (nullable), `last_used_at` (minute-granular via `mark_used()`), `user` (FK,
  CASCADE, `related_name="tokens"`), `digest` (unique, SHA-256 hex), `name`
  (100 chars), `prefix` (indexed, 12 chars). Classmethod
  `Token.issue(*, expires_at=None, name, user) -> tuple[raw_token, Token]` —
  the ONLY producer of valid tokens. Raw format:
  `pat_<12-hex-prefix>_<43-char-urlsafe-secret>`.
- Auth (`src/apps/api/auth.py`): `BearerTokenAuth(HttpBearer)` — digest+prefix
  lookup, expiry check, (post plan 002) `is_active` check, `mark_used()`,
  sets `request.user`.
- API composition (`src/apps/api/api.py`): `internal_api` (NinjaAPI, probes)
  and `v1_api` (NinjaExtraAPI when the example API is on;
  `register_controllers(NotesController)`). Business endpoints live under
  `/api/v1/`; controllers follow the ninja-extra class-based pattern of
  `src/apps/notes/controllers.py` (auth per controller, explicit response
  schema maps incl. 401/403/422, `Status[...]` returns).
- Bake-time reality: everything token-related renders ONLY when
  `use_example_api=yes AND api_auth=token`; `hooks/post_gen_project.py`
  deletes it otherwise. A token-lifecycle feature must either live under the
  same guard or force a knob redesign — the design doc must address this.
- Throttling: when `api_throttling=basic`, `/api/v1/` anonymous requests are
  budget-limited (`src/apps/api/throttling.py`); token-issuance endpoints are
  authentication-adjacent and need explicit thought about limits.
- Settled maintainer decisions that bind this design (from
  `plans/README.md` + memory): Sentry/env/config conventions; env vars only
  for secrets/topology/sizing; "auth scaffolding" was earlier deferred as
  direction — this spike IS that follow-up, scoped to tokens only.

## Commands you will need

| Purpose | Command | Expected on success |
|---------|---------|---------------------|
| Read allauth headless docs | WebFetch/browse https://docs.allauth.org/en/dev/headless/ (and /dev/headless/openapi-specification/ if present) | facts for Step 1 |
| Bake reference project | `uvx cookiecutter . -o /tmp/verify-006 --no-input use_example_api=yes api_auth=token` | project to inspect |

## Scope

**In scope**: creating ONE new file,
`plans/006-token-lifecycle-design.md` (the deliverable), and updating this
plan's status row in `plans/README.md`.

**Out of scope**: ANY change under `{{cookiecutter.project_slug}}/`, hooks,
or workflows. No dependencies added. No implementation.

## Git workflow

- Branch: work directly on the current branch is acceptable (plans/ is
  currently untracked); if committing, `docs: add token lifecycle design`.
- Do NOT push.

## Steps

### Step 1: Evaluate django-allauth headless (the maintainer's explicit question)

Read the current headless docs and answer, with citations (URL + section):

1. Does allauth headless provide **user-managed, named, long-lived API
   tokens** (PAT-style: create named token, list, revoke, optional expiry)?
   Or only *auth-session* artifacts (session tokens / access tokens tied to
   login flows)? (As of the audit's knowledge: headless focuses on
   login/signup/2FA flows for SPAs with session or access tokens and
   an app-client model — likely adjacent-but-different. VERIFY against
   current docs; do not trust this parenthetical.)
2. If it does offer something equivalent: what would adopting it cost?
   (new dependency + its transitive surface, INSTALLED_APPS/middleware/urls
   footprint, how its token storage compares to the existing `Token` model,
   migration/replacement of `BearerTokenAuth`, interaction with django-axes
   lockout, whether it can be knob-gated as cleanly as the current
   `api_auth=token` machinery.)
3. Recommendation: adopt / don't adopt / adopt-partially, in ≤ 5 sentences,
   grounded in 1–2.

### Step 2: Inventory the bespoke design space

From the baked reference project, document: exact current Token semantics
(model excerpt), the controller conventions a `TokensController` must follow
(auth declaration, response maps, pagination, schema module placement,
test layout `tests/<app>/{integration,unit}/`), and the admin gap
(`TokenAdmin` cannot mint — decide: remove add permission, or wire
`Token.issue` into an admin action?).

### Step 3: Write the design doc (`plans/006-token-lifecycle-design.md`)

Required sections:

- **Allauth headless verdict** (Step 1 output).
- **Proposed API** (if bespoke): endpoints under `/api/v1/tokens` —
  create (auth: how does the FIRST token get created? session auth for
  browser users; document the bootstrap story explicitly), list (id, name,
  prefix, created_at, expires_at, last_used_at — NEVER digest), revoke
  (delete vs setting `expires_at=now` — pick one, justify vs audit trails),
  show-once semantics for the raw token (response schema, and the explicit
  statement that it is never retrievable again).
- **Auth matrix**: which auth guards each endpoint (session? existing token?
  both?) and why; axes/throttling interaction.
- **Knob placement**: stays under `use_example_api=yes api_auth=token`, or
  motivates promoting token auth to a standalone knob (list the files whose
  Jinja guards change — the audit counted at least models.py, auth.py,
  exceptions.py, admin.py, migrations 0002, conftest.py, factories, and
  hooks/post_gen_project.py).
- **Admin fix** decision from Step 2.
- **Test plan sketch** per repo conventions (unit for model/schema,
  integration for endpoints; 100% coverage implications).
- **Open questions for the maintainer** (≤ 5, each with your recommended
  answer).
- **Effort estimate** for the build plan (S/M/L with 2-sentence basis).

### Step 4: Update the index

Set plan 006's status in `plans/README.md` to DONE with a one-line pointer to
the design doc.

## Done criteria

- [ ] `plans/006-token-lifecycle-design.md` exists with every required section
- [ ] Allauth headless verdict includes at least two doc citations
- [ ] No file outside `plans/` modified (`git status`)
- [ ] `plans/README.md` status row updated

## STOP conditions

- The allauth docs URL is unreachable AND no cached/alternative source
  (PyPI description, GitHub README) suffices — report rather than guessing.
- You find an existing third-party django-ninja-native token-management app
  that changes the build-vs-buy calculus — surface it in the doc's verdict
  section rather than expanding the investigation unbounded.

## Maintenance notes

- The design doc is input to a future build plan; nothing ships from this
  spike.
- If plan 002 changed `is_active` semantics further by the time this runs,
  reflect that in the auth matrix.
