---
name: new-api-resource
description: 'Scaffold a new authenticated, owner-scoped API resource (model, schemas, ninja-extra controller, admin, migration, factory, tests) following this project''s AGENTS.md conventions. Use when adding a new REST resource / endpoint / CRUD app. Trigger: "new resource", "add an endpoint", "new model API".'
allowed-tools: Read, Write, Edit, Bash
---

# New API Resource

Use this skill to add a new authenticated, owner-scoped REST resource to this
project. It covers the model, schemas, ninja-extra controller, admin, migration,
factory, fixtures, integration tests, and unit tests expected by the generated
project gates.

This is a first-party project recipe, not an upstream vendored skill. It fits
the template's agent-first posture: the skill gives a complete first pass, while
the generated project's CI gates provide the actual enforcement through 100%
coverage, Ruff, Ty, django-extra-checks, and the migration linter.

The skill is self-contained. Do not depend on `apps.notes` or `tests/notes`
existing, because projects baked without the example API delete those files.

## Inputs

Collect these names before editing:

- Resource app, snake-case plural: `widgets`
- Model class, PascalCase singular: `Widget`
- Model variable, snake-case singular: `widget`
- Owner: default to the authenticated user unless the project has a different
  ownership model.
- Scalar fields: start with `name` and `description` unless the domain needs
  different fields.

The templates below use:

- `<app>` for the snake-case plural app name, such as `widgets`.
- `<Model>` for the PascalCase singular model name, such as `Widget`.
- `<model>` for the snake-case singular model name, such as `widget`.

## Convention Checklist

<!-- markdownlint-disable MD029 -->

### Model - `src/apps/<app>/models.py`

1. Define `__str__` (extra-checks `model-attribute: __str__`).
2. Define `Meta.ordering` (extra-checks `model-meta-attribute: ordering`).
3. Register the model in admin (extra-checks `model-admin`).
4. Every field has a gettext `verbose_name` (`field-verbose-name`,
   `field-verbose-name-gettext`, `field-verbose-name-gettext-case`); help text,
   if any, is gettext (`field-help-text-gettext`).
5. FKs declare explicit `related_name` and `db_index`
   (`field-related-name`, `field-foreign-key-db-index: always`).
6. Choice fields use a DB constraint (`field-choices-constraint`).
7. Use `UniqueConstraint`, never `unique_together` (`no-unique-together`).
8. Respect null rules (`field-null`, `field-text-null`, `field-default-null`);
   text fields use `blank=True`, not `null=True`.
9. Inherit `UUIDModel, CreatedAtUpdatedAtModel` from `apps.core.models`
   (UUIDv7 pk plus `created_at`/`updated_at`) for owner-owned resources.
10. Order model fields logically, not alphabetically: inherited timestamps
    first, then relations (the `owner` FK), then scalar attributes, with large
    `TextField` bodies last.
11. Add an index for the owner-scoped list query:
    `Meta.indexes = (models.Index(fields=["owner", "-created_at"]),)`.

### Schemas - `src/apps/<app>/schemas.py`

12. Provide the In/Out/Filter split (`<Model>InSchema`, `<Model>OutSchema`,
    `<Model>FilterSchema`).
13. `<Model>InSchema` is closed to writable fields only, each validated
    (`max_length`, `min_length` for required text, `pattern=NO_NUL_PATTERN`).
14. Order Ninja schema fields to match the model's field order, not
    alphabetically.

### Controller - `src/apps/<app>/controllers.py`

15. Use a ninja-extra class-based controller (`@api_controller`,
    `ControllerBase`) mounted at the resource prefix (`/<app>`), with
    route-local paths relative.
16. Set auth on the controller. For session-auth projects, use `django_auth`.
    For token-auth projects, mirror the generated project's existing
    bearer-token auth helper. The API has no default auth; never ship a
    mutating endpoint unauthenticated.
