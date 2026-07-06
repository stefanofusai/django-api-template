# Plan 009: Ship an optional example resource showing the full API pattern

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving to the
> next step. If anything in the "STOP conditions" section occurs, stop and
> report — do not improvise. When done, update the status row for this plan
> in `plans/README.md` — unless a reviewer dispatched you and told you they
> maintain the index.
>
> **Drift check (run first)**:
> `git diff --stat d333a73..HEAD -- cookiecutter.json hooks/post_gen_project.py '{{cookiecutter.project_slug}}/src' '{{cookiecutter.project_slug}}/tests' .github/workflows/ci.yaml README.md`
> Plans 001-003/008 legitimately change some of these — read their diffs
> and integrate. On any OTHER unexplained mismatch with the excerpts
> below, STOP.

## Status

- **Priority**: P2
- **Effort**: L
- **Risk**: MED — touches the knob system, hooks, CI matrix, and the
  100%-coverage suite
- **Depends on**: 001, 002 (hard — its migration and tests build on
  them); 008 (hard — its endpoints activate the v1 Schemathesis
  coverage and must satisfy it)
- **Category**: direction
- **Planned at**: commit `d333a73`, 2026-07-05

## Why this matters

A fresh bake advertises a "production-minded API service" yet `/api/v1/`
serves zero routes: `v1_api` is instantiated and mounted but no
`add_router` call exists. Meanwhile every supporting convention ships
unused — `BoundedLimitOffsetPagination` has no consumer, the
`UUIDModel`/`CreatedAt*` abstract bases have no concrete model besides
`User`, `AGENTS.md` prescribes a router/auth/testing pattern with no
concrete example to copy, and the API "ships unauthenticated" with only
a doc link at the exact moment a user writes their first protected
endpoint. This plan adds ONE vertical slice — model → migration →
schemas → authenticated CRUD router → factory → tests — behind a new
`use_example_api` knob **defaulting to `no`** so default output is
unchanged (the template's established rule: defaults reproduce the
historical bake byte-for-byte).

Maintainer-taste decisions baked in: session auth (`ninja.security
.django_auth`) because it needs zero new dependencies and pairs with the
existing staff-gated docs; ownership-scoped queries; explicit error
response schemas so Schemathesis stays green.

## Current state

Cookiecutter template. Generated project under the literal
`{{cookiecutter.project_slug}}/` directory; `.github/workflows/*` and
`.agents/*` copy without rendering. Knob machinery: choice knobs live in
`cookiecutter.json` with `__prompts__` entries; whole-file/dir removal
happens in `hooks/post_gen_project.py` `REMOVED_PATHS` (currently
files-only via `Path.unlink()` — this plan needs directory removal);
inline conditionals use Jinja.

- `{{cookiecutter.project_slug}}/src/apps/api/api.py` — full content:

  ```python
  from django.conf import settings
  from django.utils.module_loading import import_string
  from ninja import NinjaAPI

  from config.pyproject import project_name

  from .routes import health_router, ready_router

  docs_decorator = import_string(settings.API_DOCS_DECORATOR)

  internal_api = NinjaAPI(
      title=f"{project_name} (internal)",
      docs_decorator=docs_decorator,
      urls_namespace="internal",
  )
  internal_api.add_router("", health_router)
  internal_api.add_router("", ready_router)

  v1_api = NinjaAPI(
      title=project_name,
      version="1.0.0",
      docs_decorator=docs_decorator,
      urls_namespace="v1",
  )
  ```

- `{{cookiecutter.project_slug}}/src/apps/core/models.py` — abstract
  bases `CreatedAtModel`, `CreatedAtUpdatedAtModel`, `UUIDModel`
  (uuid7 PK), and concrete `User(AbstractUser)`.

- `{{cookiecutter.project_slug}}/src/apps/api/pagination.py` —
  `BoundedLimitOffsetPagination` (unused today).

- `{{cookiecutter.project_slug}}/src/apps/core/admin.py` — the admin
  exemplar (unfold `ModelAdmin`), to imitate.

- `{{cookiecutter.project_slug}}/src/config/settings/components/apps.py`
  — `INSTALLED_APPS` with `# Project` section listing `apps.api`,
  `apps.core` (alphabetical).

