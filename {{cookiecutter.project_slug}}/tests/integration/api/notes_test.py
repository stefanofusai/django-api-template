from http import HTTPStatus
from typing import TYPE_CHECKING

import pytest

from apps.api.pagination import PAGINATION_MAX_LIMIT
from apps.notes.models import Note

if TYPE_CHECKING:
    from django.test import Client

    from apps.core.models import User
    from tests.factories import NoteFactory

pytestmark = pytest.mark.django_db


def test_create_note_returns_201_when_authenticated(client: Client, user: User) -> None:
    client.force_login(user)

    response = client.post(
        "/api/v1/notes",
        content_type="application/json",
        data={"body": "Some body", "title": "My note"},
    )

    assert response.status_code == HTTPStatus.CREATED
    payload = response.json()
    assert payload["body"] == "Some body"
    assert payload["title"] == "My note"
    note = Note.objects.get(id=payload["id"])
    assert note.owner == user
    assert str(note) == "My note"


def test_create_note_returns_401_when_anonymous(client: Client) -> None:
    response = client.post(
        "/api/v1/notes",
        content_type="application/json",
        data={"title": "My note"},
    )

    assert response.status_code == HTTPStatus.UNAUTHORIZED


def test_delete_note_returns_204_when_authenticated_owner(
    client: Client, note_factory: type[NoteFactory], user: User
) -> None:
    note = note_factory.create(owner=user)
    client.force_login(user)

    response = client.delete(f"/api/v1/notes/{note.id}")

    assert response.status_code == HTTPStatus.NO_CONTENT
    assert not Note.objects.filter(id=note.id).exists()


def test_delete_note_returns_404_when_owned_by_other_user(
    client: Client, note_factory: type[NoteFactory], user: User
) -> None:
    other_note = note_factory.create()
    client.force_login(user)

    response = client.delete(f"/api/v1/notes/{other_note.id}")

    assert response.status_code == HTTPStatus.NOT_FOUND
    assert Note.objects.filter(id=other_note.id).exists()


def test_detail_note_returns_200_when_authenticated_owner(
    client: Client, note_factory: type[NoteFactory], user: User
) -> None:
    note = note_factory.create(owner=user)
    client.force_login(user)

    response = client.get(f"/api/v1/notes/{note.id}")

    assert response.status_code == HTTPStatus.OK
    assert response.json()["id"] == str(note.id)


def test_detail_note_returns_404_when_owned_by_other_user(
    client: Client, note_factory: type[NoteFactory], user: User
) -> None:
    other_note = note_factory.create()
    client.force_login(user)

    response = client.get(f"/api/v1/notes/{other_note.id}")

    assert response.status_code == HTTPStatus.NOT_FOUND


def test_list_notes_returns_401_when_anonymous(client: Client) -> None:
    response = client.get("/api/v1/notes")

    assert response.status_code == HTTPStatus.UNAUTHORIZED


def test_list_notes_returns_422_when_limit_exceeds_maximum(
    client: Client, user: User
) -> None:
    client.force_login(user)

    response = client.get("/api/v1/notes", {"limit": PAGINATION_MAX_LIMIT + 1})

    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY


def test_list_notes_returns_only_callers_notes_when_authenticated(
    client: Client, note_factory: type[NoteFactory], user: User
) -> None:
    own_note = note_factory.create(owner=user)
    note_factory.create()
    client.force_login(user)

    response = client.get("/api/v1/notes")

    assert response.status_code == HTTPStatus.OK
    payload = response.json()
    assert payload["count"] == 1
    assert [item["id"] for item in payload["items"]] == [str(own_note.id)]


def test_update_note_returns_200_when_authenticated_owner(
    client: Client, note_factory: type[NoteFactory], user: User
) -> None:
    note = note_factory.create(owner=user, title="Original")
    client.force_login(user)

    response = client.put(
        f"/api/v1/notes/{note.id}",
        content_type="application/json",
        data={"body": "Updated body", "title": "Updated title"},
    )

    assert response.status_code == HTTPStatus.OK
    payload = response.json()
    assert payload["body"] == "Updated body"
    assert payload["title"] == "Updated title"
    note.refresh_from_db()
    assert note.title == "Updated title"


def test_update_note_returns_404_when_owned_by_other_user(
    client: Client, note_factory: type[NoteFactory], user: User
) -> None:
    other_note = note_factory.create(title="Original")
    client.force_login(user)

    response = client.put(
        f"/api/v1/notes/{other_note.id}",
        content_type="application/json",
        data={"body": "Updated body", "title": "Updated title"},
    )

    assert response.status_code == HTTPStatus.NOT_FOUND
    other_note.refresh_from_db()
    assert other_note.title == "Original"