17. Owner-scope every lookup with `get_object_or_404(<Model>, id=...,
    owner=request.user)` (IDOR protection: other users' rows 404).
18. Each operation's `response=` map declares the error schemas it can emit
    (400/401/403/404/422 as applicable) using `ErrorSchema` /
    `ValidationErrorSchema` from `apps.api.schemas`.
19. List uses `BoundedLimitOffsetPagination`, `@ordering(...)`,
    `@searching(...)`, and `filters.filter(<Model>.objects.filter(
    owner=request.user))`.
20. Alphabetize the controller's public methods (`create`, `delete`, `get`,
    `list`, `update`); `request` and other framework-required leading params
    are exempt from parameter alphabetization.

### Admin - `src/apps/<app>/admin.py`

21. Use `@admin.register(<Model>)` on an `unfold.admin.ModelAdmin` subclass.
22. Lead `list_display` with `created_at`, `updated_at`, then other columns.
23. Declare `list_select_related` for FK columns shown in the list.

### App Config - `src/apps/<app>/apps.py`

24. Add an `AppConfig` subclass with `name = "apps.<app>"`.

### Migrations - `src/apps/<app>/migrations/`

25. Run `manage.py makemigrations <app>` and keep the migration.
26. Annotate the generated migration. `makemigrations` emits `dependencies`
    and `operations` as bare mutable class attributes, which Ruff `RUF012`
    rejects. Add `from typing import ClassVar` and annotate
    `dependencies: ClassVar[list[tuple[str, str]]]` and
    `operations: ClassVar[list[object]]`.
27. Run `ruff format` on the migration. `makemigrations` emits long
    single-line field definitions that the formatter wraps.

### Factory - `tests/factories.py`

28. Add a `<Model>Factory(factory.django.DjangoModelFactory)` with
    `owner = factory.SubFactory(UserFactory)` and Faker-backed fields.
29. Order factory fields to match the model's field order; place a factory
    after any factory it references via `SubFactory` (so `UserFactory` first).

### Factory Registration - `tests/conftest.py` and per-tree conftest

30. Register `<Model>Factory` in `tests/conftest.py` with
    `register(<Model>Factory)`, and import it in the factories import line.
31. In `tests/<app>/integration/conftest.py`, register named model fixtures
    with sequence suffixes (`<model>_1`, `<model>_2`) and a
    `<model>_owner_user_1` via `LazyFixture("user_1")` for IDOR tests.
32. In `tests/<app>/unit/conftest.py`, expose a `<app>_controller_client`
    fixture (`ninja_extra.testing.TestClient`).

### Tests - `tests/<app>/{integration,unit}/`

33. Organize by app then type; `tests/conftest.py` auto-applies the
    `integration`/`unit` marker from the path segment, so do not add manual
    markers.
34. Test names follow `test_<subject>_<expected>_when_<condition>` (or
    `for_<scenario>`); keep functions alphabetized within each file.
35. Drive endpoints through the ninja `TestClient` fixtures (`v1_api_client`,
    `authenticated_v1_api_client`), read `response.data`, use
    router-relative paths, and pass `user=` for authenticated calls when not
    using `authenticated_v1_api_client`.
36. Cover the full behavior set so 100% coverage is reached: create (201,
    401, two 422 cases), delete (204 owner, 404 other user), detail (200
    owner, 404 other user), list (pagination cap, 401, 422 limit/offset over
    max, unknown-ordering-ignored, owner-only, filter, order, second page,
    search across both text fields), update (200 owner, 422 over-length, 404
    other user). An under-specified test set leaves controller branches
    uncovered and fails `--cov-fail-under=100`.
37. Admin: add a staff/superuser changelist-200 test resolving the URL with
    `django.urls.reverse("admin:<app>_<model>_changelist")`.
38. Use Faker/factory values for incidental data; keep fixed literals only
    when they are the behavior under test; avoid `Model.objects.create(...)`
    and use factories.

### Wiring