- `{{cookiecutter.project_slug}}/tests/factories.py`, `tests/conftest.py`
  — `UserFactory` + `register(UserFactory)`; pytest-factoryboy provides
  the `user` fixture.

- `{{cookiecutter.project_slug}}/tests/integration/api/versioning_test.py`
  — contains
  `test_v1_api_serves_empty_openapi_schema_when_template_is_fresh`
  (asserts `paths == {}`) and
  `test_v1_api_serves_no_routes_when_template_is_fresh` — both are TRUE
  only when the knob is off; they must become knob-conditional.

- `.github/workflows/ci.yaml` `bake` job matrix — 9 cases; new knob
  variants belong here (alphabetical case names).

- Baked `AGENTS.md` rules the example must satisfy (quoted):
  - "Respect `django-extra-checks`: models need `__str__`,
    `Meta.ordering`, admin registration, gettext verbose/help text,
    explicit FK `related_name` and `db_index`, choice constraints, and
    `UniqueConstraint` instead of `unique_together`."
  - "never ship a mutating endpoint unauthenticated."
  - "Keep Django Ninja routers resource-oriented. Mount resource routers
    at their resource prefix and keep route-local paths relative."
  - "Mount business routers on `v1_api` (under `/api/v1/`)."
  - Test naming/alphabetization/factory rules (Testing section).

- Root `README.md` — Variables table (alphabetical) and "What You Get"
  bullets; `cookiecutter.json` `__prompts__` for every knob.

- Plan 008 (prerequisite) made Schemathesis load
  `/api/v1/openapi.json`. `case.call_and_validate()` fails on
  *undocumented* response codes, so every operation here must declare
  its error responses (401/404) explicitly.

## Commands you will need

| Purpose | Command | Expected on success |
|---------|---------|---------------------|
| Bake knob ON | `uvx cookiecutter . --no-input -o /tmp/plan009 use_example_api=yes` | baked with `apps/notes` |
| Bake default | `uvx cookiecutter . --no-input -o /tmp/plan009off` | NO `apps/notes` anywhere |
| Diff default vs pre-change default | see Step 8 | byte-identical |
| Suite | `uv sync --locked && uv run pytest` (Postgres running per plan 001) | pass, 100% cov |
| Migrations gate | `./.github/scripts/migrations-check.sh` (from plan 002) | exit 0 |
| Baked pre-commit | `git add -A && uv run pre-commit run --all-files` | exit 0 |
| Root pre-commit | `pre-commit run --all-files` | exit 0 |

## Scope

**In scope**:

- `cookiecutter.json` (knob + prompt)
- `hooks/post_gen_project.py` (knob constant, `REMOVED_DIRS` mechanism,
  entries)
- Create: `{{cookiecutter.project_slug}}/src/apps/notes/` (`__init__.py`,
  `admin.py`, `apps.py`, `models.py`, `schemas.py`, `routes.py`,
  `migrations/`)
- Modify: `src/apps/api/api.py`, `src/config/settings/components/apps.py`
  (Jinja-gated lines)
- Create: `tests/integration/api/notes_test.py`; modify:
  `tests/factories.py`, `tests/conftest.py`,
  `tests/integration/api/versioning_test.py`,
  `tests/integration/api/schema_test.py` (only if auth headers needed —
  see Step 6)
- `.github/workflows/ci.yaml` (one new bake matrix case)
- Root `README.md` (Variables row + What You Get bullet); baked
  `README.md` (short Usage note, gated)

**Out of scope** (do NOT touch):

- `apps/core` models/admin (the example gets its own app so the knob
  strips cleanly).
- Any auth beyond `django_auth` (token/JWT knobs are recorded as
  deferred direction — do not add dependencies).
- `pagination.py`, `internal_api`.

## Git workflow

- Work directly on `main`; do not create or switch to a plan branch unless the
  operator explicitly asks.
- Do NOT commit, push, or open a PR unless the operator explicitly instructs it.
- If asked to commit, use a conventional commit such as
  `feat: add use_example_api knob with notes resource`.

## Steps

### Step 1: Add the knob

