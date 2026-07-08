# Plan 005: Migrate the example notes API to django-ninja-extra class-based controllers

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving to the
> next step. If anything in the "STOP conditions" section occurs, stop and
> report — do not improvise. When done, update the status row for this plan
> in `plans/README.md` — unless a reviewer dispatched you and told you they
> maintain the index.
>
> **Drift check (run first)**:
>
> ```shell
> git diff --stat 4a1fae8..HEAD -- cookiecutter.json "{{cookiecutter.project_slug}}/pyproject.toml" "{{cookiecutter.project_slug}}/src/apps/notes/routes.py" "{{cookiecutter.project_slug}}/src/apps/api/api.py" "{{cookiecutter.project_slug}}/src/apps/api/pagination.py" "{{cookiecutter.project_slug}}/src/config/settings/components/apps.py"
> ```
>
> If any in-scope file changed since this plan was written, compare the
> "Current state" excerpts below against the live code before proceeding; on a
> mismatch, treat it as a STOP condition.

## Status

- **Priority**: P2
- **Effort**: L
- **Risk**: MED
- **Depends on**: none (plan 001 is already merged to `main`; this plan's
  excerpts already reflect its `api_auth` knob)
- **Category**: migration
- **Planned at**: commit `4a1fae8`, 2026-07-08

## Why this matters

