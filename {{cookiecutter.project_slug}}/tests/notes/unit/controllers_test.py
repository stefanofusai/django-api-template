from http import HTTPStatus
from typing import TYPE_CHECKING

import pytest
{% if cookiecutter.api_auth == "token" %}
from apps.core.models import Token
{% endif %}
if TYPE_CHECKING:
    from faker import Faker
    from ninja_extra.testing import TestClient

    from apps.core.models import User
    from tests.factories import NoteFactory

pytestmark = pytest.mark.django_db


def test_get_note_returns_401_when_anonymous(
    faker: Faker,
    notes_controller_client: TestClient,
) -> None:
    response = notes_controller_client.get(f"/{faker.uuid4()}")

    assert response.status_code == HTTPStatus.UNAUTHORIZED


def test_get_note_returns_note_when_authenticated_owner(
    notes_controller_client: TestClient,
    note_factory: type[NoteFactory],
    user: User,
) -> None:
    note = note_factory.create(owner=user)
{% if cookiecutter.api_auth == "token" %}
    raw_token, _ = Token.issue(name="test token", user=user)
    response = notes_controller_client.get(
        f"/{note.id}",
        headers={"Authorization": f"Bearer {raw_token}"},
    )
{% else %}
    response = notes_controller_client.get(f"/{note.id}", user=user)
{% endif %}
    assert response.status_code == HTTPStatus.OK
    assert response.data["id"] == str(note.id)