`cookiecutter.json`: add `"use_example_api": ["no", "yes"]` positioned
alphabetically among the knobs (after `use_celery`, before
`use_s3_media`), and a `__prompts__` entry:

```json
"use_example_api": {
    "__prompt__": "Example notes API resource",
    "no": "Ship an empty /api/v1/",
    "yes": "Include the example notes model, router, and tests"
}
```

Update root `README.md` Variables table (alphabetical row) and add a
"What You Get" bullet ("Optional example `notes` resource demonstrating
the model-to-tests vertical slice").

**Verify**: `uvx cookiecutter . --no-input -o /tmp/plan009knob
use_example_api=yes` bakes; `use_example_api=bogus` fails (cookiecutter
rejects non-choice values — matches the existing `bad-knob` CI case
pattern).

### Step 2: Create the notes app

All files ship render-plain (no Jinja inside the app — the knob removes
the whole directory). Follow `apps/core` style throughout.

`src/apps/notes/models.py`:

```python
from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.models import CreatedAtUpdatedAtModel, UUIDModel


class Note(UUIDModel, CreatedAtUpdatedAtModel):
    body = models.TextField(_("body"), blank=True)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        db_index=True,
        on_delete=models.CASCADE,
        related_name="notes",
        verbose_name=_("owner"),
    )
    title = models.CharField(_("title"), max_length=200)

    class Meta:
        ordering = ("-created_at",)
        verbose_name = _("note")
        verbose_name_plural = _("notes")

    def __str__(self) -> str:
        return self.title
```

(Field order: Django semantic constraints allow alphabetical here; keep
`id` implicit from `UUIDModel`. django-extra-checks requirements — see
Current state — must all pass; run the suite early to catch any missed
check like `H*` codes and fix per its messages.)

`apps.py`: `NotesConfig` with `name = "apps.notes"`. `admin.py`:
register `Note` with an unfold `ModelAdmin` mirroring
`apps/core/admin.py`'s import style (a plain
`@admin.register(Note)\nclass NoteAdmin(ModelAdmin): ...` with
`list_display = ("title", "owner", "created_at")`). `__init__.py` empty.

**Verify**: nothing yet — compiles in Step 5's bake.

### Step 3: Schemas and authenticated CRUD router

`src/apps/notes/schemas.py` — explicit ninja `Schema` classes
(alphabetical class order):

```python
import uuid
from datetime import datetime

from ninja import Schema


class NoteInSchema(Schema):
    body: str = ""
    title: str


class NoteOutSchema(Schema):
    body: str
    created_at: datetime
    id: uuid.UUID
    title: str
    updated_at: datetime
```

`src/apps/notes/routes.py` — resource-oriented router, session auth,
ownership scoping, explicit error responses (Schemathesis conformance
requires documenting 401 on every operation and 404 on detail
operations; ninja's default auth failure returns
`{"detail": "Unauthorized"}` with 401, and `Http404` maps to a 404
`{"detail": ...}`). Use a shared error schema:

```python
from http import HTTPStatus
from uuid import UUID

from django.http import HttpRequest
from django.shortcuts import get_object_or_404
from ninja import Router, Schema, Status
from ninja.pagination import paginate
from ninja.security import django_auth

from apps.api.pagination import BoundedLimitOffsetPagination

from .models import Note
from .schemas import NoteInSchema, NoteOutSchema


class ErrorSchema(Schema):
    detail: str


router = Router(auth=django_auth, tags=["notes"])
```

Operations (keep ninja decorator/response typing style consistent with
`routes/health.py` — `response={...}` dicts and `Status[...]` returns):

- `GET ""` → `list[NoteOutSchema]` via
  `@paginate(BoundedLimitOffsetPagination)`, queryset
  `Note.objects.filter(owner=request.user)`; responses: 200 (+401 via a
  router-level documented response — ninja cannot attach 401 globally,
  so declare `response={200: list[NoteOutSchema], 401: ErrorSchema}`;
  note `@paginate` wraps the 200 response envelope — follow
  django-ninja's documented pagination+response-dict interplay; if the
  two genuinely cannot compose in the pinned ninja version, the
  401-declaration fallback is an `openapi_extra` responses entry — pick
  whichever the pinned `django-ninja==1.6.2` supports and record it).