The example notes API in `apps/notes/routes.py` is written as a flat set of
`@router`-decorated functions. [django-ninja-extra](https://eadwincode.github.io/django-ninja-extra/)
adds class-based `APIController`s on top of django-ninja: reusable
`permission_classes`, constructor-based dependency injection, and a structure
that scales better once a generated project grows past one example resource.
Because this repo is a cookiecutter template, the example app is also the
reference pattern every generated project copies for its first real endpoint —
landing the class-based style here means new business controllers in
downstream projects have a real, tested example to imitate instead of only the
plain-router style. This plan converts the one existing example resource
(`notes`) end to end and leaves the internal `/api/health` and `/api/ready`
routers untouched, so the blast radius is one resource with full existing test
coverage as a safety net.

## Current state

- `{{cookiecutter.project_slug}}/src/apps/notes/routes.py` (full file today —
  plan 001 already added the `api_auth` session/token switch here):

  ```python
  import uuid

  from django.db.models import QuerySet
  from django.http import HttpRequest
  from django.shortcuts import get_object_or_404
  from ninja import Router, Status
  from ninja.pagination import paginate
  {%- if cookiecutter.api_auth == "session" %}
  from ninja.security import django_auth
  {%- endif %}

  {% if cookiecutter.api_auth == "token" -%}
  from apps.api.auth import bearer_token_auth
  {% endif -%}
  from apps.api.pagination import BoundedLimitOffsetPagination
  from apps.api.schemas import ErrorSchema

  from .models import Note
  from .schemas import NoteInSchema, NoteOutSchema

  {% if cookiecutter.api_auth == "token" -%}
  router = Router(auth=bearer_token_auth, tags=["notes"])
  {% else -%}
  router = Router(auth=django_auth, tags=["notes"])
  {% endif %}

  @router.post("", response={201: NoteOutSchema, 401: ErrorSchema, 403: ErrorSchema})
  def create_note(request: HttpRequest, payload: NoteInSchema) -> Status[Note]:
      note = Note.objects.create(owner=request.user, **payload.dict())
      return Status(201, note)


  @router.delete(
      "/{note_id}",
      response={204: None, 401: ErrorSchema, 403: ErrorSchema, 404: ErrorSchema},
  )
  def delete_note(request: HttpRequest, note_id: uuid.UUID) -> Status[None]:
      note = get_object_or_404(Note, id=note_id, owner=request.user)
      note.delete()
      return Status(204, None)


  @router.get(
      "/{note_id}", response={200: NoteOutSchema, 401: ErrorSchema, 404: ErrorSchema}
  )
  def get_note(request: HttpRequest, note_id: uuid.UUID) -> Note:
      return get_object_or_404(Note, id=note_id, owner=request.user)


  @router.get("", response={200: list[NoteOutSchema], 401: ErrorSchema})
  @paginate(BoundedLimitOffsetPagination)
  def list_notes(request: HttpRequest) -> QuerySet[Note]:
      return Note.objects.filter(owner=request.user)


  @router.put(
      "/{note_id}",
      response={
          200: NoteOutSchema,
          401: ErrorSchema,
          403: ErrorSchema,
          404: ErrorSchema,
      },
  )
  def update_note(
      request: HttpRequest, note_id: uuid.UUID, payload: NoteInSchema
  ) -> Note:
      note = get_object_or_404(Note, id=note_id, owner=request.user)
      note.body = payload.body
      note.title = payload.title
      note.save()
      return note
  ```

- `{{cookiecutter.project_slug}}/src/apps/api/api.py` mounts it today:

  ```python
  from django.conf import settings
  from django.utils.module_loading import import_string
  from ninja import NinjaAPI

  {% if cookiecutter.use_example_api == "yes" -%}
  from apps.notes.routes import router as notes_router
  {% endif -%}
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
  {%- if cookiecutter.use_example_api == "yes" %}
  v1_api.add_router("/notes", notes_router)
  {%- endif %}
  ```

  `internal_api` (health/ready) is out of scope — leave it a plain `NinjaAPI`
  with plain `Router`s.

- `{{cookiecutter.project_slug}}/src/apps/api/pagination.py` (unchanged file,
  quoted so you can see what `BoundedLimitOffsetPagination` extends):

  ```python
  import math

  from ninja import Field
  from ninja.conf import settings
  from ninja.pagination import LimitOffsetPagination

  PAGINATION_MAX_LIMIT = (
      settings.PAGINATION_PER_PAGE
      if math.isinf(settings.PAGINATION_MAX_LIMIT)
      else settings.PAGINATION_MAX_LIMIT
  )


  class BoundedLimitOffsetPagination(LimitOffsetPagination):
      class Input(LimitOffsetPagination.Input):
          limit: int = Field(
              settings.PAGINATION_PER_PAGE,
              ge=1,
              le=PAGINATION_MAX_LIMIT,
          )
          offset: int = Field(0, ge=0, le=settings.PAGINATION_MAX_OFFSET)
  ```

- `{{cookiecutter.project_slug}}/tests/conftest.py` builds test clients around
  the full `NinjaAPI` instance, not per-router:

  ```python
  @pytest.fixture
  def v1_api_client() -> TestClient:
      return TestClient(v1_api)
  ```

  `authenticated_v1_api_client` wraps `v1_api_client` in
  `tests/utils.py:AuthenticatedTestClient`. These fixtures send real HTTP
  requests to `/notes`, `/notes/{id}` and assert on `response.data` — they do
  not import anything from `apps.notes.routes` directly. **This means the
  existing test files should need zero content changes** — only whatever
  import path change is mechanically required if you rename the module (see
  Task 2). If a test's assertions need to change for any reason other than an
  import path, that means behavior changed and you must STOP (see STOP
  conditions).

- `{{cookiecutter.project_slug}}/pyproject.toml` dependency block (relevant
  slice, alphabetically ordered):

  ```toml
      "django-environ==0.13.0",
      "django-extra-checks==0.17.0",
      "django-ninja==1.6.2",
      "django-redis==7.0.0",
  ```

- `{{cookiecutter.project_slug}}/pyproject.toml` ruff config that matters here:

  ```toml
  [tool.ruff.lint.flake8-type-checking]
  runtime-evaluated-decorators = [
      "ninja.NinjaAPI.delete",
      "ninja.NinjaAPI.get",
      "ninja.NinjaAPI.patch",
      "ninja.NinjaAPI.post",
      "ninja.NinjaAPI.put",
      "ninja.Router.delete",
      "ninja.Router.get",
      "ninja.Router.patch",
      "ninja.Router.post",
      "ninja.Router.put",
  ]
  ```

  This list tells ruff which decorated functions have their parameter
  annotations evaluated at runtime (by django-ninja's schema/operation
  building), so ruff must NOT move those annotations into a `TYPE_CHECKING`
  block. Plan 001 hit this directly: `apps/api/auth.py`'s `authenticate`
  method isn't in this list, so ruff's TC002 rule forced `HttpRequest` into
  `TYPE_CHECKING` there. The new `ninja_extra` route decorators are not in
  this list yet — you must add them, or `ruff check` will try to move
  `HttpRequest` out of the controller methods' runtime signature, which would
  break request/response schema resolution rather than just relocate an
  import.

- `{{cookiecutter.project_slug}}/src/config/settings/components/apps.py`
  `INSTALLED_APPS` (relevant slice):

  ```python
      "django_structlog",
      "extra_checks",
      # Project
      "apps.api",
      "apps.core",
  {%- if cookiecutter.use_example_api == "yes" %}
      "apps.notes",
  {%- endif %}
  ]
  ```

- Repo conventions that apply here (from `AGENTS.md`, quoted so you don't have
  to go find them):
  - "Keep Django Ninja routers resource-oriented. Mount resource routers at
    their resource prefix and keep route-local paths relative." — the
    controller's `@api_controller("/notes", ...)` path plus relative
    per-method paths (`""`, `"/{note_id}"`) satisfies this the same way the
    current `Router` does.
  - "Order public classes, public functions, and methods alphabetically
    within their group when dependency order does not matter." — keep the
    five controller methods in the same alphabetical order they're in today:
    `create_note`, `delete_note`, `get_note`, `list_notes`, `update_note`.
  - "Alphabetize parameters in tests, helper functions, and Django Ninja
    endpoints when framework conventions do not require a leading parameter
    such as `self`, `request`, ..." — `self` and `request` stay first, the
    rest keep today's order.
  - "The API has no default auth. Endpoints requiring protection must add
    ninja auth ... never ship a mutating endpoint unauthenticated." — the
    controller must keep the exact same `auth=` behavior as today (session vs
    token, switched on `cookiecutter.api_auth`).

## Commands you will need

| Purpose | Command | Expected on success |
|---|---|---|
| Bake (session mode) | `uvx cookiecutter . -o /tmp/bake-controllers-session --no-input use_example_api=yes` | exit 0 |
| Bake (token mode) | `uvx cookiecutter . -o /tmp/bake-controllers-token --no-input use_example_api=yes api_auth=token` | exit 0 |
| Bake (no example API) | `uvx cookiecutter . -o /tmp/bake-controllers-empty --no-input` | exit 0, no `ninja_extra` dependency, no `apps.notes` |
| Django check | `uv run python manage.py check` (run inside a baked project) | "System check identified no issues" |
| Migration check | `uv run python manage.py makemigrations --check --dry-run` | "No changes detected" |
| Tests | `uv run pytest` (run inside a baked project) | exit 0, 100% coverage |
| Root lint/format/type-check | `pre-commit run --all-files` (run at repo root) | exit 0 |

(`rtk` is a token-optimized proxy wrapper some environments have installed —
if a `rtk <cmd>` alias is available, prefer it; otherwise run the commands
above directly, which is not a deviation worth reporting.)

## Suggested executor toolkit

Read these before starting — they cover the exact API surface this plan uses:

- <https://eadwincode.github.io/django-ninja-extra/> — overview,
  `@api_controller`, `register_controllers`.
- <https://eadwincode.github.io/django-ninja-extra/tutorial/pagination/> —
  `@paginate` and pagination classes.
- <https://eadwincode.github.io/django-ninja-extra/tutorial/authentication/> —
  `auth=` on `@api_controller` and per-route.

Two things the docs state inconsistently (found during planning — verify
yourself rather than trusting either claim blindly):

1. Some doc pages imply `@api_controller`-decorated classes need no base
   class; the project's own test suite
   (`tests/test_permissions.py` in the django-ninja-extra repo) explicitly
   subclasses `ControllerBase` — e.g. `class Some2Controller(ControllerBase):`.
   **Use explicit `ControllerBase` inheritance** for `NotesController`; it is
   the pattern proven in the library's own tests.
2. It's unclear from the docs whether the plain `ninja.pagination.paginate`
   decorator (used today) keeps working unmodified on a bound controller
   method, or whether it must be swapped for `ninja_extra.pagination.paginate`
   with `BoundedLimitOffsetPagination` rebased onto
   `ninja_extra.pagination.LimitOffsetPagination`. Task 4 below has you try
   the low-risk path first (keep everything from plain `ninja`) with a
   concrete fallback if it fails.

## Scope

**In scope**:
- `{{cookiecutter.project_slug}}/pyproject.toml`
- `{{cookiecutter.project_slug}}/src/config/settings/components/apps.py`
- `{{cookiecutter.project_slug}}/src/apps/api/api.py`
- `{{cookiecutter.project_slug}}/src/apps/api/pagination.py` (only if Task 4's
  fallback path is needed)
- `{{cookiecutter.project_slug}}/src/apps/notes/routes.py` (delete/rename to
  `controllers.py`)
- `{{cookiecutter.project_slug}}/src/apps/notes/controllers.py` (create)
- `{{cookiecutter.project_slug}}/AGENTS.md`
- `{{cookiecutter.project_slug}}/README.md`
- `README.md` (root, only if the dependency table needs a line — check first;
  it currently lists cookiecutter variables, not pinned dependencies, so this
  file likely needs no change)

**Out of scope** (do NOT touch, even though they look related):
- `{{cookiecutter.project_slug}}/src/apps/api/routes/health.py` and
  `ready.py`, and `internal_api` in `api.py` — these stay plain
  `Router`/`NinjaAPI`. Converting them is a separate, unrequested change.
- `{{cookiecutter.project_slug}}/tests/notes/integration/notes_test.py` —
  should need zero behavioral changes (see "Current state"). If you find
  yourself editing an assertion, STOP.
- `{{cookiecutter.project_slug}}/tests/conftest.py` and
  `{{cookiecutter.project_slug}}/tests/utils.py` — the full-`NinjaAPI`
  `TestClient` fixtures are framework-agnostic to this change; do not switch
  them to `ninja_extra.testing.TestClient`.
- Plan 003 (`api_throttling`, not yet implemented) — do not add throttling
  here. If plan 003 lands after this one, it will need to target
  `apps/notes/controllers.py` instead of `routes.py`; that's a note for
  whoever executes plan 003, not work for this plan.
- Adding `permission_classes`, DI-based services, or any django-ninja-extra
  feature beyond what's needed to reproduce today's behavior 1:1. This plan is
  a structural conversion, not a feature addition.

## Git workflow

- Commit per task below; message style matches this repo's history, e.g.
  `feat: convert notes API to django-ninja-extra controllers`,
  `test: ...` if a follow-up test-only commit is needed.
- Do NOT push or open a PR unless the operator instructed it.

## Steps

### Task 1: Add the dependency

- [ ] Confirm the current latest stable `django-ninja-extra` release and that
      it declares compatibility with `django-ninja>=0.16.1` (the pin here is
      `django-ninja==1.6.2`) and Django 6 — check
      <https://pypi.org/project/django-ninja-extra/>. At planning time this
      was `0.31.5` (released 2026-06-14, states Django 3.1–6.0 and
      `django-ninja>=0.16.1` support). Use that version unless you find a
      newer stable release; if so, use the newer one and note it in your
      report.
- [ ] In `{{cookiecutter.project_slug}}/pyproject.toml`, add the dependency
      alphabetically between `django-ninja` and `django-redis`, **gated to
      `use_example_api == "yes"`** (mirrors how `apps.notes` itself is
      gated — empty API projects should not gain this dependency):

  ```toml
      "django-ninja==1.6.2",
  {%- if cookiecutter.use_example_api == "yes" %}
      "django-ninja-extra==0.31.5",
  {%- endif %}
      "django-redis==7.0.0",
  ```

- [ ] In `{{cookiecutter.project_slug}}/src/config/settings/components/apps.py`,
      add `"ninja_extra"` to `INSTALLED_APPS`, gated the same way, placed with
      the other third-party apps (before the `# Project` comment):

  ```python
      "django_structlog",
      "extra_checks",
  {%- if cookiecutter.use_example_api == "yes" %}
      "ninja_extra",
  {%- endif %}
      # Project
      "apps.api",
      "apps.core",
  {%- if cookiecutter.use_example_api == "yes" %}
      "apps.notes",
  {%- endif %}
  ]
  ```

- [ ] In `[tool.ruff.lint.flake8-type-checking].runtime-evaluated-decorators`
      in `pyproject.toml`, add the `ninja_extra` route decorators you will use
      in Task 3 (alphabetized with the existing entries):

  ```toml
  runtime-evaluated-decorators = [
      "ninja.NinjaAPI.delete",
      "ninja.NinjaAPI.get",
      "ninja.NinjaAPI.patch",
      "ninja.NinjaAPI.post",
      "ninja.NinjaAPI.put",
      "ninja.Router.delete",
      "ninja.Router.get",
      "ninja.Router.patch",
      "ninja.Router.post",
      "ninja.Router.put",
      "ninja_extra.http_delete",
      "ninja_extra.http_get",
      "ninja_extra.http_post",
      "ninja_extra.http_put",
  ]
  ```

  Do not gate this list itself on `use_example_api` — `pyproject.toml`'s
  `[tool.ruff...]` sections are not Jinja-templated per-variable the way
  `dependencies` is; adding these four entries unconditionally is harmless
  when `apps.notes` isn't rendered (ruff just never sees a matching
  decorator).

