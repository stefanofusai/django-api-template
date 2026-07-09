{% if cookiecutter.use_example_api == "yes" and cookiecutter.api_auth == "jwt" -%}
from http import HTTPStatus
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from faker import Faker
    from ninja.testing import TestClient

    from apps.core.models import User

pytestmark = pytest.mark.django_db


@pytest.fixture
def valid_password(faker: Faker) -> str:
    return faker.password(length=16, special_chars=False)


def test_access_token_is_rejected_when_user_deactivated_after_issuance(
    user: User,
    valid_password: str,
    v1_api_client: TestClient,
) -> None:
    _set_password(user, valid_password)
    pair_response = v1_api_client.post(
        "/token/pair",
        json={"password": valid_password, "username": user.username},
    )

    user.is_active = False
    user.save(update_fields=("is_active",))

    response = v1_api_client.get(
        "/notes",
        headers={"Authorization": f"Bearer {pair_response.data['access']}"},
    )

    assert response.status_code == HTTPStatus.UNAUTHORIZED


def test_blacklisted_refresh_token_cannot_be_refreshed(
    user: User,
    valid_password: str,
    v1_api_client: TestClient,
) -> None:
    _set_password(user, valid_password)
    pair_response = v1_api_client.post(
        "/token/pair",
        json={"password": valid_password, "username": user.username},
    )
    refresh = pair_response.data["refresh"]

    blacklist_response = v1_api_client.post(
        "/token/blacklist", json={"refresh": refresh}
    )
    follow_up = v1_api_client.post("/token/refresh", json={"refresh": refresh})

    assert blacklist_response.status_code == HTTPStatus.OK
    assert follow_up.status_code == HTTPStatus.UNAUTHORIZED


def test_inactive_user_cannot_obtain_token_pair(
    user: User,
    valid_password: str,
    v1_api_client: TestClient,
) -> None:
    user.is_active = False
    user.set_password(valid_password)
    user.save(update_fields=("is_active", "password"))

    response = v1_api_client.post(
        "/token/pair",
        json={"password": valid_password, "username": user.username},
    )

    assert response.status_code == HTTPStatus.UNAUTHORIZED


def test_refresh_token_returns_new_access_token(
    user: User,
    valid_password: str,
    v1_api_client: TestClient,
) -> None:
    _set_password(user, valid_password)
    pair_response = v1_api_client.post(
        "/token/pair",
        json={"password": valid_password, "username": user.username},
    )

    response = v1_api_client.post(
        "/token/refresh", json={"refresh": pair_response.data["refresh"]}
    )

    assert response.status_code == HTTPStatus.OK
    assert response.data["access"] != pair_response.data["access"]


def test_token_pair_returns_access_and_refresh_tokens(
    user: User,
    valid_password: str,
    v1_api_client: TestClient,
) -> None:
    _set_password(user, valid_password)

    response = v1_api_client.post(
        "/token/pair",
        json={"password": valid_password, "username": user.username},
    )

    assert response.status_code == HTTPStatus.OK
    assert response.data["access"]
    assert response.data["refresh"]


def test_token_pair_access_token_authenticates_notes_request(
    user: User,
    valid_password: str,
    v1_api_client: TestClient,
) -> None:
    _set_password(user, valid_password)
    pair_response = v1_api_client.post(
        "/token/pair",
        json={"password": valid_password, "username": user.username},
    )

    response = v1_api_client.get(
        "/notes",
        headers={"Authorization": f"Bearer {pair_response.data['access']}"},
    )

    assert response.status_code == HTTPStatus.OK


# Utils


def _set_password(user: User, password: str) -> None:
    user.set_password(password)
    user.save(update_fields=("password",))
{%- endif %}