39. Add `"apps.<app>"` to `INSTALLED_APPS` (`# Project` block,
    alphabetically), add `<app>` to `[tool.django_migration_linter]
    include_apps`, and import plus register the controller in
    `src/apps/api/api.py` (`v1_api.register_controllers(NotesController,
    <Model>sController)` or the local equivalent).
40. Final verification is the full generated gate: `uv run pytest` at 100%
    coverage, `uv run pre-commit run --all-files`, and the migration CI checks
    (`manage.py makemigrations --check --dry-run` plus `manage.py
    lintmigrations`).

<!-- markdownlint-enable MD029 -->

## Embedded File Templates

The templates below are the minimal owner-scoped shape validated against this
project's generated gates. Replace placeholder names consistently, then adjust
fields and tests for the real resource.

### `src/apps/<app>/models.py`

```python
from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.models import CreatedAtUpdatedAtModel, UUIDModel


class <Model>(UUIDModel, CreatedAtUpdatedAtModel):
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        db_index=True,
        on_delete=models.CASCADE,
        related_name="<app>",
        verbose_name=_("owner"),
    )
    name = models.CharField(_("name"), max_length=255)
    description = models.TextField(_("description"), blank=True)

    class Meta:
        indexes = (models.Index(fields=["owner", "-created_at"]),)
        ordering = ("-created_at",)
        verbose_name = _("<model>")
        verbose_name_plural = _("<app>")

    def __str__(self) -> str:
        return self.name
```

### `src/apps/<app>/schemas.py`

```python
import uuid
from datetime import datetime
from typing import Annotated

from ninja import Field, FilterLookup, FilterSchema, Schema

NO_NUL_PATTERN = r"^[^\x00]*$"


class <Model>FilterSchema(FilterSchema):
    name: Annotated[str | None, FilterLookup("name__icontains")] = None


class <Model>InSchema(Schema):
    name: str = Field(max_length=255, min_length=1, pattern=NO_NUL_PATTERN)
    description: str = Field("", pattern=NO_NUL_PATTERN)


class <Model>OutSchema(Schema):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    name: str
    description: str
```

### `src/apps/<app>/controllers.py`

```python
import uuid

from django.db.models import QuerySet
from django.http import HttpRequest
from django.shortcuts import get_object_or_404
from ninja import Query, Status
from ninja.security import django_auth
from ninja_extra import (
    ControllerBase,
    api_controller,
    http_delete,
    http_get,
    http_post,
    http_put,
)
from ninja_extra.ordering import Ordering, ordering
from ninja_extra.pagination import paginate
from ninja_extra.schemas import NinjaPaginationResponseSchema
from ninja_extra.searching import Searching, searching

from apps.api.pagination import BoundedLimitOffsetPagination
from apps.api.schemas import ErrorSchema, ValidationErrorSchema

from .models import <Model>
from .schemas import <Model>FilterSchema, <Model>InSchema, <Model>OutSchema


@api_controller(
    "/<app>",
    auth=django_auth,
    tags=["<app>"],
)
class <Model>sController(ControllerBase):
    @http_post(
        "",
        response={
            201: <Model>OutSchema,
            400: ErrorSchema,
            401: ErrorSchema,
            403: ErrorSchema,
            422: ValidationErrorSchema,
        },
    )
    def create_<model>(
        self, request: HttpRequest, payload: <Model>InSchema
    ) -> Status[<Model>]:
        <model> = <Model>.objects.create(owner=request.user, **payload.dict())
        return Status(201, <model>)

    @http_delete(
        "/{<model>_id}",
        response={
            204: None,
            400: ErrorSchema,
            401: ErrorSchema,
            403: ErrorSchema,
            404: ErrorSchema,
            422: ValidationErrorSchema,
        },
    )
    def delete_<model>(
        self, request: HttpRequest, <model>_id: uuid.UUID
    ) -> Status[None]:
        <model> = get_object_or_404(<Model>, id=<model>_id, owner=request.user)
        <model>.delete()
        return Status(204, None)

    @http_get(
        "/{<model>_id}",
        response={
            200: <Model>OutSchema,
            400: ErrorSchema,
            401: ErrorSchema,
            404: ErrorSchema,
            422: ValidationErrorSchema,
        },
    )
    def get_<model>(self, request: HttpRequest, <model>_id: uuid.UUID) -> <Model>:
        return get_object_or_404(<Model>, id=<model>_id, owner=request.user)

    @http_get(
        "",
        response={
            200: NinjaPaginationResponseSchema[<Model>OutSchema],
            401: ErrorSchema,
            422: ValidationErrorSchema,
        },
    )
    @paginate(BoundedLimitOffsetPagination)
    @ordering(Ordering, ordering_fields=["created_at", "name"])
    @searching(Searching, search_fields=["description", "name"])
    def list_<app>(
        self, request: HttpRequest, filters: Query[<Model>FilterSchema]
    ) -> QuerySet[<Model>]:
        return filters.filter(<Model>.objects.filter(owner=request.user))

    @http_put(
        "/{<model>_id}",
        response={
            200: <Model>OutSchema,
            400: ErrorSchema,
            401: ErrorSchema,
            403: ErrorSchema,
            404: ErrorSchema,
            422: ValidationErrorSchema,
        },
    )
    def update_<model>(
        self, request: HttpRequest, <model>_id: uuid.UUID, payload: <Model>InSchema
    ) -> <Model>:
        <model> = get_object_or_404(<Model>, id=<model>_id, owner=request.user)
        <model>.description = payload.description
        <model>.name = payload.name
        <model>.save()
        return <model>
```