- [ ] Verify: bake with `use_example_api=yes api_auth=token`, then inside the
      baked project run `uv sync --locked`. Expected: exit 0, `uv.lock`
      updates to include `django-ninja-extra` and its transitive deps.

### Task 2: Convert `routes.py` to `controllers.py`

- [ ] `git mv` (or create + delete)
      `{{cookiecutter.project_slug}}/src/apps/notes/routes.py` to
      `{{cookiecutter.project_slug}}/src/apps/notes/controllers.py`.
- [ ] Rewrite its contents as a class-based controller. Target shape (adapt
      the `auth=` value exactly as today's Jinja gate does):

  ```python
  import uuid

  from django.db.models import QuerySet
  from django.http import HttpRequest
  from django.shortcuts import get_object_or_404
  from ninja import Status
  from ninja.pagination import paginate
  from ninja_extra import ControllerBase, api_controller, http_delete, http_get, http_post, http_put
  {%- if cookiecutter.api_auth == "session" %}
  from ninja.security import django_auth
  {%- endif %}

  {% if cookiecutter.api_auth == "token" -%}
  from apps.api.auth import bearer_token_auth
  {% endif -%}
  from apps.api.pagination import BoundedLimitOffsetPagination
  from apps.api.schemas import ErrorSchema

  from .models import Note
  from .schemas import NoteInSchema, NoteOutSchema


  @api_controller(
      "/notes",
      auth={% if cookiecutter.api_auth == "token" %}bearer_token_auth{% else %}django_auth{% endif %},
      tags=["notes"],
  )
  class NotesController(ControllerBase):
      @http_post("", response={201: NoteOutSchema, 401: ErrorSchema, 403: ErrorSchema})
      def create_note(self, request: HttpRequest, payload: NoteInSchema) -> Status[Note]:
          note = Note.objects.create(owner=request.user, **payload.dict())
          return Status(201, note)

      @http_delete(
          "/{note_id}",
          response={204: None, 401: ErrorSchema, 403: ErrorSchema, 404: ErrorSchema},
      )
      def delete_note(self, request: HttpRequest, note_id: uuid.UUID) -> Status[None]:
          note = get_object_or_404(Note, id=note_id, owner=request.user)
          note.delete()
          return Status(204, None)

      @http_get(
          "/{note_id}", response={200: NoteOutSchema, 401: ErrorSchema, 404: ErrorSchema}
      )
      def get_note(self, request: HttpRequest, note_id: uuid.UUID) -> Note:
          return get_object_or_404(Note, id=note_id, owner=request.user)

      @http_get("", response={200: list[NoteOutSchema], 401: ErrorSchema})
      @paginate(BoundedLimitOffsetPagination)
      def list_notes(self, request: HttpRequest) -> QuerySet[Note]:
          return Note.objects.filter(owner=request.user)

      @http_put(
          "/{note_id}",
          response={
              200: NoteOutSchema,
              401: ErrorSchema,
              403: ErrorSchema,
              404: ErrorSchema,
          },
      )
      def update_note(
          self, request: HttpRequest, note_id: uuid.UUID, payload: NoteInSchema
      ) -> Note:
          note = get_object_or_404(Note, id=note_id, owner=request.user)
          note.body = payload.body
          note.title = payload.title
          note.save()
          return note
  ```

  Import ordering, line wrapping, and the exact Jinja whitespace-control
  markers (`{%-`, `-%}`) must satisfy `ruff format` and this repo's Jinja
  linting — run the verify command below and let the formatters fix
  whitespace rather than hand-tuning it.

- [ ] Verify: bake `use_example_api=yes` (session) and
      `use_example_api=yes api_auth=token`, then inside each run
      `uv run python manage.py check`. Expected: "System check identified no
      issues (0 silenced)" for both.

### Task 3: Wire the controller into `api.py`

- [ ] Update `{{cookiecutter.project_slug}}/src/apps/api/api.py` so `v1_api`
      is a `NinjaExtraAPI` only when `use_example_api == "yes"` (empty API
      projects keep the plain `NinjaAPI`, matching the dependency gate in
      Task 1), and register the controller instead of `add_router`:

  ```python
  from django.conf import settings
  from django.utils.module_loading import import_string
  from ninja import NinjaAPI
  {%- if cookiecutter.use_example_api == "yes" %}
  from ninja_extra import NinjaExtraAPI
  {%- endif %}

  {% if cookiecutter.use_example_api == "yes" -%}
  from apps.notes.controllers import NotesController
  {% endif -%}
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

  v1_api = {% if cookiecutter.use_example_api == "yes" %}NinjaExtraAPI{% else %}NinjaAPI{% endif %}(
      title=project_name,
      version="1.0.0",
      docs_decorator=docs_decorator,
      urls_namespace="v1",
  )
  {%- if cookiecutter.use_example_api == "yes" %}
  v1_api.register_controllers(NotesController)
  {%- endif %}
  ```

  `internal_api` must stay exactly as it is today — a plain `NinjaAPI` with
  `add_router`.

- [ ] Verify: bake `use_example_api=no`. Expected: `apps/api/api.py` renders
      with no `ninja_extra` import and `v1_api = NinjaAPI(...)`; run
      `uv run python manage.py check` inside it → no issues.

### Task 4: Confirm pagination still works

- [ ] Bake `use_example_api=yes` and run
      `uv run pytest --no-cov tests/notes/integration/notes_test.py -k pagina` (or
      the two pagination-specific tests:
      `test_list_notes_returns_second_page_when_offset_given` and
      `test_list_notes_caps_items_when_limit_below_total`, plus
      `test_list_notes_returns_422_when_limit_exceeds_maximum` and
      `test_list_notes_returns_422_when_offset_exceeds_maximum`).
- [ ] **If all four pass** with `BoundedLimitOffsetPagination` and
      `ninja.pagination.paginate` unchanged (i.e. you did not need to touch
      `apps/api/pagination.py`): you're done with this task, move on.
- [ ] **If any fail or error** in a way that traces to the pagination
      decorator/class rather than a genuine regression you introduced
      elsewhere: switch `list_notes` to
      `from ninja_extra.pagination import paginate` and rebase
      `BoundedLimitOffsetPagination` in
      `{{cookiecutter.project_slug}}/src/apps/api/pagination.py` onto
      `ninja_extra.pagination.LimitOffsetPagination` instead of
      `ninja.pagination.LimitOffsetPagination`. Re-run the same four tests and
      confirm they pass. Note this deviation explicitly in your report — it
      means `apps/api/pagination.py` is now in scope even though the primary
      path above expected it not to be.
- [ ] Verify: the four pagination tests above pass either way.

### Task 5: Update docs

- [ ] `{{cookiecutter.project_slug}}/AGENTS.md`: near the existing line "Keep
      Django Ninja routers resource-oriented..." (around line 132), add a
      sentence noting the example notes resource specifically uses a
      django-ninja-extra class-based controller
      (`apps.notes.controllers.NotesController`) while `/api/health` and
      `/api/ready` remain plain function-based routers — so a future agent
      doesn't assume the whole API must be one style or the other.
- [ ] `{{cookiecutter.project_slug}}/README.md`: if it documents the notes
      example's implementation style anywhere (check for mentions of
      "router" near the notes/API section), update the wording to say
      "class-based controller". If it only documents cookiecutter variables
      and doesn't describe implementation style, no change is needed here —
      say so in your report rather than inventing a section.
