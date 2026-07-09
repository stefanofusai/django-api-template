from http import HTTPStatus
from typing import TYPE_CHECKING

import pytest
from django.urls import reverse

if TYPE_CHECKING:
    from django.test import Client

    from apps.core.models import User

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize("user__is_staff", [True])
@pytest.mark.parametrize("user__is_superuser", [True])
def test_user_changelist_returns_200_when_staff(
    client: Client,
    user: User,
) -> None:
    client.force_login(user)

    response = client.get(reverse("admin:core_user_changelist"))

    assert response.status_code == HTTPStatus.OK
