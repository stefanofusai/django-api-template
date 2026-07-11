from datetime import timedelta
from http import HTTPStatus
from typing import TYPE_CHECKING

import pytest
from django.utils import timezone
from ninja.conf import settings as ninja_settings

from apps.api.pagination import PAGINATION_MAX_LIMIT
from apps.notes.models import Note

if TYPE_CHECKING:
    from ninja.testing import TestClient

    from tests.utils import AuthenticatedTestClient

pytestmark = pytest.mark.django_db


def test_create_note_returns_201_when_authenticated(
    authenticated_v1_api_client: AuthenticatedTestClient,
) -> None:
    response = authenticated_v1_api_client.post(
        "/notes", json={"body": "Some body", "title": "My note"}
    )

    assert response.status_code == HTTPStatus.CREATED
    payload = response.data
    assert payload["body"] == "Some body"
    assert payload["title"] == "My note"
    note = Note.objects.get(id=payload["id"])
    assert note.owner == authenticated_v1_api_client.user
    assert str(note) == "My note"


def test_create_note_returns_401_when_anonymous(v1_api_client: TestClient) -> None:
    response = v1_api_client.post("/notes", json={"title": "My note"})

    assert response.status_code == HTTPStatus.UNAUTHORIZED


def test_create_note_returns_422_when_title_exceeds_column_length(
    authenticated_v1_api_client: AuthenticatedTestClient,
) -> None:
    response = authenticated_v1_api_client.post("/notes", json={"title": "x" * 256})

    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    assert not Note.objects.exists()


def test_create_note_returns_422_when_title_is_empty(
    authenticated_v1_api_client: AuthenticatedTestClient,
) -> None:
    response = authenticated_v1_api_client.post("/notes", json={"title": ""})

    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY


def test_delete_note_returns_204_when_authenticated_owner(
    authenticated_v1_api_client: AuthenticatedTestClient,
    note: Note,
) -> None:
    response = authenticated_v1_api_client.delete(f"/notes/{note.id}")

    assert response.status_code == HTTPStatus.NO_CONTENT
    assert not Note.objects.filter(id=note.id).exists()


def test_delete_note_returns_404_when_owned_by_other_user(
    authenticated_v1_api_client: AuthenticatedTestClient,
    note_owner_user_1: Note,
) -> None:
    response = authenticated_v1_api_client.delete(f"/notes/{note_owner_user_1.id}")

    assert response.status_code == HTTPStatus.NOT_FOUND
    assert Note.objects.filter(id=note_owner_user_1.id).exists()


def test_detail_note_returns_200_when_authenticated_owner(
    authenticated_v1_api_client: AuthenticatedTestClient,
    note: Note,
) -> None:
    response = authenticated_v1_api_client.get(f"/notes/{note.id}")

    assert response.status_code == HTTPStatus.OK
    assert response.data["id"] == str(note.id)


def test_detail_note_returns_404_when_owned_by_other_user(
    authenticated_v1_api_client: AuthenticatedTestClient,
    note_owner_user_1: Note,
) -> None:
    response = authenticated_v1_api_client.get(f"/notes/{note_owner_user_1.id}")

    assert response.status_code == HTTPStatus.NOT_FOUND


def test_list_notes_caps_items_when_limit_below_total(
    authenticated_v1_api_client: AuthenticatedTestClient,
    note: Note,
    note_1: Note,
    note_2: Note,
) -> None:
    limit = 2
    notes = [note, note_1, note_2]

    response = authenticated_v1_api_client.get("/notes", query_params={"limit": limit})

    assert response.status_code == HTTPStatus.OK
    payload = response.data
    assert payload["count"] == len(notes)
    assert len(payload["items"]) == limit


def test_list_notes_returns_401_when_anonymous(v1_api_client: TestClient) -> None:
    response = v1_api_client.get("/notes")

    assert response.status_code == HTTPStatus.UNAUTHORIZED


def test_list_notes_returns_422_when_limit_exceeds_maximum(
    authenticated_v1_api_client: AuthenticatedTestClient,
) -> None:
    response = authenticated_v1_api_client.get(
        "/notes", query_params={"limit": PAGINATION_MAX_LIMIT + 1}
    )

    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY


def test_list_notes_returns_422_when_offset_exceeds_maximum(
    authenticated_v1_api_client: AuthenticatedTestClient,
) -> None:
    response = authenticated_v1_api_client.get(
        "/notes",
        query_params={"offset": ninja_settings.PAGINATION_MAX_OFFSET + 1},
    )

    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY


def test_list_notes_returns_422_when_ordering_field_is_unknown(
    authenticated_v1_api_client: AuthenticatedTestClient,
) -> None:
    response = authenticated_v1_api_client.get(
        "/notes", query_params={"ordering": "owner__password"}
    )

    # ninja-extra silently ignores unknown ordering fields.
    assert response.status_code == HTTPStatus.OK


def test_list_notes_returns_only_callers_notes_when_authenticated(
    authenticated_v1_api_client: AuthenticatedTestClient,
    note: Note,
    note_owner_user_1: Note,
) -> None:
    response = authenticated_v1_api_client.get("/notes")

    assert response.status_code == HTTPStatus.OK
    payload = response.data
    item_ids = [item["id"] for item in payload["items"]]
    assert payload["count"] == 1
    assert item_ids == [str(note.id)]
    assert str(note_owner_user_1.id) not in item_ids


