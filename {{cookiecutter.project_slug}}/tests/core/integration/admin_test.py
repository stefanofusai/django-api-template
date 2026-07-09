from http import HTTPStatus
from typing import TYPE_CHECKING

import pytest
from django.urls import reverse

from apps.core.models import User

if TYPE_CHECKING:
    from django.test import Client
    from faker import Faker

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize("user__is_staff", [True])
@pytest.mark.parametrize("user__is_superuser", [True])
def test_user_add_form_creates_second_user_when_emails_differ(
    authenticated_client: Client,
    faker: Faker,
) -> None:
    password = faker.password(length=16, special_chars=False)

    for username, email in (
        (faker.user_name(), faker.email()),
        (faker.user_name(), faker.email()),
    ):
        response = authenticated_client.post(
            reverse("admin:core_user_add"),
            {
                "email": email,
                "password1": password,
                "password2": password,
                "usable_password": "true",
                "username": username,
            },
        )

        assert response.status_code == HTTPStatus.FOUND
        assert User.objects.filter(username=username, email=email).exists()


@pytest.mark.parametrize("user__is_staff", [True])
@pytest.mark.parametrize("user__is_superuser", [True])
def test_user_add_form_requires_email_when_omitted(
    authenticated_client: Client,
    faker: Faker,
) -> None:
    password = faker.password(length=16, special_chars=False)
    username = faker.user_name()

    response = authenticated_client.post(
        reverse("admin:core_user_add"),
        {
            "password1": password,
            "password2": password,
            "usable_password": "true",
            "username": username,
        },
    )

    assert response.status_code == HTTPStatus.OK
    assert not User.objects.filter(username=username).exists()


@pytest.mark.parametrize("user__is_staff", [True])
@pytest.mark.parametrize("user__is_superuser", [True])
def test_user_changelist_returns_200_when_staff(
    authenticated_client: Client,
) -> None:
    response = authenticated_client.get(reverse("admin:core_user_changelist"))

    assert response.status_code == HTTPStatus.OK