- [ ] Verify: `grep -rn "notes_router\|apps.notes.routes" "{{cookiecutter.project_slug}}"`
      returns no matches (confirms no stale references survive the rename).

### Task 6: Full verification sweep

- [ ] Bake all three variants and run the full suite in each:
  - `use_example_api=no` → `uv sync --locked`, `pytest`, `pre-commit run --all-files`
  - `use_example_api=yes` (session) → same three commands
  - `use_example_api=yes api_auth=token` → same three commands
  - Expected each time: pytest exits 0 at 100% coverage;
    `pre-commit run --all-files` exits 0.
- [ ] At the repo root (not inside a bake): `pre-commit run --all-files`.
      Expected: exit 0.

## Test plan

- No new test files are expected. The existing
  `tests/notes/integration/notes_test.py` suite (14 tests covering create,
  get, list + pagination + limits, update, delete, ownership checks,
  anonymous 401s) is the regression harness — it asserts on HTTP
  status/response bodies through the full `v1_api` `TestClient`, which is
  implementation-agnostic to router-vs-controller.
- `tests/api/integration/schema_test.py` (OpenAPI schema conformance) and
  `tests/api/integration/docs_gating_test.py` must also keep passing
  unchanged — they prove the generated OpenAPI schema and docs gating didn't
  shift.