- `POST ""` → 201 `NoteOutSchema`, create with `owner=request.user`;
  responses 201/401.
- `GET "/{note_id}"` → 200/401/404; fetch with
  `get_object_or_404(Note, id=note_id, owner=request.user)` (ownership
  scoping makes another user's note indistinguishable from absent).
- `PUT "/{note_id}"` → 200/401/404; update `body`/`title` from
  `NoteInSchema`, save.
- `DELETE "/{note_id}"` → 204/401/404 (204 response `None`).

Wire-up (Jinja-gated lines):

- `api.py`: after the `v1_api` block add

  ```python
  {%- if cookiecutter.use_example_api == "yes" %}
  from apps.notes.routes import router as notes_router

  v1_api.add_router("/notes", notes_router)
  {%- endif %}
  ```

  (Import placement: module top would be cleaner Ruff-wise — put the
  gated import with the other imports and only the `add_router` call
  below; check the rendered file passes Ruff in BOTH knob states.)
- `apps.py` settings component: gated `"apps.notes",` in the `# Project`
  section (alphabetical: after `apps.api`, before `apps.core`? —
  alphabetical is api, core, notes; put it after `apps.core`).

**Verify**: Step 5 bake compiles; `/api/v1/docs` renders the notes
operations.

### Step 4: Generate the migration

In a knob-ON bake with deps installed, run the env-prefixed
`manage.py makemigrations notes` (same env prefix as plan 002 Step 2),
then copy the generated `0001_initial.py` back into the template at
`src/apps/notes/migrations/0001_initial.py` (plus an empty
`migrations/__init__.py`). The file is render-plain — verify it contains
no project-specific strings (it references `settings.AUTH_USER_MODEL`,
so it is slug-independent).

**Verify**: fresh knob-ON bake passes
`./.github/scripts/migrations-check.sh` (no drift) — this is plan 002's
gate doing its job.

### Step 5: Factory and tests

- `tests/factories.py` (gated block):

  ```python
  {%- if cookiecutter.use_example_api == "yes" %}


  class NoteFactory(factory.django.DjangoModelFactory):
      body = factory.Faker("paragraph")
      owner = factory.SubFactory(UserFactory)
      title = factory.Faker("sentence")

      class Meta:
          model = Note
  {%- endif %}
  ```

  with the gated `from apps.notes.models import Note` import.
- `tests/conftest.py`: gated `register(NoteFactory)` + import.
- `tests/integration/api/notes_test.py` — render-plain file, removed by
  the hook when the knob is off. Cover (alphabetized test functions,
  AGENTS naming; use the django `client` fixture + `client.force_login`;
  `pytestmark = pytest.mark.django_db`):
  1. anonymous `GET /api/v1/notes` → 401
  2. anonymous `POST /api/v1/notes` → 401
  3. create → 201, response matches input, `owner` is the logged-in user
     (assert via ORM)
  4. list returns only the caller's notes (create one via `NoteFactory`
     for another user, one for the caller) and honors the pagination
     envelope (`{"items": [...], "count": 1}`)
  5. list `?limit=<PAGINATION_MAX_LIMIT+1>` → 422 (bounded pagination
     rejects over-limit)
  6. detail/update/delete happy paths (200/200/204)
  7. detail of another user's note → 404 (ownership scoping)
  8. update/delete of another user's note → 404
- `tests/integration/api/versioning_test.py`: wrap the two
  "when_template_is_fresh" tests in
  `{% if cookiecutter.use_example_api == "no" %}…{% endif %}` and add
  knob-ON counterparts in the `else` branch
  (`test_v1_api_exposes_notes_paths_when_example_api_is_enabled`
  asserting `"/api/v1/notes" rendered path prefix in schema["paths"]`).
  Check rendered whitespace both ways.
- Schemathesis (from plan 008) now generates cases against the notes
  operations **unauthenticated**, expecting documented 401s — that's
  exactly what the explicit `401: ErrorSchema` declarations satisfy. If
  `call_and_validate` still fails (e.g. ninja's 422 validation responses
  undocumented), declare 422 responses where ninja emits them
  (`ninja` auto-documents 422 for request validation — verify in the
  rendered openapi.json) and record what was needed.