For projects with public API throttling enabled, mirror the existing generated
controller pattern by importing `get_public_api_throttles` and adding
`throttle=get_public_api_throttles()` to `@api_controller(...)`.

For projects using bearer-token auth instead of session auth, mirror the
existing generated controller pattern by importing the bearer-token auth helper
and setting `auth=<that helper>` instead of `auth=django_auth`.

### `src/apps/<app>/admin.py`

```python
from django.contrib import admin
from unfold.admin import ModelAdmin

from .models import <Model>


@admin.register(<Model>)
class <Model>Admin(ModelAdmin):
    list_display = ("created_at", "updated_at", "owner", "name")
    list_select_related = ("owner",)
```

### `src/apps/<app>/apps.py`

```python
from django.apps import AppConfig


class <Model>sConfig(AppConfig):
    name = "apps.<app>"
```

### Migration hand-edit

After `uv run manage.py makemigrations <app>`, edit the generated migration to
use `ClassVar` annotations. Then run `uv run ruff format
src/apps/<app>/migrations`.

```python
import uuid
from typing import ClassVar

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies: ClassVar[list[tuple[str, str]]] = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations: ClassVar[list[object]] = [
        # Keep makemigrations output here, then run ruff format.
    ]
```

### `tests/factories.py`

Add the factory import and registration without disrupting existing factories.

```python
from apps.<app>.models import <Model>


class <Model>Factory(factory.django.DjangoModelFactory):
    owner = factory.SubFactory(UserFactory)
    name = factory.Faker("sentence")
    description = factory.Faker("paragraph")

    class Meta:
        model = <Model>
```

### `tests/conftest.py`

```python
from tests.factories import <Model>Factory, UserFactory

register(UserFactory)
register(<Model>Factory)
```

If `tests/utils.py` does not exist because the project was baked without the
example API, create the authenticated wrapper before using the integration
test template:

```python
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ninja.testing import TestClient
    from ninja.testing.client import NinjaResponse

    from apps.core.models import User


class AuthenticatedTestClient:
    def __init__(self, client: TestClient, user: User) -> None:
        self._client = client
        self.user = user

    def delete(self, path: str) -> NinjaResponse:
        return self._client.delete(path, user=self.user)

    def get(
        self, path: str, query_params: dict[str, object] | None = None
    ) -> NinjaResponse:
        return self._client.get(path, query_params=query_params, user=self.user)

    def post(self, path: str, json: dict[str, object] | None = None) -> NinjaResponse:
        return self._client.post(path, json=json, user=self.user)

    def put(self, path: str, json: dict[str, object] | None = None) -> NinjaResponse:
        return self._client.put(path, json=json, user=self.user)
```

Then add this fixture to `tests/conftest.py` if it is missing:

```python
@pytest.fixture
def authenticated_v1_api_client(
    v1_api_client: TestClient,
    user: User,
) -> AuthenticatedTestClient:
    return AuthenticatedTestClient(v1_api_client, user)
```

### `tests/<app>/integration/conftest.py`

```python
from pytest_factoryboy import LazyFixture, register

from tests.factories import <Model>Factory, UserFactory

register(UserFactory, "user_1")
register(<Model>Factory, "<model>_1")
register(<Model>Factory, "<model>_2")
register(<Model>Factory, "<model>_owner_user_1", owner=LazyFixture("user_1"))
```

### `tests/<app>/unit/conftest.py`

```python
import pytest
from ninja_extra.testing import TestClient

from apps.<app>.controllers import <Model>sController


@pytest.fixture
def <app>_controller_client() -> TestClient:
    return TestClient(<Model>sController)
```

### `tests/<app>/integration/admin_test.py`

```python
from http import HTTPStatus
from typing import TYPE_CHECKING

import pytest
from django.urls import reverse

if TYPE_CHECKING:
    from django.test import Client

    from apps.<app>.models import <Model>
    from apps.core.models import User

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize("user__is_staff", [True])
@pytest.mark.parametrize("user__is_superuser", [True])
def test_<model>_changelist_returns_200_when_staff(
    client: Client,
    <model>: <Model>,
    user: User,
) -> None:
    assert <model>.pk is not None
    client.force_login(user)

    response = client.get(reverse("admin:<app>_<model>_changelist"))

    assert response.status_code == HTTPStatus.OK
```

### `tests/<app>/unit/controllers_test.py`

```python
from http import HTTPStatus
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from faker import Faker
    from ninja_extra.testing import TestClient

    from apps.<app>.models import <Model>

pytestmark = pytest.mark.django_db


def test_get_<model>_returns_401_when_anonymous(
    faker: Faker,
    <app>_controller_client: TestClient,
) -> None:
    response = <app>_controller_client.get(f"/{faker.uuid4()}")

    assert response.status_code == HTTPStatus.UNAUTHORIZED


def test_get_<model>_returns_<model>_when_authenticated_owner(
    <app>_controller_client: TestClient,
    <model>: <Model>,
) -> None:
    response = <app>_controller_client.get(f"/{<model>.id}", user=<model>.owner)

    assert response.status_code == HTTPStatus.OK
    assert response.data["id"] == str(<model>.id)
```

For bearer-token projects, mirror the generated token fixture pattern in the
unit test: parametrize the token user to `<model>__owner`, request `raw_token`,
and pass `headers={"Authorization": f"Bearer {raw_token}"}`.

### `tests/<app>/integration/<app>_test.py`