- Verification: `pytest` inside each of the three bakes in Task 6 → all pass,
  100% coverage, no new or modified assertions in `notes_test.py`
  (`git diff --stat` should show `0` changes to that file unless Task 4's
  fallback path required something you must justify in your report).

## Done criteria

- [ ] `apps/notes/routes.py` no longer exists; `apps/notes/controllers.py`
      exists and defines `NotesController(ControllerBase)` with the same five
      operations, same paths, same response schemas as before.
- [ ] `v1_api` is a `NinjaExtraAPI` when `use_example_api=yes`, a plain
      `NinjaAPI` when `use_example_api=no`. `internal_api` is unchanged.
- [ ] `django-ninja-extra` and `"ninja_extra"` (INSTALLED_APPS) render only
      when `use_example_api=yes`.
- [ ] `tests/notes/integration/notes_test.py` is unmodified (or any
      modification is explicitly justified in the executor's report).
- [ ] All three bake variants (`no`, `yes`+session, `yes`+token) pass
      `pytest` at 100% coverage and `pre-commit run --all-files` inside the
      bake.
- [ ] Root `pre-commit run --all-files` passes.
- [ ] `plans/README.md` status row for plan 005 updated.

## STOP conditions

- The code at the locations in "Current state" doesn't match (the codebase
  drifted since this plan was written — re-run the drift check command).
