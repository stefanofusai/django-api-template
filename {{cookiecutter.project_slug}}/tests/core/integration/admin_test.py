from http import HTTPStatus
from typing import TYPE_CHECKING

import pytest
from django.urls import reverse

if TYPE_CHECKING:
    from django.test import Client

    from apps.core.models import {% if cookiecutter.use_example_api == "yes" and cookiecutter.api_auth == "token" %}Token, User{% else %}User{% endif %}

pytestmark = pytest.mark.django_db
{%- if cookiecutter.use_example_api == "yes" and cookiecutter.api_auth == "token" %}


@pytest.mark.parametrize("user__is_staff", [True])
@pytest.mark.parametrize("user__is_superuser", [True])
def test_token_changelist_returns_200_when_staff(
    client: Client,
    token: Token,
    user: User,
) -> None:
    assert token.pk is not None
    client.force_login(user)

    response = client.get(reverse("admin:core_token_changelist"))

    assert response.status_code == HTTPStatus.OK
{%- endif %}


@pytest.mark.parametrize("user__is_staff", [True])
@pytest.mark.parametrize("user__is_superuser", [True])
def test_user_changelist_returns_200_when_staff(
    client: Client,
    user: User,
) -> None:
    client.force_login(user)

    response = client.get(reverse("admin:core_user_changelist"))

    assert response.status_code == HTTPStatus.OK