@pytest.mark.parametrize("ordering", [None, "title", "-title"])
def test_list_notes_returns_disjoint_pages_when_ordering_values_tie(
    authenticated_v1_api_client: AuthenticatedTestClient,
    ordering: str | None,
) -> None:
    notes = [
        Note.objects.create(
            body="Same body",
            owner=authenticated_v1_api_client.user,
            title="Same title",
        )
        for _ in range(5)
    ]
    Note.objects.filter(id__in=[note.id for note in notes]).update(
        created_at=timezone.now()
    )
    item_ids = []

    for offset in (0, 2, 4):
        query_params: dict[str, object] = {"limit": 2, "offset": offset}

        if ordering is not None:
            query_params["ordering"] = ordering

        response = authenticated_v1_api_client.get("/notes", query_params=query_params)

        assert response.status_code == HTTPStatus.OK
        assert response.data["count"] == len(notes)
        item_ids.extend(item["id"] for item in response.data["items"])

    assert len(item_ids) == len(set(item_ids)) == len(notes)
    assert set(item_ids) == {str(note.id) for note in notes}


@pytest.mark.parametrize("note__title", ["Quarterly planning"])
@pytest.mark.parametrize("note_1__title", ["Daily checklist"])
def test_list_notes_filters_by_title_when_authenticated(
    authenticated_v1_api_client: AuthenticatedTestClient,
    note: Note,
    note_1: Note,
) -> None:
    response = authenticated_v1_api_client.get(
        "/notes", query_params={"title": "planning"}
    )

    assert response.status_code == HTTPStatus.OK
    payload = response.data
    item_ids = [item["id"] for item in payload["items"]]
    assert payload["count"] == 1
    assert item_ids == [str(note.id)]
    assert str(note_1.id) not in item_ids


@pytest.mark.parametrize("note__title", ["Alpha"])
@pytest.mark.parametrize("note_1__title", ["Beta"])
def test_list_notes_orders_by_requested_field_when_authenticated(
    authenticated_v1_api_client: AuthenticatedTestClient,
    note: Note,
    note_1: Note,
) -> None:
    response = authenticated_v1_api_client.get(
        "/notes", query_params={"ordering": "title"}
    )

    expected_notes = [note, note_1]

    assert response.status_code == HTTPStatus.OK
    payload = response.data
    assert payload["count"] == len(expected_notes)
    assert [item["id"] for item in payload["items"]] == [
        str(expected_note.id) for expected_note in expected_notes
    ]


def test_list_notes_returns_second_page_when_offset_given(
    authenticated_v1_api_client: AuthenticatedTestClient,
    note: Note,
    note_1: Note,
    note_2: Note,
) -> None:
    notes = [note, note_1, note_2]
    base_time = timezone.now()
    Note.objects.filter(id=note.id).update(created_at=base_time)
    Note.objects.filter(id=note_1.id).update(
        created_at=base_time + timedelta(minutes=1)
    )
    Note.objects.filter(id=note_2.id).update(
        created_at=base_time + timedelta(minutes=2)
    )

    response = authenticated_v1_api_client.get(
        "/notes",
        query_params={"limit": 1, "offset": 1},
    )

    assert response.status_code == HTTPStatus.OK
    payload = response.data
    assert payload["count"] == len(notes)
    assert [item["id"] for item in payload["items"]] == [str(note_1.id)]


@pytest.mark.parametrize("note__body", ["Remember the apricot launch detail"])
@pytest.mark.parametrize("note__title", ["Release notes"])
@pytest.mark.parametrize("note_1__body", ["Unrelated body"])
@pytest.mark.parametrize("note_1__title", ["Apricot checklist"])
@pytest.mark.parametrize("note_2__body", ["No matching term"])
@pytest.mark.parametrize("note_2__title", ["Daily checklist"])
def test_list_notes_searches_title_and_body_when_authenticated(
    authenticated_v1_api_client: AuthenticatedTestClient,
    note: Note,
    note_1: Note,
    note_2: Note,
) -> None:
    response = authenticated_v1_api_client.get(
        "/notes", query_params={"ordering": "title", "search": "apricot"}
    )

    expected_notes = [note_1, note]

    assert response.status_code == HTTPStatus.OK
    payload = response.data
    item_ids = [item["id"] for item in payload["items"]]
    assert payload["count"] == len(expected_notes)
    assert item_ids == [str(expected_note.id) for expected_note in expected_notes]
    assert str(note_2.id) not in item_ids


def test_update_note_returns_200_when_authenticated_owner(
    authenticated_v1_api_client: AuthenticatedTestClient,
    note: Note,
) -> None:
    note.title = "Original"
    note.save()

    response = authenticated_v1_api_client.put(
        f"/notes/{note.id}",
        json={"body": "Updated body", "title": "Updated title"},
    )

    assert response.status_code == HTTPStatus.OK
    payload = response.data
    assert payload["body"] == "Updated body"
    assert payload["title"] == "Updated title"
    note.refresh_from_db()
    assert note.title == "Updated title"


def test_update_note_returns_422_when_title_exceeds_column_length(
    authenticated_v1_api_client: AuthenticatedTestClient,
    note: Note,
) -> None:
    original_title = note.title

    response = authenticated_v1_api_client.put(
        f"/notes/{note.id}",
        json={"body": "Updated body", "title": "x" * 256},
    )

    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    note.refresh_from_db()
    assert note.title == original_title


def test_update_note_returns_404_when_owned_by_other_user(
    authenticated_v1_api_client: AuthenticatedTestClient,
    note_owner_user_1: Note,
) -> None:
    original_title = note_owner_user_1.title

    response = authenticated_v1_api_client.put(
        f"/notes/{note_owner_user_1.id}",
        json={"body": "Updated body", "title": "Updated title"},
    )

    assert response.status_code == HTTPStatus.NOT_FOUND
    note_owner_user_1.refresh_from_db()
    assert note_owner_user_1.title == original_title