```python
from datetime import timedelta
from http import HTTPStatus
from typing import TYPE_CHECKING

import pytest
from django.utils import timezone
from ninja.conf import settings as ninja_settings

from apps.<app>.models import <Model>
from apps.api.pagination import PAGINATION_MAX_LIMIT

if TYPE_CHECKING:
    from ninja.testing import TestClient

    from tests.utils import AuthenticatedTestClient

pytestmark = pytest.mark.django_db


def test_create_<model>_returns_201_when_authenticated(
    authenticated_v1_api_client: AuthenticatedTestClient,
) -> None:
    response = authenticated_v1_api_client.post(
        "/<app>", json={"description": "Some description", "name": "My <model>"}
    )

    assert response.status_code == HTTPStatus.CREATED
    payload = response.data
    assert payload["description"] == "Some description"
    assert payload["name"] == "My <model>"
    <model> = <Model>.objects.get(id=payload["id"])
    assert <model>.owner == authenticated_v1_api_client.user
    assert str(<model>) == "My <model>"


def test_create_<model>_returns_401_when_anonymous(v1_api_client: TestClient) -> None:
    response = v1_api_client.post("/<app>", json={"name": "My <model>"})

    assert response.status_code == HTTPStatus.UNAUTHORIZED


def test_create_<model>_returns_422_when_name_exceeds_column_length(
    authenticated_v1_api_client: AuthenticatedTestClient,
) -> None:
    response = authenticated_v1_api_client.post("/<app>", json={"name": "x" * 256})

    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    assert not <Model>.objects.exists()


def test_create_<model>_returns_422_when_name_is_empty(
    authenticated_v1_api_client: AuthenticatedTestClient,
) -> None:
    response = authenticated_v1_api_client.post("/<app>", json={"name": ""})

    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY


def test_delete_<model>_returns_204_when_authenticated_owner(
    authenticated_v1_api_client: AuthenticatedTestClient,
    <model>: <Model>,
) -> None:
    response = authenticated_v1_api_client.delete(f"/<app>/{<model>.id}")

    assert response.status_code == HTTPStatus.NO_CONTENT
    assert not <Model>.objects.filter(id=<model>.id).exists()


def test_delete_<model>_returns_404_when_owned_by_other_user(
    authenticated_v1_api_client: AuthenticatedTestClient,
    <model>_owner_user_1: <Model>,
) -> None:
    response = authenticated_v1_api_client.delete(
        f"/<app>/{<model>_owner_user_1.id}"
    )

    assert response.status_code == HTTPStatus.NOT_FOUND
    assert <Model>.objects.filter(id=<model>_owner_user_1.id).exists()


def test_detail_<model>_returns_200_when_authenticated_owner(
    authenticated_v1_api_client: AuthenticatedTestClient,
    <model>: <Model>,
) -> None:
    response = authenticated_v1_api_client.get(f"/<app>/{<model>.id}")

    assert response.status_code == HTTPStatus.OK
    assert response.data["id"] == str(<model>.id)


def test_detail_<model>_returns_404_when_owned_by_other_user(
    authenticated_v1_api_client: AuthenticatedTestClient,
    <model>_owner_user_1: <Model>,
) -> None:
    response = authenticated_v1_api_client.get(f"/<app>/{<model>_owner_user_1.id}")

    assert response.status_code == HTTPStatus.NOT_FOUND


def test_list_<app>_caps_items_when_limit_below_total(
    authenticated_v1_api_client: AuthenticatedTestClient,
    <model>: <Model>,
    <model>_1: <Model>,
    <model>_2: <Model>,
) -> None:
    limit = 2
    <app> = [<model>, <model>_1, <model>_2]

    response = authenticated_v1_api_client.get("/<app>", query_params={"limit": limit})

    assert response.status_code == HTTPStatus.OK
    payload = response.data
    assert payload["count"] == len(<app>)
    assert len(payload["items"]) == limit


def test_list_<app>_returns_401_when_anonymous(v1_api_client: TestClient) -> None:
    response = v1_api_client.get("/<app>")

    assert response.status_code == HTTPStatus.UNAUTHORIZED


def test_list_<app>_returns_422_when_limit_exceeds_maximum(
    authenticated_v1_api_client: AuthenticatedTestClient,
) -> None:
    response = authenticated_v1_api_client.get(
        "/<app>", query_params={"limit": PAGINATION_MAX_LIMIT + 1}
    )

    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY


def test_list_<app>_returns_422_when_offset_exceeds_maximum(
    authenticated_v1_api_client: AuthenticatedTestClient,
) -> None:
    response = authenticated_v1_api_client.get(
        "/<app>",
        query_params={"offset": ninja_settings.PAGINATION_MAX_OFFSET + 1},
    )

    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY


def test_list_<app>_returns_422_when_ordering_field_is_unknown(
    authenticated_v1_api_client: AuthenticatedTestClient,
) -> None:
    response = authenticated_v1_api_client.get(
        "/<app>", query_params={"ordering": "owner__password"}
    )

    # ninja-extra silently ignores unknown ordering fields.
    assert response.status_code == HTTPStatus.OK


def test_list_<app>_returns_only_callers_<app>_when_authenticated(
    authenticated_v1_api_client: AuthenticatedTestClient,
    <model>: <Model>,
    <model>_owner_user_1: <Model>,
) -> None:
    response = authenticated_v1_api_client.get("/<app>")

    assert response.status_code == HTTPStatus.OK
    payload = response.data
    item_ids = [item["id"] for item in payload["items"]]
    assert payload["count"] == 1
    assert item_ids == [str(<model>.id)]
    assert str(<model>_owner_user_1.id) not in item_ids


@pytest.mark.parametrize("<model>__name", ["Quarterly planning"])
@pytest.mark.parametrize("<model>_1__name", ["Daily checklist"])
def test_list_<app>_filters_by_name_when_authenticated(
    authenticated_v1_api_client: AuthenticatedTestClient,
    <model>: <Model>,
    <model>_1: <Model>,
) -> None:
    response = authenticated_v1_api_client.get(
        "/<app>", query_params={"name": "planning"}
    )

    assert response.status_code == HTTPStatus.OK
    payload = response.data
    item_ids = [item["id"] for item in payload["items"]]
    assert payload["count"] == 1
    assert item_ids == [str(<model>.id)]
    assert str(<model>_1.id) not in item_ids


@pytest.mark.parametrize("<model>__name", ["Alpha"])
@pytest.mark.parametrize("<model>_1__name", ["Beta"])
def test_list_<app>_orders_by_requested_field_when_authenticated(
    authenticated_v1_api_client: AuthenticatedTestClient,
    <model>: <Model>,
    <model>_1: <Model>,
) -> None:
    response = authenticated_v1_api_client.get(
        "/<app>", query_params={"ordering": "name"}
    )

    expected_<app> = [<model>, <model>_1]

    assert response.status_code == HTTPStatus.OK
    payload = response.data
    assert payload["count"] == len(expected_<app>)
    assert [item["id"] for item in payload["items"]] == [
        str(expected_<model>.id) for expected_<model> in expected_<app>
    ]


def test_list_<app>_returns_second_page_when_offset_given(
    authenticated_v1_api_client: AuthenticatedTestClient,
    <model>: <Model>,
    <model>_1: <Model>,
    <model>_2: <Model>,
) -> None:
    <app> = [<model>, <model>_1, <model>_2]
    base_time = timezone.now()
    <Model>.objects.filter(id=<model>.id).update(created_at=base_time)
    <Model>.objects.filter(id=<model>_1.id).update(
        created_at=base_time + timedelta(minutes=1)
    )
    <Model>.objects.filter(id=<model>_2.id).update(
        created_at=base_time + timedelta(minutes=2)
    )

    response = authenticated_v1_api_client.get(
        "/<app>",
        query_params={"limit": 1, "offset": 1},
    )

    assert response.status_code == HTTPStatus.OK
    payload = response.data
    assert payload["count"] == len(<app>)
    assert [item["id"] for item in payload["items"]] == [str(<model>_1.id)]


@pytest.mark.parametrize("<model>__description", ["Remember the apricot detail"])
@pytest.mark.parametrize("<model>__name", ["Release <app>"])
@pytest.mark.parametrize("<model>_1__description", ["Unrelated description"])
@pytest.mark.parametrize("<model>_1__name", ["Apricot checklist"])
@pytest.mark.parametrize("<model>_2__description", ["No matching term"])
@pytest.mark.parametrize("<model>_2__name", ["Daily checklist"])
def test_list_<app>_searches_name_and_description_when_authenticated(
    authenticated_v1_api_client: AuthenticatedTestClient,
    <model>: <Model>,
    <model>_1: <Model>,
    <model>_2: <Model>,
) -> None:
    response = authenticated_v1_api_client.get(
        "/<app>", query_params={"ordering": "name", "search": "apricot"}
    )

    expected_<app> = [<model>_1, <model>]

    assert response.status_code == HTTPStatus.OK
    payload = response.data
    item_ids = [item["id"] for item in payload["items"]]
    assert payload["count"] == len(expected_<app>)
    assert item_ids == [str(expected_<model>.id) for expected_<model> in expected_<app>]
    assert str(<model>_2.id) not in item_ids


def test_update_<model>_returns_200_when_authenticated_owner(
    authenticated_v1_api_client: AuthenticatedTestClient,
    <model>: <Model>,
) -> None:
    <model>.name = "Original"
    <model>.save()

    response = authenticated_v1_api_client.put(
        f"/<app>/{<model>.id}",
        json={"description": "Updated description", "name": "Updated name"},
    )

    assert response.status_code == HTTPStatus.OK
    payload = response.data
    assert payload["description"] == "Updated description"
    assert payload["name"] == "Updated name"
    <model>.refresh_from_db()
    assert <model>.name == "Updated name"


def test_update_<model>_returns_422_when_name_exceeds_column_length(
    authenticated_v1_api_client: AuthenticatedTestClient,
    <model>: <Model>,
) -> None:
    original_name = <model>.name

    response = authenticated_v1_api_client.put(
        f"/<app>/{<model>.id}",
        json={"description": "Updated description", "name": "x" * 256},
    )

    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    <model>.refresh_from_db()
    assert <model>.name == original_name


def test_update_<model>_returns_404_when_owned_by_other_user(
    authenticated_v1_api_client: AuthenticatedTestClient,
    <model>_owner_user_1: <Model>,
) -> None:
    original_name = <model>_owner_user_1.name

    response = authenticated_v1_api_client.put(
        f"/<app>/{<model>_owner_user_1.id}",
        json={"description": "Updated description", "name": "Updated name"},
    )

    assert response.status_code == HTTPStatus.NOT_FOUND
    <model>_owner_user_1.refresh_from_db()
    assert <model>_owner_user_1.name == original_name
```

