from http import HTTPStatus
from typing import TYPE_CHECKING

import pytest

from apps.api.pagination import PAGINATION_MAX_LIMIT
from apps.notes.models import Note

if TYPE_CHECKING:
    from ninja.testing import TestClient

    from tests.conftest import _AuthenticatedClient
    from tests.factories import NoteFactory

pytestmark = pytest.mark.django_db


def test_create_note_returns_201_when_authenticated(
    authenticated_client: _AuthenticatedClient,
) -> None:
    response = authenticated_client.post(
        "/notes", json={"body": "Some body", "title": "My note"}
    )

    assert response.status_code == HTTPStatus.CREATED
    payload = response.data
    assert payload["body"] == "Some body"
    assert payload["title"] == "My note"
    note = Note.objects.get(id=payload["id"])
    assert note.owner == authenticated_client.user
    assert str(note) == "My note"


def test_create_note_returns_401_when_anonymous(v1_api_client: TestClient) -> None:
    response = v1_api_client.post("/notes", json={"title": "My note"})

    assert response.status_code == HTTPStatus.UNAUTHORIZED


def test_delete_note_returns_204_when_authenticated_owner(
    authenticated_client: _AuthenticatedClient, note_factory: type[NoteFactory]
) -> None:
    note = note_factory.create(owner=authenticated_client.user)

    response = authenticated_client.delete(f"/notes/{note.id}")

    assert response.status_code == HTTPStatus.NO_CONTENT
    assert not Note.objects.filter(id=note.id).exists()


def test_delete_note_returns_404_when_owned_by_other_user(
    authenticated_client: _AuthenticatedClient, note_factory: type[NoteFactory]
) -> None:
    other_note = note_factory.create()

    response = authenticated_client.delete(f"/notes/{other_note.id}")

    assert response.status_code == HTTPStatus.NOT_FOUND
    assert Note.objects.filter(id=other_note.id).exists()


def test_detail_note_returns_200_when_authenticated_owner(
    authenticated_client: _AuthenticatedClient, note_factory: type[NoteFactory]
) -> None:
    note = note_factory.create(owner=authenticated_client.user)

    response = authenticated_client.get(f"/notes/{note.id}")

    assert response.status_code == HTTPStatus.OK
    assert response.data["id"] == str(note.id)


def test_detail_note_returns_404_when_owned_by_other_user(
    authenticated_client: _AuthenticatedClient, note_factory: type[NoteFactory]
) -> None:
    other_note = note_factory.create()

    response = authenticated_client.get(f"/notes/{other_note.id}")

    assert response.status_code == HTTPStatus.NOT_FOUND


def test_list_notes_returns_401_when_anonymous(v1_api_client: TestClient) -> None:
    response = v1_api_client.get("/notes")

    assert response.status_code == HTTPStatus.UNAUTHORIZED


def test_list_notes_returns_422_when_limit_exceeds_maximum(
    authenticated_client: _AuthenticatedClient,
) -> None:
    response = authenticated_client.get(
        "/notes", query_params={"limit": PAGINATION_MAX_LIMIT + 1}
    )

    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY


def test_list_notes_returns_only_callers_notes_when_authenticated(
    authenticated_client: _AuthenticatedClient, note_factory: type[NoteFactory]
) -> None:
    own_note = note_factory.create(owner=authenticated_client.user)
    note_factory.create()

    response = authenticated_client.get("/notes")

    assert response.status_code == HTTPStatus.OK
    payload = response.data
    assert payload["count"] == 1
    assert [item["id"] for item in payload["items"]] == [str(own_note.id)]


def test_update_note_returns_200_when_authenticated_owner(
    authenticated_client: _AuthenticatedClient, note_factory: type[NoteFactory]
) -> None:
    note = note_factory.create(owner=authenticated_client.user, title="Original")

    response = authenticated_client.put(
        f"/notes/{note.id}",
        json={"body": "Updated body", "title": "Updated title"},
    )

    assert response.status_code == HTTPStatus.OK
    payload = response.data
    assert payload["body"] == "Updated body"
    assert payload["title"] == "Updated title"
    note.refresh_from_db()
    assert note.title == "Updated title"


def test_update_note_returns_404_when_owned_by_other_user(
    authenticated_client: _AuthenticatedClient, note_factory: type[NoteFactory]
) -> None:
    other_note = note_factory.create(title="Original")

    response = authenticated_client.put(
        f"/notes/{other_note.id}",
        json={"body": "Updated body", "title": "Updated title"},
    )

    assert response.status_code == HTTPStatus.NOT_FOUND
    other_note.refresh_from_db()
    assert other_note.title == "Original"
