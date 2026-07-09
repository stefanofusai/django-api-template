# Plan 006: Build token lifecycle endpoints (create / list / revoke) for `api_auth=token`

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving to the
> next step. If anything in the "STOP conditions" section occurs, stop and
> report — do not improvise. This plan modifies the GENERATED project, so all
> real verification happens inside a bake; never edit a baked tree and call it
> done — edits go to the template under `{{cookiecutter.project_slug}}/` (Jinja)
> or `hooks/` (plain Python). When done, update the status row for this plan in
> `plans/README.md` — unless a reviewer dispatched you and told you they
> maintain the index.
>
> **Drift check (run first)**:
> `git diff --stat 16a12b3..HEAD -- '{{cookiecutter.project_slug}}/src/apps/core/models.py' '{{cookiecutter.project_slug}}/src/apps/api/auth.py' '{{cookiecutter.project_slug}}/src/apps/api/api.py' '{{cookiecutter.project_slug}}/src/apps/core/admin.py' '{{cookiecutter.project_slug}}/tests/factories.py' '{{cookiecutter.project_slug}}/tests/api/unit/auth_test.py' '{{cookiecutter.project_slug}}/tests/core/unit/models_test.py' '{{cookiecutter.project_slug}}/tests/core/integration/admin_test.py' hooks/post_gen_project.py`
> If any in-scope file changed since this plan was written, compare the
> "Current state" excerpts against the live code before proceeding; on a
> mismatch, treat it as a STOP condition.

## Status

- **Priority**: P3
- **Effort**: M
- **Risk**: LOW-MED
- **Depends on**: plans/002-token-auth-inactive-users.md (DONE — its
  `is_active` reject semantics are assumed by the auth change here). Coordinate
  with plan 020 (UUID pk squash): this plan adds a new `core` migration
  (`0003_token_revoked_at`) on top of `0002_token`; if 020 lands **after** this
  plan it must absorb `0003` into its fresh initial, and if 020 lands **first**
  the migration here must be regenerated against 020's squashed initial and the
  schema `id` fields must become `uuid.UUID` — see Maintenance notes.
- **Category**: feature
- **Planned at**: commit `16a12b3`, 2026-07-09

## Why this matters

When the template is baked with `use_example_api=yes api_auth=token`, there is
**no supported way to mint a usable token except `Token.issue()` in a Django
shell**: the notes controller only consumes tokens, and `TokenAdmin`
(`src/apps/core/admin.py`) is a plain `ModelAdmin` — creating a row through it
stores whatever `digest` the operator types, which authenticates nothing (real
digests are SHA-256 of a `pat_<prefix>_<secret>` string that only
`Token.issue()` can produce, and the raw token must be shown exactly once).
Every project baked from this template currently has to hand-roll token
management. This plan ships first-class lifecycle endpoints (`create`, `list`,
`revoke`) plus a bootstrap-capable admin.

**Why not django-allauth headless** (settled during planning, recorded so
nobody re-opens it): allauth headless provides login/signup/2FA session and access
tokens for SPA flows via an app-client model — *authentication-session*
artifacts tied to login, not the user-managed, named, long-lived PAT-style
tokens this template already models with `Token` + `BearerTokenAuth`. Adopting
it would add a large dependency and middleware surface and displace the
existing `Token` model and auth for no fit. We build a bespoke ninja-extra
`TokensController` instead, following the conventions of
`src/apps/notes/controllers.py`.

**Placement**: the controller and its schemas live in the `core` app
(`src/apps/core/controllers.py`, `src/apps/core/schemas.py`), colocated with
the `Token` model exactly as `NotesController` lives with `Note` in the `notes`
app. `src/apps/api/` holds only cross-cutting infrastructure (auth, pagination,
throttling, error schemas), so a token controller does not belong there.

## Current state

This repo is a **cookiecutter template**; nothing under
`{{cookiecutter.project_slug}}/` runs directly. Verification means baking a
project and running its suite. All token machinery renders **only** when
`use_example_api=yes AND api_auth=token`; `hooks/post_gen_project.py` deletes or
Jinja-guards it away otherwise. This plan keeps that knob placement unchanged —
no knob redesign.

Verified against a fresh bake
(`uvx cookiecutter . -o /tmp/verify-006 --no-input use_example_api=yes api_auth=token`):