## Post-Generation Todo List

1. Create `src/apps/<app>/__init__.py`, `models.py`, `schemas.py`,
   `controllers.py`, `admin.py`, `apps.py`, and `migrations/__init__.py`.
2. Add tests under `tests/<app>/integration/` and `tests/<app>/unit/`, each
   with `__init__.py`.
3. Wire `"apps.<app>"` into `INSTALLED_APPS` in the `# Project` block.
4. Import and register `<Model>sController` in `src/apps/api/api.py`.
5. Add `<app>` to `[tool.django_migration_linter] include_apps`.
6. Import `<Model>Factory` in `tests/factories.py` and register it in
   `tests/conftest.py`.
7. Run `uv run manage.py makemigrations <app>`.
8. Annotate the migration with `ClassVar` for `dependencies` and `operations`.
9. Run `uv run ruff format src/apps/<app>/migrations`.
10. Start Postgres, then run the acceptance self-test.

## Acceptance Self-Test

The resource is not done until all of these pass:

```bash
docker compose -f .docker/compose/dev.yaml --env-file=.env up -d --wait postgres
uv run pytest
uv run pre-commit run --all-files
uv run manage.py makemigrations --check --dry-run
uv run manage.py lintmigrations
```

`uv run pytest` must report 100% coverage. If coverage is lower, add tests for
the uncovered behavior. Do not lower the coverage threshold and do not use
`# pragma: no cover`.