**Verify**: knob-ON bake: `uv run pytest` → all pass, 100% coverage
(the coverage gate forces every route branch to be exercised — add
tests until green).

### Step 6: Hook removal for the knob-OFF bake

`hooks/post_gen_project.py`:

- Add `USE_EXAMPLE_API = {{ cookiecutter.use_example_api | tojson }}`
  (alphabetical constants).
- Add a `REMOVED_DIRS` list + `shutil.rmtree` loop in `main()` (mirror
  the `REMOVED_PATHS` loop; `shutil` is already imported):

  ```python
  REMOVED_DIRS = [
      *(["src/apps/notes"] if USE_EXAMPLE_API == "no" else []),
  ]
  ```

- Add to `REMOVED_PATHS`:
  `*(["tests/integration/api/notes_test.py"] if USE_EXAMPLE_API == "no" else [])`.

**Verify**: default bake → `find . -path '*apps/notes*'` empty,
`notes_test.py` absent, suite passes, `grep -rn "notes"` in the baked
`src/`+`tests/` returns nothing.

### Step 7: CI matrix case

Add to the `bake` job matrix (alphabetical case name):

```yaml
          - case: example-api
            project_name: My Project
            extra-args: use_example_api=yes
            slug: my-project
```

**Verify**: `uvx --from actionlint actionlint .github/workflows/ci.yaml`
→ exit 0.

### Step 8: Default-output byte-identity check

The template rule: knob defaults reproduce the pre-knob output.

```shell
git stash --include-untracked   # pristine template
uvx cookiecutter . --no-input -o /tmp/plan009-before
git stash pop
uvx cookiecutter . --no-input -o /tmp/plan009-after
diff -r /tmp/plan009-before/my-project /tmp/plan009-after/my-project
```

**Verify**: `diff -r` reports NO differences (uv.lock may differ only if
deps changed — this plan adds none, so it must be identical too).

### Step 9: Full verification

Knob-ON and knob-OFF (default) bakes: suite, migrations-check,
pre-commit; root pre-commit; baked README gains a short gated Usage
sentence pointing at `/api/v1/docs` for the example endpoints.

**Verify**: everything exits 0.

## Test plan

Step 5 is the test plan (8+ integration tests, factory, versioning-test
rework). Pattern files: `docs_test.py` / `models_test.py` /
`ready_test.py`. The 100%-coverage gate is the completeness backstop.

## Done criteria

- [ ] Default bake byte-identical to pre-plan output (Step 8 diff empty)
- [ ] Knob-ON bake: suite green at 100%, migrations-check green,
      pre-commit green, `/api/v1/openapi.json` documents the notes
      operations with 401/404 responses
- [ ] Knob-OFF bake contains zero traces of the example
- [ ] Schemathesis passes against the populated v1 schema
- [ ] CI matrix includes `example-api`; actionlint green
- [ ] Root README Variables/What You Get updated; root pre-commit green
- [ ] `plans/README.md` status row updated

## STOP conditions

- `@paginate` + explicit `response={...}` dicts don't compose in
  `django-ninja==1.6.2` and the `openapi_extra` fallback also fails —
  report the ninja behavior; do not drop the pagination or the response
  documentation.
- Schemathesis cannot be satisfied without weakening checks — report
  which check and why rather than configuring exclusions.
- django-extra-checks demands something the spec above doesn't provide
  and the fix isn't obvious from its error message — report.
- The Step 8 diff is non-empty — find the leak (usually Jinja whitespace
  in a gated block) before proceeding; if you cannot, STOP.

## Maintenance notes

- This app is the template's living style guide — future convention
  changes (auth default, pagination, schema naming) must update it.
- The `django_auth` choice means browser-session semantics (CSRF applies
  to real clients; tests bypass via `force_login`). A token/JWT auth
  knob remains deferred direction — if added later, the notes router is
  where it plugs in.
- Reviewer focus: Jinja whitespace in the gated blocks (`api.py`,
  `apps.py`, `factories.py`, `conftest.py`, `versioning_test.py`) in
  BOTH knob states, and the byte-identity check.
