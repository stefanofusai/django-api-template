# Plan 011: Notes-slice hardening — real pagination coverage, a composite index, an authenticated contract pass, and a Hypothesis CI profile

> **Executor instructions**: This plan has three parts. Part A (pagination
> tests + index) is a straightforward do-it. Part C (Hypothesis profile) is
> small. **Part B (authenticated Schemathesis) is the hard one and has an
> explicit fallback — read its STOP/fallback before starting it.** Parts are
> independent; land A and C even if B ends in a report. Run every verification
> command. When done, update this plan's status row in `plans/README.md` —
> unless a reviewer dispatched you and told you they maintain the index.
>
> **Drift check (run first)**:
> `git diff --stat ae42991..HEAD -- "{{cookiecutter.project_slug}}/src/apps/notes" "{{cookiecutter.project_slug}}/tests/notes" "{{cookiecutter.project_slug}}/tests/api/integration/schema_test.py" "{{cookiecutter.project_slug}}/src/apps/api/pagination.py"`
> On a mismatch with "Current state", STOP. (Plan 005 edits `schema_test.py`'s
> `use_example_api=no` tail — a different region; reconcile if it landed.)

## Status

- **Priority**: P2
- **Effort**: M (A: S, B: M, C: S)
- **Risk**: LOW (A, C) / MED (B — Hypothesis-driven authenticated writes need per-example DB hygiene)
- **Depends on**: none
- **Category**: tests (+ one S perf item riding along in Part A)
- **Planned at**: commit `ae42991`, 2026-07-07

## Repository context (read before anything else)

This is a **Cookiecutter template**. Source is under
`{{cookiecutter.project_slug}}/` — **quote it in shell**; test files contain
Jinja that must stay valid. The notes app ships only when
`use_example_api=yes`, so **everything in this plan lives behind that knob**
(the notes test dir is deleted otherwise; `schema_test.py`'s notes-specific
parts are Jinja-gated). Baked project enforces **100% coverage** on `src/`.
Tests need a reachable `postgres:18.4`. Bake with
`uvx cookiecutter . --no-input -o /tmp/bake-ex use_example_api=yes`.

## Why this matters

The notes slice is the template's showcase — the pattern downstream teams
copy. Three gaps undercut it:

1. **The contract test only ever validates 401s.** `schema_test.py` runs
   Schemathesis over the v1 schema, but every notes route requires
   `django_auth` and `from_wsgi` carries no session — so every generated notes
   request is rejected, and since 401 is a documented response, the test
   passes while never checking the 200/201/204/404/422 bodies against the
   schema. The flagship correctness test validates only the auth-rejection
   branch.
2. **Pagination is never exercised end-to-end.** The only pagination tests are
   a 422-over-limit check and a single-note list. Nothing proves `limit`
   actually caps rows, `offset` skips the right rows, or the max-offset bound
   rejects. The paginator is the reusable primitive every future list endpoint
   inherits.
3. **The list query has no supporting composite index.** `list_notes` runs
   `WHERE owner_id = ? ORDER BY created_at DESC`; the model has only a
   single-column `owner` index, so Postgres re-sorts the matched rows on every
   list request. A `(owner, -created_at)` composite serves filter+order in one
   scan — and is exactly the "index implied by the query pattern" lesson an
   example slice should teach.

Plus a latent-flake tax: no Hypothesis profile is registered anywhere, so the
contract test runs with the default per-example deadline (flaky against
cold-DB first examples under `--numprocesses=auto`) and `pytest-randomly`
reseeds Hypothesis every run (failures are not reproducible without the seed).

## Current state

`{{cookiecutter.project_slug}}/src/apps/notes/models.py:8-22` — `owner` FK
with `db_index=True` only; `Meta.ordering = ("-created_at",)`; no
`Meta.indexes`. Routes: `src/apps/notes/routes.py` — `list_notes` returns
`Note.objects.filter(owner=request.user)` on a `Router(auth=django_auth,
tags=["notes"])`.

`{{cookiecutter.project_slug}}/tests/api/integration/schema_test.py` (the
`use_example_api=yes` shape):

```python
@pytest.fixture(params=["/api/openapi.json", "/api/v1/openapi.json"])
def api_schema(request: pytest.FixtureRequest) -> object:
    return schemathesis.openapi.from_wsgi(request.param, application)

schema = schemathesis.pytest.from_fixture("api_schema")

@pytest.mark.django_db(transaction=True)
@schema.parametrize()
def test_api_schema_conforms_to_openapi_contract(case: Case) -> None:
    case.call_and_validate()
```

`{{cookiecutter.project_slug}}/tests/notes/integration/notes_test.py:93-115` —
the only pagination-adjacent tests:
`test_list_notes_returns_422_when_limit_exceeds_maximum` and
`test_list_notes_returns_only_callers_notes_when_authenticated` (one note).

`{{cookiecutter.project_slug}}/src/apps/api/pagination.py` — the whole file:
`PAGINATION_MAX_LIMIT` falls back to `PAGINATION_PER_PAGE` when ninja's
default is inf; `BoundedLimitOffsetPagination.Input` bounds
`limit (ge=1, le=PAGINATION_MAX_LIMIT)` and
`offset (ge=0, le=settings.PAGINATION_MAX_OFFSET)`; ninja's
`PAGINATION_MAX_OFFSET` defaults to 100.

