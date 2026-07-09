from http import HTTPStatus
from typing import TYPE_CHECKING

import pytest
{% if cookiecutter.api_auth == "token" -%}
from pytest_factoryboy import LazyFixture
{% endif %}
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


{% if cookiecutter.api_auth == "token" -%}
@pytest.mark.parametrize("token__user", [LazyFixture("note__owner")])
{% endif -%}
def test_get_note_returns_note_when_authenticated_owner(
    notes_controller_client: TestClient,
    note: Note,{% if cookiecutter.api_auth == "token" %}
    raw_token: str,{% endif %}
) -> None:
{% if cookiecutter.api_auth == "token" %}
    response = notes_controller_client.get(
        f"/{note.id}",
        headers={"Authorization": f"Bearer {raw_token}"},
    )
{% else %}
    response = notes_controller_client.get(f"/{note.id}", user=note.owner)
{% endif %}
    assert response.status_code == HTTPStatus.OK
    assert response.data["id"] == str(note.id)
