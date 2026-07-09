from http import HTTPStatus
from typing import TYPE_CHECKING

import pytest
from django.urls import reverse

{% if cookiecutter.use_example_api == "yes" and cookiecutter.api_auth == "token" -%}
from apps.core.models import Token

{% endif -%}
if TYPE_CHECKING:
    from django.test import Client

    from apps.core.models import User

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


@pytest.mark.parametrize("user__is_staff", [True])
@pytest.mark.parametrize("user__is_superuser", [True])
def test_token_add_mints_token_and_shows_it_once(
    client: Client,
    user: User,
) -> None:
    client.force_login(user)

    add_response = client.get(reverse("admin:core_token_add"))

    assert add_response.status_code == HTTPStatus.OK

    response = client.post(
        reverse("admin:core_token_add"),
        {"name": "ci token", "user": user.pk, "expires_at": ""},
        follow=True,
    )

    assert response.status_code == HTTPStatus.OK
    assert Token.objects.filter(name="ci token", user=user).exists()
    assert b"it will not be shown again" in response.content


@pytest.mark.parametrize("user__is_staff", [True])
@pytest.mark.parametrize("user__is_superuser", [True])
def test_token_change_updates_name(
    client: Client,
    token: Token,
    user: User,
) -> None:
    client.force_login(user)

    response = client.post(
        reverse("admin:core_token_change", args=[token.pk]),
        {
            "name": "renamed token",
            "user": token.user.pk,
            "expires_at": "",
        },
        follow=True,
    )

    assert response.status_code == HTTPStatus.OK
    token.refresh_from_db()
    assert token.name == "renamed token"
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