No `register_profile` / `@settings` / `deadline` / `max_examples` exists
anywhere under `tests/` or `pyproject.toml` (grep to confirm).

**Conventions**: tests named `test_<subject>_<expected>_when_<condition>`,
alphabetized within the file; model the structure on the existing
`notes_test.py` functions; factories via the `note_factory` fixture; Ruff
`ALL`; never `from __future__ import annotations`; private helpers at the
bottom under `# Utils`.

## Commands you will need

| Purpose | Command | Expected |
|---------|---------|----------|
| Bake example-api | `uvx cookiecutter . --no-input -o /tmp/bake-ex use_example_api=yes` | notes present |
| Bake default | `uvx cookiecutter . --no-input -o /tmp/bake` | notes absent (regression) |
| Baked tests | `cd /tmp/bake-ex/my-project && DATABASE_URL=postgres://postgres:postgres@localhost:5432/postgres uv run pytest` | 100% cov, all pass |
| Just the contract test | same, plus `tests/api/integration/schema_test.py` | pass |
| Migration check | `cd /tmp/bake-ex/my-project && ./.github/scripts/migrations-check.sh` | exit 0 (new migration is committed and complete) |
| Baked + root pre-commit | as in other plans | exit 0 |

## Scope

**In scope**:
- `{{cookiecutter.project_slug}}/src/apps/notes/models.py` — add
  `Meta.indexes` (Part A).
