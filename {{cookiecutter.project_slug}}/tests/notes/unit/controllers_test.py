{% if cookiecutter.api_auth == "jwt" -%}
from collections.abc import Callable
{% endif -%}
from http import HTTPStatus
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from faker import Faker
    from ninja_extra.testing import TestClient

    from apps.notes.models import Note

pytestmark = pytest.mark.django_db


def test_get_note_returns_401_when_anonymous(
    faker: Faker,
    notes_controller_client: TestClient,
) -> None:
    response = notes_controller_client.get(f"/{faker.uuid4()}")

    assert response.status_code == HTTPStatus.UNAUTHORIZED


def test_get_note_returns_note_when_authenticated_owner(
    {%- if cookiecutter.api_auth == "jwt" %}
    jwt_auth_headers_for_user: Callable[[object], dict[str, str]],
    {%- endif %}
    notes_controller_client: TestClient,
    note: Note,
) -> None:
{% if cookiecutter.api_auth == "jwt" %}
    response = notes_controller_client.get(
        f"/{note.id}",
        headers=jwt_auth_headers_for_user(note.owner),
    )
{% else %}
    response = notes_controller_client.get(f"/{note.id}", user=note.owner)
{% endif %}
    assert response.status_code == HTTPStatus.OK
    assert response.data["id"] == str(note.id)
