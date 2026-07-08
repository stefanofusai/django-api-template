from http import HTTPStatus
from typing import TYPE_CHECKING

import pytest
from django.urls import reverse

if TYPE_CHECKING:
    from django.test import Client

    from apps.core.models import User
    from apps.notes.models import Note

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize("user__is_staff", [True])
@pytest.mark.parametrize("user__is_superuser", [True])
def test_note_changelist_returns_200_when_staff(
    client: Client,
    note: Note,
    user: User,
) -> None:
    assert note.pk is not None
    client.force_login(user)

    response = client.get(reverse("admin:notes_note_changelist"))

    assert response.status_code == HTTPStatus.OK