- `{{cookiecutter.project_slug}}/src/apps/notes/migrations/` — the new
  migration (Part A; generate, don't hand-write).
- `{{cookiecutter.project_slug}}/tests/notes/integration/notes_test.py` — new
  pagination tests (Part A).
- `{{cookiecutter.project_slug}}/tests/api/integration/schema_test.py` — the
  authenticated contract pass (Part B) and the Hypothesis profile hookup if
  local to this file (Part C).
- `{{cookiecutter.project_slug}}/tests/conftest.py` — Hypothesis profile
  registration (Part C), and any auth fixture Part B needs.

**Out of scope**:
- The `use_example_api=no` tail of `schema_test.py` (plan 005's edit).
- Any route/schema change; changing `NoteOutSchema` to "make" the contract
  pass — if the contract fails against real responses, that is a FOUND BUG:
  report it, do not paper over it.
- Ninja pagination settings values (`PAGINATION_PER_PAGE` etc.).

## Git workflow

- Work directly on `main`. Do NOT branch/commit/push/PR unless told. If asked
  to commit: Conventional Commits, e.g.
  `test: exercise pagination end-to-end and authenticate the contract test`.

## Steps

### Part A

#### Step A1: Composite index

In `models.py`, add to `Note.Meta` (keep `Meta` attribute order alphabetical —
`indexes`, `ordering`, `verbose_name`, `verbose_name_plural`):

```python
        indexes = (models.Index(fields=["owner", "-created_at"]),)
```

Generate the migration **in a bake**, then copy it back into the template:

```
cd /tmp/bake-ex/my-project
DATABASE_URL=... uv run manage.py makemigrations notes
cp src/apps/notes/migrations/0002_*.py \
   "<repo>/{{cookiecutter.project_slug}}/src/apps/notes/migrations/"
```

Check the copied file for renderable `{{`/`{%` sequences (unlikely in a
migration, but the template renders it — if the slug appears anywhere, STOP
and report). **Verify**: `./.github/scripts/migrations-check.sh` in a FRESH
bake exits 0 (proves the committed migration is complete and named
consistently).

#### Step A2: Pagination end-to-end tests

In `notes_test.py`, add (alphabetized among the existing functions; follow
their style):

- `test_list_notes_returns_second_page_when_offset_given` — create a known
  number of notes for the caller (> 1), request
  `query_params={"limit": 1, "offset": 1}`, assert `count` is the total and
  `items` contains exactly the second-newest note (ordering is
  `-created_at`; create notes with distinct timestamps — factory `created_at`
  or sequential creation both work, but assert deterministically).
- `test_list_notes_caps_items_when_limit_below_total` — create
  more notes than the requested `limit`, assert `len(items) == limit` and
  `count` == total.
- `test_list_notes_returns_422_when_offset_exceeds_maximum` — request
  `offset` = ninja's `PAGINATION_MAX_OFFSET + 1` (import
  `from ninja.conf import settings as ninja_settings` and use
  `ninja_settings.PAGINATION_MAX_OFFSET`, mirroring how `pagination.py` reads
  it), assert 422.

**Verify**: `uv run pytest tests/notes/integration/notes_test.py` (in the
bake, with `DATABASE_URL`) → all pass, including 3 new tests.

### Part B

#### Step B1: Authenticate the contract pass

Goal: Schemathesis exercises the notes operations with a real session so 2xx
responses are validated against the schema — not only 401s.

Mechanics to investigate first (read the installed packages in the bake — do
not guess): django-ninja's `django_auth` requires a session cookie **and CSRF
handling for unsafe methods**. The workable shape is usually:

1. A fixture that creates a user and a logged-in session server-side (e.g.
   Django test `Client.force_login`, then read `client.cookies`).
2. Injecting `Cookie: sessionid=...; csrftoken=...` and `X-CSRFToken: ...`
   headers into every generated case — Schemathesis supports header injection
   via `case.call_and_validate(headers=...)` or an auth/hook mechanism on the
   schema object (check the installed schemathesis version's API for the
   sanctioned way; prefer the schema-level hook so the test body stays
   one line).
3. Keeping `@pytest.mark.django_db(transaction=True)` and confirming
   Hypothesis-generated writes (POST/PUT/DELETE against real rows) leave no
   cross-example leakage — the notes routes scope everything to
   `owner=request.user`, so a single throwaway user is fine, but DELETE
   examples may consume rows other examples created; that is acceptable (the
   contract test validates responses, not row counts).

Add the authenticated pass **alongside** the anonymous one — the 401 coverage
is still worth keeping. Two parametrized tests (anonymous + authenticated), or
one test taking a fixture-injected header set, both acceptable; keep function
names descriptive per convention.

**Verify**: run the contract test and confirm from Schemathesis/Hypothesis
output (or `-v`) that notes operations now produce validated non-401
responses. A quick sanity probe: temporarily change `NoteOutSchema`'s `title`
field name in the bake and confirm the authenticated pass FAILS (then revert)
— that is the exact regression this exists to catch.

**FALLBACK / STOP**: if CSRF + session injection under Schemathesis proves
intractable after a genuine attempt (e.g. ninja's `django_auth` CSRF check
cannot be satisfied per-case), STOP Part B and write up what you tried, the
exact blocker, and the options (e.g. an `auth=` test-only bypass — NOT
acceptable to merge; a future token-auth mode from plan 013 would make this
trivial — note the dependency). Land Parts A and C regardless.

### Part C

#### Step C1: Hypothesis CI profile

In `tests/conftest.py`, register and load a profile:

```python
from hypothesis import settings as hypothesis_settings

hypothesis_settings.register_profile("ci", deadline=None, max_examples=50)
hypothesis_settings.load_profile("ci")
```

(Exact numbers: `deadline=None` kills the cold-DB flake class;
`max_examples=50` bounds runtime — adjust only if the suite's wall-clock
visibly regresses.) Note in a one-line comment why `deadline=None` exists
(cold-connection first example under xdist) — that is a constraint the code
can't show. Confirm placement satisfies Ruff import order.

**Verify**: full baked suite passes; `uv run pytest
tests/api/integration/schema_test.py -p no:randomly` and a normal randomized
run both pass (profile applies in both).

### Final regression

Full suite on `/tmp/bake-ex` (100% coverage — the new index/migration lines
are exercised by existing list tests) AND on a default bake (`/tmp/bake`,
notes absent — proves no un-gated reference leaked). Baked + root pre-commit.

## Test plan

This plan IS tests, plus one indexed migration. Net: +3 pagination tests,
+1 authenticated contract pass (or a written fallback report), +1 Hypothesis
profile. Structural pattern: the existing `notes_test.py` functions.

## Done criteria

ALL must hold:

- [ ] `Note.Meta.indexes` has the `(owner, -created_at)` composite; the migration is committed; `migrations-check.sh` exits 0 on a fresh example-api bake.
- [ ] Three new pagination tests exist and pass (offset slice, limit cap, max-offset 422).
- [ ] EITHER the contract test validates authenticated notes responses (and the sanity probe failed-then-reverted as expected), OR a written fallback report exists in this plan's status row / your report with the exact blocker.
- [ ] A Hypothesis `ci` profile (`deadline=None`, bounded `max_examples`) is registered and loaded in `tests/conftest.py`.
- [ ] Example-api bake: `uv run pytest` 100%, all pass. Default bake: unaffected, all pass.
- [ ] Baked + root pre-commit exit 0; no out-of-scope files modified; `plans/README.md` status row updated.

## STOP conditions

Stop and report (do not improvise) if:

- The generated migration contains renderable Jinja-like sequences or a
  slug-derived literal (template rendering would corrupt it).
- The authenticated contract pass hits the CSRF/session wall (see Part B
  fallback — Parts A and C still land).
- The authenticated pass reveals a REAL schema/response mismatch in the notes
  routes — that is a found bug; report it, do not adjust the schema to green
  the test.
- Coverage drops below 100% on any bake.

## Maintenance notes

- When plan 013's token-auth knob lands (if ever), revisit Part B — a token
  header is far easier to inject per-case than a session+CSRF pair, and the
  authenticated contract pass should switch to it.
- The Hypothesis profile is suite-wide: future property tests inherit
  `deadline=None`; if a test needs a deadline, set it locally.
- A reviewer should scrutinize: the migration's index ordering matches
  `Meta.ordering` (`-created_at`), and the authenticated pass actually reaches
  2xx (look for validated non-401 examples in the run output, not just green).