- `ControllerBase` inheritance, or any of `http_get`/`http_post`/`http_put`/
  `http_delete`, doesn't exist at the import paths given here in the pinned
  `django-ninja-extra` version — the library's public API changed since this
  plan was researched. Stop and report the actual API surface you found.
- Making `tests/notes/integration/notes_test.py` pass requires changing an
  assertion (not just an import), or requires touching
  `tests/conftest.py`/`tests/utils.py` beyond what Task 2's rename mechanically
  requires.
- `manage.py check` or `pre-commit` demands additional Django settings
  (cache backends, throttle rates, etc.) purely to install `ninja_extra` —
  do not add speculative settings; report what's being asked for instead.
- Task 4's fallback path also fails to make the pagination tests pass — that
  means the incompatibility is deeper than a class swap; stop and report the
  actual error.
- The conversion cannot preserve the exact `auth=` behavior (session vs
  token) that plan 001 established.

## Maintenance notes

- Plan 003 (`api_throttling=basic`, not yet implemented) will need to target
  `apps/notes/controllers.py` instead of `routes.py` once it's written or
  refreshed — flag this to whoever picks up plan 003 next.
- If a future plan adds a second example resource, model it on
  `NotesController` (class-based, `ControllerBase`, `api_controller`) rather
  than reintroducing the plain-`Router` style, to keep the example API
  internally consistent.
- `django-ninja-extra` releases fairly often; when dependency updates touch
  it, re-run the full bake matrix in Task 6, since its `@api_controller`/
  `@paginate` behavior is the part of this stack with the least test coverage
  from the upstream project itself relative to plain django-ninja.
