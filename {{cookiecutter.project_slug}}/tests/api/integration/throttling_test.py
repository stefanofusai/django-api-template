from http import HTTPStatus
from typing import TYPE_CHECKING

import pytest
from django.core.cache import cache
from django.test import Client, override_settings

{% if cookiecutter.api_auth == "token" -%}
from apps.core.models import Token
{% endif %}
if TYPE_CHECKING:
    from apps.core.models import User
    from tests.factories import UserFactory

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def clear_cache() -> None:
    cache.clear()


@override_settings(API_THROTTLE_USER_RATE="2/min")
def test_authenticated_users_get_separate_counters(
    client: Client,
    user: User,
    user_factory: type[UserFactory],
) -> None:
    first_headers = _auth_headers(client, user)
    second_headers = _auth_headers(client, user_factory.create())

    assert (
        client.get("/api/v1/notes", headers=first_headers).status_code == HTTPStatus.OK
    )
    assert (
        client.get("/api/v1/notes", headers=first_headers).status_code == HTTPStatus.OK
    )
    assert (
        client.get("/api/v1/notes", headers=first_headers).status_code
        == HTTPStatus.TOO_MANY_REQUESTS
    )
    assert (
        client.get("/api/v1/notes", headers=second_headers).status_code == HTTPStatus.OK
    )


@override_settings(API_THROTTLE_ANON_RATE="2/min")
def test_anonymous_ips_get_separate_counters(client: Client) -> None:
    first_headers = {"X-Forwarded-For": "198.51.100.10"}
    second_headers = {"X-Forwarded-For": "198.51.100.11"}

    assert client.get("/api/v1/notes", headers=first_headers).status_code in {
        HTTPStatus.UNAUTHORIZED,
        HTTPStatus.FORBIDDEN,
    }
    assert client.get("/api/v1/notes", headers=first_headers).status_code in {
        HTTPStatus.UNAUTHORIZED,
        HTTPStatus.FORBIDDEN,
    }
    assert (
        client.get("/api/v1/notes", headers=first_headers).status_code
        == HTTPStatus.TOO_MANY_REQUESTS
    )
    assert client.get("/api/v1/notes", headers=second_headers).status_code in {
        HTTPStatus.UNAUTHORIZED,
        HTTPStatus.FORBIDDEN,
    }


@override_settings(API_THROTTLE_USER_RATE="2/min")
def test_public_api_requests_return_429_after_configured_limit(
    client: Client,
    user: User,
) -> None:
    headers = _auth_headers(client, user)
    assert client.get("/api/v1/notes", headers=headers).status_code == HTTPStatus.OK
    assert client.get("/api/v1/notes", headers=headers).status_code == HTTPStatus.OK

    response = client.get("/api/v1/notes", headers=headers)

    assert response.status_code == HTTPStatus.TOO_MANY_REQUESTS


@override_settings(API_THROTTLE_ANON_RATE="2/min")
def test_internal_probes_are_not_throttled(client: Client) -> None:
    for _ in range(3):
        assert client.get("/api/health").status_code == HTTPStatus.OK
        assert client.get("/api/ready").status_code == HTTPStatus.OK


@override_settings(API_THROTTLE_ANON_RATE=None, API_THROTTLE_USER_RATE=None)
def test_public_api_requests_are_not_throttled_when_rates_are_unset(
    client: Client,
) -> None:
    headers = {"X-Forwarded-For": "198.51.100.10"}

    for _ in range(3):
        assert client.get("/api/v1/notes", headers=headers).status_code in {
            HTTPStatus.UNAUTHORIZED,
            HTTPStatus.FORBIDDEN,
        }


# Utils


def _auth_headers(client: Client, user: User) -> dict[str, str]:
    {% if cookiecutter.api_auth == "token" -%}
    _ = client
    raw_token, _ = Token.issue(name="test token", user=user)
    return {"Authorization": f"Bearer {raw_token}"}
    {%- else %}
    client.force_login(user)
    return {}
    {%- endif %}
