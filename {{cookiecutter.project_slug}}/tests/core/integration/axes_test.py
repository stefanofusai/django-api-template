from http import HTTPStatus
from typing import TYPE_CHECKING

import pytest
from django.test import override_settings

from tests.factories import UserFactory

if TYPE_CHECKING:
    from django.test import Client
    from faker import Faker

    from apps.core.models import User

pytestmark = pytest.mark.django_db


@override_settings(AXES_FAILURE_LIMIT=3)
def test_admin_login_locks_out_after_configured_failures(
    client: Client, faker: Faker
) -> None:
    username = faker.user_name()
    password = faker.password(length=16)
    remote_addr = faker.ipv4()
    # Deterministically distinct from `password` rather than drawn from the
    # same random distribution, so this never needs a collision retry.
    wrong_password = f"wrong-{password}"

    user = UserFactory.create(is_staff=True, username=username)
    _set_password(user, password)

    assert (
        _post_admin_login(client, username, wrong_password, remote_addr)[0]
        == HTTPStatus.OK
    )
    assert (
        _post_admin_login(client, username, wrong_password, remote_addr)[0]
        == HTTPStatus.OK
    )
    assert (
        _post_admin_login(client, username, wrong_password, remote_addr)[0]
        == HTTPStatus.TOO_MANY_REQUESTS
    )
    assert (
        _post_admin_login(client, username, wrong_password, remote_addr)[0]
        == HTTPStatus.TOO_MANY_REQUESTS
    )
    assert (
        _post_admin_login(client, username, password, remote_addr)[0]
        == HTTPStatus.TOO_MANY_REQUESTS
    )


@override_settings(AXES_FAILURE_LIMIT=3)
def test_login_succeeds_before_lockout_threshold(client: Client, faker: Faker) -> None:
    username = faker.user_name()
    password = faker.password(length=16)
    remote_addr = faker.ipv4()
    # Deterministically distinct from `password` rather than drawn from the
    # same random distribution, so this never needs a collision retry.
    wrong_password = f"wrong-{password}"

    user = UserFactory.create(is_staff=True, username=username)
    _set_password(user, password)

    assert (
        _post_admin_login(client, username, wrong_password, remote_addr)[0]
        == HTTPStatus.OK
    )

    status_code, location = _post_admin_login(client, username, password, remote_addr)

    assert status_code == HTTPStatus.FOUND
    assert location == "/admin/"


# Utils


def _post_admin_login(
    client: Client, username: str, password: str, remote_addr: str
) -> tuple[int, str | None]:
    response = client.post(
        "/admin/login/",
        {
            "next": "/admin/",
            "password": password,
            "username": username,
        },
        REMOTE_ADDR=remote_addr,
    )
    return response.status_code, response.get("Location")


def _set_password(user: User, password: str) -> None:
    user.set_password(password)
    user.save(update_fields=("password",))