- **`Token` model** (`src/apps/core/models.py`) — `Token(CreatedAtModel)` with
  `expires_at` (nullable), `last_used_at` (nullable, minute-granular via
  `mark_used()`), `user` (FK CASCADE, `related_name="tokens"`), `digest`
  (unique SHA-256 hex), `name` (100 chars), `prefix` (indexed, 12 chars).
  Classmethod `Token.issue(*, expires_at=None, name, user) -> tuple[str, Token]`
  is the ONLY producer of valid tokens; `is_expired()` mirrors the shape the new
  `is_revoked()` will follow. **The pk is `BigAutoField`** (int) — confirmed in
  `core/migrations/0002_token.py` — so schema `id`/`token_id` fields are typed
  `int` for now (plan 020 flips them to `uuid.UUID`). The whole `Token` block is
  Jinja-guarded by `{% raw %}{% if cookiecutter.use_example_api == "yes" and cookiecutter.api_auth == "token" %}{% endraw %}`.

- **Auth** (`src/apps/api/auth.py`, a token-only file removed by post-gen
  otherwise) — `BearerTokenAuth(HttpBearer)` rejects when
  `stored_token is None or stored_token.is_expired() or not stored_token.user.is_active`
  (the `is_active` clause is plan 002's, DONE). `mark_used()` then sets
  `request.user`.

- **API composition** (`src/apps/api/api.py`) — `v1_api` is a `NinjaExtraAPI`
  when `use_example_api=yes`; today it runs only
  `v1_api.register_controllers(NotesController)` under a
  `{% raw %}{%- if cookiecutter.use_example_api == "yes" %}{% endraw %}` guard.

- **Controller conventions** (`src/apps/notes/controllers.py`) —
  `@api_controller("/notes", auth=bearer_token_auth, tags=[...])` on a
  `ControllerBase`; each route has an explicit response map including
  `401: ErrorSchema` and `422: ValidationErrorSchema`; write routes return
  `Status[Model]` (e.g. `return Status(201, note)`); list uses
  `@paginate(BoundedLimitOffsetPagination)` returning
  `NinjaPaginationResponseSchema[...]`; per-owner scoping via
  `get_object_or_404(Model, id=..., owner=request.user)`. Schemas
  (`src/apps/notes/schemas.py`) are plain `ninja.Schema` with
  `Field(max_length=..., min_length=..., pattern=NO_NUL_PATTERN)`.

- **Admin gap** (`src/apps/core/admin.py`) — `TokenAdmin(ModelAdmin)` is
  list-only config; its default add form exposes `digest` for hand-entry, which
  authenticates nothing. Guarded by the same token `{% raw %}{% if %}{% endraw %}` block.

- **Throttling** (`src/apps/api/throttling.py`, present only when
  `api_throttling=basic`) — `_should_throttle_public_api_anonymous_request`
  gates on `not request.user.is_authenticated`, `method != "OPTIONS"`, and
  `path_info.startswith("/api/v1/")`. The anon IP budget applies **only** to
  header-less anonymous requests and to requests that end in `401`; a request
  bearing a valid token resolves to an authenticated user and is charged to the
  `UserRateThrottle` budget (or none) instead. **Consequence for this plan**:
  the three new endpoints are `BearerTokenAuth`-guarded, so a successful call
  is never debited from the anon budget; only failed-auth attempts are — which
  is the correct brute-force control. `create` is **not** an anonymous login
  surface (it requires an existing token), so no special throttle handling is
  needed. No change to `throttling.py`.

- **Test layout** — `tests/<app>/{integration,unit}/`; global factories in
  `tests/factories.py` (`TokenFactory` already exists, token-guarded);
  `tests/conftest.py` registers them and exposes `v1_api_client` (anonymous
  `TestClient(v1_api)`) and `authenticated_v1_api_client` (an
  `AuthenticatedTestClient` from `tests/utils.py` that mints a real token via
  `Token.issue`). The suite enforces **100% coverage**
  (`--cov-fail-under=100` in `pyproject.toml`), so every new line must be
  exercised. `.github/scripts/migrations-check.sh` runs
  `makemigrations --check --dry-run`, so the new migration must match Django's
  own output exactly.

- **New migration number**: the next `core` migration is
  `0003_token_revoked_at.py` (current head is `0002_token.py`).

## Commands you will need

| Purpose | Command | Expected on success |
|---------|---------|---------------------|
| Bake reference | `uvx cookiecutter . -o /tmp/verify-006 --no-input use_example_api=yes api_auth=token` | project generated |
| Regenerate the migration (in bake) | `uv run python src/manage.py makemigrations core` | writes `0003_token_revoked_at.py` |
| Migration completeness (in bake) | `uv run python src/manage.py makemigrations --check --dry-run` | "No changes detected", exit 0 |
| Start Postgres (in bake) | `cp .env.example .env && docker compose -f .docker/compose/dev.yaml --env-file=.env up -d --wait postgres` | postgres healthy |
| Full suite (in bake, needs Postgres) | `uv sync --locked && uv run pytest` | all pass, coverage 100% |
| Targeted (in bake) | `uv run pytest tests/core/integration/tokens_test.py tests/core/integration/admin_test.py tests/api/unit/auth_test.py tests/core/unit/models_test.py --no-cov` | all pass |
| Lint (in bake) | `uv run ruff check . && uv run ruff format --check .` | exit 0 |
| Teardown (in bake) | `docker compose -f .docker/compose/dev.yaml --env-file=.env down -v` | exit 0 |
| Off-config bake (negative) | `uvx cookiecutter . -o /tmp/verify-006-session --no-input use_example_api=yes api_auth=session` | no token files present |

## Scope

**In scope** (template paths):

Create:
- `{{cookiecutter.project_slug}}/src/apps/core/controllers.py` — `TokensController`
- `{{cookiecutter.project_slug}}/src/apps/core/schemas.py` — token schemas
- `{{cookiecutter.project_slug}}/src/apps/core/migrations/0003_token_revoked_at.py`
- `{{cookiecutter.project_slug}}/tests/core/integration/tokens_test.py`

Modify:
- `{{cookiecutter.project_slug}}/src/apps/core/models.py` — `revoked_at` field + `is_revoked()`
- `{{cookiecutter.project_slug}}/src/apps/api/auth.py` — reject revoked tokens
- `{{cookiecutter.project_slug}}/src/apps/api/api.py` — register `TokensController`
- `{{cookiecutter.project_slug}}/src/apps/core/admin.py` — mint-through-`issue` add flow, show-once, no digest editing
- `{{cookiecutter.project_slug}}/tests/factories.py` — `TokenFactory.revoked_at = None`
- `{{cookiecutter.project_slug}}/tests/api/unit/auth_test.py` — revoked-token reject test
- `{{cookiecutter.project_slug}}/tests/core/unit/models_test.py` — `is_revoked()` tests
- `{{cookiecutter.project_slug}}/tests/core/integration/admin_test.py` — admin mint test
- `hooks/post_gen_project.py` — add the two new `core` modules, the new migration, and the new integration test to the token removal block

**Out of scope** (do NOT touch):

- The knob set / prompts / `cookiecutter.json` — placement stays under
  `use_example_api=yes AND api_auth=token`.
- `src/apps/api/throttling.py` — analysis above shows no change is needed.
- `src/apps/notes/` — unrelated app.
- `plans/README.md` numbering — leave as-is (only your own status row).
- Plan 020's migration squash — coordinate per Maintenance notes, do not
  perform it here.

## Git workflow

- Conventional commits, e.g. `feat: add token lifecycle endpoints for api_auth=token`.
  A reasonable split: one `feat:` for model/auth/admin/api/controller/schemas +
  migration, one `test:` for the suite additions. The `hooks/` change belongs
  with the `feat:` commit (it is part of the feature's render logic).
- Do NOT push unless instructed.

## Steps

All template excerpts below show the Jinja **as it must appear in the template
source**. When a snippet belongs inside an existing
`{% raw %}{% if cookiecutter.use_example_api == "yes" and cookiecutter.api_auth == "token" %}{% endraw %}`
block, add it inside that block — do not open a new one unless told.

### Step 1: Add `revoked_at` and `is_revoked()` to the `Token` model

In `{{cookiecutter.project_slug}}/src/apps/core/models.py`, inside the existing
`Token` block, add the field after `last_used_at`:

```python
    last_used_at = models.DateTimeField(_("last used at"), blank=True, null=True)
    revoked_at = models.DateTimeField(_("revoked at"), blank=True, null=True)
```

and add the method next to `is_expired()`:

```python
    def is_revoked(self) -> bool:
        return self.revoked_at is not None
```

**Verify** (after Step 3's bake exists, or bake now): the rendered
`core/models.py` in the token bake shows both additions and
`uv run ruff check src/apps/core/models.py` passes.

### Step 2: Reject revoked tokens in `BearerTokenAuth`

In `{{cookiecutter.project_slug}}/src/apps/api/auth.py` (a token-only file — no
new Jinja needed), OR `is_revoked()` into the reject condition, keeping plan
002's `is_active` clause:

```python
        if (
            stored_token is None
            or stored_token.is_expired()
            or stored_token.is_revoked()
            or not stored_token.user.is_active
        ):
            raise InvalidTokenError
```

**Verify**: covered by the new `auth_test.py` case in Step 8.

### Step 3: Generate the `revoked_at` migration (do not hand-author it)

Bake the reference project, then let Django write the migration so it matches
`makemigrations --check`:

```bash
uvx cookiecutter . -o /tmp/verify-006 --no-input use_example_api=yes api_auth=token
cd /tmp/verify-006/my-project
uv sync --locked
uv run python src/manage.py makemigrations core
```

Copy the generated `core/migrations/0003_token_revoked_at.py` back to
`{{cookiecutter.project_slug}}/src/apps/core/migrations/0003_token_revoked_at.py`
**verbatim** (it needs no Jinja — post-gen removes it for non-token configs).
It should match this shape (reference only — trust the generated file, and keep
the repo's `ClassVar` typing style seen in `0002_token.py`):

```python
from typing import ClassVar

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies: ClassVar[list[tuple[str, str]]] = [
        ("core", "0002_token"),
    ]

    operations: ClassVar[list[object]] = [
        migrations.AddField(
            model_name="token",
            name="revoked_at",
            field=models.DateTimeField(
                blank=True, null=True, verbose_name="revoked at"
            ),
        ),
    ]
```

**Verify** (in the bake, after copying edits back and re-baking):
`uv run python src/manage.py makemigrations --check --dry-run` → "No changes
detected", exit 0.

### Step 4: Add the token schemas

Create `{{cookiecutter.project_slug}}/src/apps/core/schemas.py` (token-only —
added to the post-gen removal list in Step 9, so no Jinja needed):

```python
from datetime import datetime

from ninja import Field, Schema

NO_NUL_PATTERN = r"^[^\x00]*$"


class TokenCreateSchema(Schema):
    name: str = Field(max_length=100, min_length=1, pattern=NO_NUL_PATTERN)
    expires_at: datetime | None = None


class TokenOutSchema(Schema):
    id: int
    name: str
    prefix: str
    created_at: datetime
    expires_at: datetime | None
    last_used_at: datetime | None
    revoked_at: datetime | None


class TokenCreatedSchema(TokenOutSchema):
    token: str
```

`TokenOutSchema` is the list/read shape — the seven fields the spike specified
and **never `digest`**. `TokenCreatedSchema` extends it with the raw `token`,
returned by `create` **exactly once**.

**Verify**: covered by Step 7's integration tests (fields serialize; digest
absent).

### Step 5: Add the `TokensController`

Create `{{cookiecutter.project_slug}}/src/apps/core/controllers.py` (token-only,
removal-listed in Step 9):

```python
from django.db.models import QuerySet
from django.http import HttpRequest
from django.shortcuts import get_object_or_404
from django.utils import timezone
from ninja import Status
from ninja_extra import (
    ControllerBase,
    api_controller,
    http_delete,
    http_get,
    http_post,
)
from ninja_extra.pagination import paginate
from ninja_extra.schemas import NinjaPaginationResponseSchema

from apps.api.auth import bearer_token_auth
from apps.api.pagination import BoundedLimitOffsetPagination
from apps.api.schemas import ErrorSchema, ValidationErrorSchema

from .models import Token
from .schemas import TokenCreatedSchema, TokenCreateSchema, TokenOutSchema


@api_controller(
    "/tokens",
    auth=bearer_token_auth,
    tags=["tokens"],
    use_unique_op_id=False,
)
class TokensController(ControllerBase):
    @http_post(
        "",
        response={
            201: TokenCreatedSchema,
            401: ErrorSchema,
            422: ValidationErrorSchema,
        },
    )
    def create_token(
        self, request: HttpRequest, payload: TokenCreateSchema
    ) -> Status[Token]:
        raw_token, token = Token.issue(
            expires_at=payload.expires_at,
            name=payload.name,
            user=request.user,
        )
        # Attach the raw token so TokenCreatedSchema surfaces it once; it is
        # derived from the digest and never stored or retrievable again.
        token.token = raw_token
        return Status(201, token)

    @http_delete(
        "/{token_id}",
        response={
            204: None,
            401: ErrorSchema,
            404: ErrorSchema,
            422: ValidationErrorSchema,
        },
    )
    def revoke_token(self, request: HttpRequest, token_id: int) -> Status[None]:
        token = get_object_or_404(
            Token, id=token_id, user=request.user, revoked_at__isnull=True
        )
        token.revoked_at = timezone.now()
        token.save(update_fields=("revoked_at",))
        return Status(204, None)

    @http_get(
        "",
        response={
            200: NinjaPaginationResponseSchema[TokenOutSchema],
            401: ErrorSchema,
            422: ValidationErrorSchema,
        },
    )
    @paginate(BoundedLimitOffsetPagination)
    def list_tokens(self, request: HttpRequest) -> QuerySet[Token]:
        return Token.objects.filter(user=request.user)
```

`use_unique_op_id=False` is required by plan 017 (the OpenAPI drift gate):
ninja-extra's default appends a random `uuid4` suffix to every operation id,
which makes the exported schema non-deterministic and would flap 017's
committed-schema check. If 017 has landed first, also extend its
operation-id regression test
(`tests/api/unit/export_openapi_schema_test.py`) with the five `tokens_*`
ids under a `{% raw %}{% if cookiecutter.api_auth == "token" %}{% endraw %}`
guard — see that plan's Maintenance notes.

Semantics (locked): `list` and `revoke` are scoped to `user=request.user` (a
caller never sees or revokes another user's tokens). `revoke` is a **soft
delete** — it sets `revoked_at` (audit trail preserved, mirroring plan 002's
`is_active` precedent) and `BearerTokenAuth` (Step 2) then refuses the token.
Revoking an **already-revoked** token returns **404** (the
`revoked_at__isnull=True` filter excludes it) — chosen over a silent 204 so the
caller learns the token was already dead; `list` still shows revoked tokens
(with `revoked_at` populated) for the audit view.

**Verify**: Step 7 integration tests.

### Step 6: Register the controller on `v1_api`

In `{{cookiecutter.project_slug}}/src/apps/api/api.py`, add the import and
registration under a **nested** token guard inside the existing
`use_example_api` blocks. The import block becomes:

```jinja
{% raw %}{% if cookiecutter.use_example_api == "yes" -%}
from apps.notes.controllers import NotesController
{% if cookiecutter.api_auth == "token" -%}
from apps.core.controllers import TokensController
{% endif -%}
{% endif -%}{% endraw %}
```

and the registration block becomes:

```jinja
{% raw %}{%- if cookiecutter.use_example_api == "yes" %}
v1_api.register_controllers(NotesController)
{%- if cookiecutter.api_auth == "token" %}
v1_api.register_controllers(TokensController)
{%- endif %}
{%- endif %}{% endraw %}
```

**Verify** (in the token bake): rendered `api.py` imports and registers both
controllers; in the `api_auth=session` bake it imports/registers only
`NotesController` and does not reference `TokensController`.

### Step 7: Integration tests for the endpoints

Create `{{cookiecutter.project_slug}}/tests/core/integration/tokens_test.py`
(token-only, removal-listed in Step 9). Use the existing fixtures — `user`,
`token` (from `TokenFactory`), `v1_api_client` (anonymous), and
`authenticated_v1_api_client`. Cover, at minimum, every branch:

- `create` 201: returns a `token` string starting `pat_`, that string
  authenticates (issue a follow-up request with it), response has no `digest`
  key, and a row exists for `request.user`.
- `create` 422: `name=""` (min_length) and `name` of 101 chars (max_length) →
  422, no row created.
- `create` 401: anonymous `v1_api_client.post("/tokens", ...)`.
- `list` 200: returns only the caller's tokens (create one for `user`, one for
  another user via `TokenFactory`), items carry the seven `TokenOutSchema`
  fields and no `digest`; a revoked token still appears with `revoked_at` set.
- `list` 401: anonymous.
- `revoke` 204: caller's own live token → 204, row's `revoked_at` is set, and
  the raw token no longer authenticates (401 on a subsequent call).
- `revoke` 404: another user's token, a non-existent id, and an
  already-revoked token.
- `revoke` 401: anonymous.

Model each test on `tests/notes/integration/notes_test.py`
(`pytestmark = pytest.mark.django_db`, `HTTPStatus`, `response.data`). To mint a
usable raw token for the caller in a test, use the same pattern as
`tests/utils.py` / `tests/notes/unit/controllers_test.py`:
`raw_token, _ = Token.issue(name="…", user=user)`.

**Verify** (in bake, Postgres up):
`uv run pytest tests/core/integration/tokens_test.py --no-cov` → all pass.

### Step 8: Unit tests for model + auth

- `{{cookiecutter.project_slug}}/tests/core/unit/models_test.py` (inside the
  existing token Jinja block): add `test_is_revoked_returns_false_when_not_revoked`
  and `test_is_revoked_returns_true_when_revoked` (set `revoked_at`).
- `{{cookiecutter.project_slug}}/tests/api/unit/auth_test.py` (token-only file):
  add `test_authenticate_raises_401_when_token_is_revoked`, mirroring the
  existing expired/inactive cases — issue a token, set `revoked_at`, assert
  `BearerTokenAuth().authenticate(...)` raises `InvalidTokenError` with status
  401.

**Verify** (in bake):
`uv run pytest tests/core/unit/models_test.py tests/api/unit/auth_test.py --no-cov`
→ all pass.

### Step 9: Fix `TokenAdmin` to bootstrap the first token safely

The FIRST token must be mintable without an existing token — through Django
admin. Rewrite the `TokenAdmin` block in
`{{cookiecutter.project_slug}}/src/apps/core/admin.py` (inside the existing
token `{% raw %}{% if %}{% endraw %}` guard) so add routes through
`Token.issue()`, the raw token is shown exactly once, and `digest` is never
editable. Add the imports (`messages`, `HttpRequest`, form/model types) that the
new code needs:

```python
@admin.register(Token)
class TokenAdmin(ModelAdmin):
    list_display = (
        "created_at",
        "expires_at",
        "last_used_at",
        "name",
        "prefix",
        "revoked_at",
        "user",
    )
    list_select_related = ("user",)
    readonly_fields = ("created_at", "last_used_at", "prefix", "revoked_at")

    def get_fields(
        self, request: HttpRequest, obj: Token | None = None
    ) -> tuple[str, ...]:
        if obj is None:
            # Add form: never expose digest; issue() derives it.
            return ("name", "user", "expires_at")
        return (
            "name",
            "user",
            "expires_at",
            "prefix",
            "created_at",
            "last_used_at",
            "revoked_at",
        )

    def save_model(
        self, request: HttpRequest, obj: Token, form: ModelForm, change: bool
    ) -> None:
        if change:
            super().save_model(request, obj, form, change)
            return

        raw_token, issued = Token.issue(
            expires_at=form.cleaned_data.get("expires_at"),
            name=form.cleaned_data["name"],
            user=form.cleaned_data["user"],
        )
        obj.pk = issued.pk
        messages.warning(
            request,
            f"Copy this token now — it will not be shown again: {raw_token}",
        )
```

Because `digest` is never in `get_fields`, the add form cannot set it; the
`save_model` add branch mints via `issue()` and surfaces the raw token once via
a `messages.warning`. The change branch keeps `name`/`expires_at` edits harmless
(`digest`/`prefix` stay read-only or absent). Confirm the exact `ModelForm`
import path (`django.forms.ModelForm`) renders cleanly under ruff.

Then extend
`{{cookiecutter.project_slug}}/tests/core/integration/admin_test.py` (inside its
token Jinja block) with:

- `test_token_add_mints_token_and_shows_it_once`: as a logged-in superuser, GET
  `reverse("admin:core_token_add")` → 200 (covers the `obj is None` branch of
  `get_fields`), then POST `name`/`user`/`expires_at` with `follow=True` →
  a `Token` row exists and the response content contains
  `"it will not be shown again"` (covers the `save_model` add branch).
- `test_token_change_updates_name`: POST the change form for an existing
  `token` with a new `name` → row's `name` updated (covers the change branch of
  both `get_fields` and `save_model`).

(The existing `test_token_changelist_returns_200_when_staff` stays.)

**Verify** (in bake, Postgres up):
`uv run pytest tests/core/integration/admin_test.py --no-cov` → all pass.

### Step 10: Wire the new token-only files into post-gen removal + factory field

In `hooks/post_gen_project.py`, extend the token removal block (currently
`src/apps/api/auth.py`, `src/apps/api/exceptions.py`,
`src/apps/core/migrations/0002_token.py`, `tests/api/unit/auth_test.py`) so the
new token-only files are deleted for non-token configs — keep the list sorted:

```python
    *(
        [
            "src/apps/api/auth.py",
            "src/apps/api/exceptions.py",
            "src/apps/core/controllers.py",
            "src/apps/core/migrations/0002_token.py",
            "src/apps/core/migrations/0003_token_revoked_at.py",
            "src/apps/core/schemas.py",
            "tests/api/unit/auth_test.py",
            "tests/core/integration/tokens_test.py",
        ]
        if not (USE_EXAMPLE_API == "yes" and API_AUTH == "token")
        else []
    ),
```

In `{{cookiecutter.project_slug}}/tests/factories.py`, add `revoked_at = None`
to `TokenFactory` (inside its existing token block), after `last_used_at = None`,
so factory-built tokens are un-revoked by default and tests can pass
`revoked_at=<dt>` to build a revoked one.

**Verify**: the negative bake
(`uvx cookiecutter . -o /tmp/verify-006-session --no-input use_example_api=yes api_auth=session`)
produces no `src/apps/core/controllers.py`, no `src/apps/core/schemas.py`, no
`0003_token_revoked_at.py`, and no `tests/core/integration/tokens_test.py`;
`api.py` there does not mention `TokensController`.

### Step 11: Full verification in both configs

Token bake (the feature config):

```bash
uvx cookiecutter . -o /tmp/verify-006 --no-input use_example_api=yes api_auth=token
cd /tmp/verify-006/my-project
uv sync --locked
uv run python src/manage.py makemigrations --check --dry-run   # No changes detected
cp .env.example .env
docker compose -f .docker/compose/dev.yaml --env-file=.env up -d --wait postgres
uv run pytest                                                  # all pass, coverage 100%
uv run ruff check . && uv run ruff format --check .            # exit 0
docker compose -f .docker/compose/dev.yaml --env-file=.env down -v
```

Session bake (regression — nothing token leaks in):

```bash
uvx cookiecutter . -o /tmp/verify-006-session --no-input use_example_api=yes api_auth=session
cd /tmp/verify-006-session/my-project
uv sync --locked
cp .env.example .env
docker compose -f .docker/compose/dev.yaml --env-file=.env up -d --wait postgres
uv run pytest                                                  # all pass, coverage 100%
docker compose -f .docker/compose/dev.yaml --env-file=.env down -v
```

Also run root pre-commit if you touched only `hooks/` logic paths:
`uvx pre-commit run --all-files` at the repo root → exit 0.

**Verify**: both bakes green at 100% coverage; both ruff-clean.

## Test plan

- **Unit** (`tests/core/unit/models_test.py`): `is_revoked()` both branches.
- **Unit** (`tests/api/unit/auth_test.py`): revoked token rejected with 401.
- **Integration** (`tests/core/integration/tokens_test.py`): create (201 /
  422 x2 / 401), list (200 owner-scoped incl. a revoked row / 401), revoke (204
  + auth-refusal after / 404 x3 / 401). Every response-map branch and every
  controller line is exercised — required by `--cov-fail-under=100`.
- **Integration** (`tests/core/integration/admin_test.py`): add mints +
  shows-once (covers `get_fields` add branch + `save_model` add branch); change
  updates name (covers both change branches); existing changelist test stays.
- **Contract**: the schemathesis contract test (`tests/api/integration/schema_test.py`)
  auto-discovers the new `/api/v1/tokens` routes and exercises them on the same
  footing as the notes endpoints — no new test code, but expect it to run
  against the new paths; if it flags a schema issue, fix the schema, not the
  test.
- No new factory beyond adding `revoked_at = None` to the existing
  `TokenFactory`; revoked tokens are built with `TokenFactory(revoked_at=<dt>)`
  or `Token.issue(...)` + explicit set.

## Done criteria

- [ ] Token bake: `uv run pytest` exits 0 at **100% coverage**, including all
  new create/list/revoke, admin, model, and auth tests
- [ ] Token bake: `makemigrations --check --dry-run` → "No changes detected"
- [ ] Token bake: `ruff check` and `ruff format --check` exit 0
- [ ] Session bake: `uv run pytest` exits 0 at 100%; no `controllers.py`,
  `schemas.py`, `0003_token_revoked_at.py`, or `tokens_test.py` present; `api.py`
  free of `TokensController`
- [ ] `create` returns the raw token exactly once (present in `create` response,
  absent from `list`/`revoke`); no endpoint ever returns `digest`
- [ ] Revoked tokens are refused by `BearerTokenAuth`; `revoke` is a soft delete
  (row retained with `revoked_at`)
- [ ] Admin add mints via `Token.issue()` and shows the raw token once; `digest`
  is not an editable admin field
- [ ] `git status` clean apart from in-scope files
- [ ] `plans/README.md` status row updated (unless a dispatching reviewer owns it)

## STOP conditions

Stop and report back if:

- `makemigrations` in the bake produces a migration that differs from the
  reference shape in Step 3 (e.g. a different `dependencies` head, or extra
  operations) — it means the model diff is not what this plan assumes; do not
  hand-edit the migration to force a match.
- Coverage lands below 100% and the missing lines are in the admin `save_model`
  or `get_fields` branches — the admin flow is the coverage hotspot; add the
  missing add/change test rather than adding a `# pragma: no cover`.
- The session (`api_auth=session`) bake fails to build or leaks any token file —
  it means a guard or the removal list is wrong; do not "fix" it by deleting
  files in the baked tree.
- Setting `token.token = raw_token` fails to serialize through
  `TokenCreatedSchema` (ninja/pydantic version drift) — report; do not fall back
  to returning a raw dict without a typed schema.
- The contract test (`schema_test.py`) fails on the new routes — surface the
  schema mismatch; it usually means a response schema is under-specified, not a
  test bug.

## Maintenance notes

- **Coordinate with plan 020 (UUID pk squash).** This plan adds
  `core/migrations/0003_token_revoked_at.py` on top of `0002_token`, and typed
  the schema `id`/`token_id` fields as `int` because `Token.pk` is
  `BigAutoField` today. If 020 lands **after** this plan, its fresh squashed
  `core` initial must include the `revoked_at` column (absorbing `0003`), and
  the `TokenOutSchema.id` / `revoke_token(token_id: int)` types must change to
  `uuid.UUID`. If 020 lands **first**, regenerate `0003` against 020's squashed
  initial (its dependency head changes) and flip those two types before landing
  this plan. Whichever order, run `makemigrations --check` in the bake to catch
  a stale head.
- The `revoked_at` soft-delete deliberately preserves the row for audit; a
  future retention job (out of scope) could hard-delete tokens revoked long ago.
- If a future plan promotes token auth to a standalone knob, the nested
  `{% raw %}{% if cookiecutter.api_auth == "token" %}{% endraw %}` guards in
  `api.py` (Step 6) and the removal-list block (Step 10) are the two places that
  know about the `use_example_api=yes AND api_auth=token` coupling.
- **Coordinate with plan 017 (OpenAPI drift gate).** The controller carries
  `use_unique_op_id=False` so the exported v1 schema stays deterministic. If
  017 lands first, its operation-id regression test must gain the `tokens_*`
  ids for `api_auth=token` bakes when this plan lands (and vice versa: if this
  plan lands first, 017 writes its test knob-aware from the start).
- `throttling.py` was analyzed and intentionally left unchanged; if the throttle
  design ever charges authenticated `/api/v1/` traffic differently, re-check
  whether `create` needs its own budget (it is auth-guarded, so today it does
  not).
