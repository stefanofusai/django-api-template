from http import HTTPStatus
from typing import TYPE_CHECKING

import pytest
from django.test import Client, override_settings

{% if cookiecutter.api_auth == "token" -%}
from apps.core.models import Token

{% endif -%}
if TYPE_CHECKING:
    from apps.core.models import User

pytestmark = pytest.mark.django_db


@override_settings(API_THROTTLE_USER_RATE="2/min")
def test_authenticated_users_get_separate_counters(
    client: Client,
    user: User,
    user_1: User,
) -> None:
    client_1 = Client()
    headers = _auth_headers(client, user)
    headers_1 = _auth_headers(client_1, user_1)

    assert client.get("/api/v1/notes", headers=headers).status_code == HTTPStatus.OK
    assert client.get("/api/v1/notes", headers=headers).status_code == HTTPStatus.OK
    assert (
        client.get("/api/v1/notes", headers=headers).status_code
        == HTTPStatus.TOO_MANY_REQUESTS
    )
    assert client_1.get("/api/v1/notes", headers=headers_1).status_code == HTTPStatus.OK


@override_settings(API_THROTTLE_ANON_RATE="2/min")
def test_anonymous_ips_get_separate_counters(client: Client) -> None:
    headers = {"X-Forwarded-For": "198.51.100.10"}
    headers_1 = {"X-Forwarded-For": "198.51.100.11"}

    assert client.get("/api/v1/notes", headers=headers).status_code in {
        HTTPStatus.UNAUTHORIZED,
        HTTPStatus.FORBIDDEN,
    }
    assert client.get("/api/v1/notes", headers=headers).status_code in {
        HTTPStatus.UNAUTHORIZED,
        HTTPStatus.FORBIDDEN,
    }
    assert (
        client.get("/api/v1/notes", headers=headers).status_code
        == HTTPStatus.TOO_MANY_REQUESTS
    )
    assert client.get("/api/v1/notes", headers=headers_1).status_code in {
        HTTPStatus.UNAUTHORIZED,
        HTTPStatus.FORBIDDEN,
    }


{% if cookiecutter.api_auth == "token" -%}
@override_settings(API_THROTTLE_ANON_RATE="2/min")
def test_anonymous_requests_with_bogus_authorization_header_return_429_after_configured_limit(
    client: Client,
) -> None:
    headers = {"Authorization": "Bearer garbage"}

    assert (
        client.get("/api/v1/notes", headers=headers).status_code
        == HTTPStatus.UNAUTHORIZED
    )
    assert (
        client.get("/api/v1/notes", headers=headers).status_code
        == HTTPStatus.UNAUTHORIZED
    )
    assert (
        client.get("/api/v1/notes", headers=headers).status_code
        == HTTPStatus.TOO_MANY_REQUESTS
    )


{% endif -%}
@override_settings(API_THROTTLE_ANON_RATE="2/min")
def test_bogus_authorization_requests_share_the_anonymous_ip_budget(
    client: Client,
) -> None:
    assert client.get("/api/v1/notes").status_code in {
        HTTPStatus.UNAUTHORIZED,
        HTTPStatus.FORBIDDEN,
    }
    assert client.get("/api/v1/notes").status_code in {
        HTTPStatus.UNAUTHORIZED,
        HTTPStatus.FORBIDDEN,
    }
    assert (
        client.get(
            "/api/v1/notes",
            headers={"Authorization": "Bearer garbage"},
        ).status_code
        == HTTPStatus.TOO_MANY_REQUESTS
    )


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


{% if cookiecutter.api_auth == "token" -%}
@override_settings(API_THROTTLE_ANON_RATE="2/min", API_THROTTLE_USER_RATE=None)
def test_valid_token_requests_are_not_counted_against_the_anonymous_budget(
    client: Client,
    user: User,
) -> None:
    headers = _auth_headers(client, user)

    assert client.get("/api/v1/notes", headers=headers).status_code == HTTPStatus.OK
    assert client.get("/api/v1/notes", headers=headers).status_code == HTTPStatus.OK
    assert client.get("/api/v1/notes", headers=headers).status_code == HTTPStatus.OK


{% endif -%}
# Utils


{% if cookiecutter.api_auth == "token" -%}
def _auth_headers(_client: Client, user: User) -> dict[str, str]:
    raw_token, _ = Token.issue(name="test token", user=user)
    return {"Authorization": f"Bearer {raw_token}"}
{%- else -%}
def _auth_headers(client: Client, user: User) -> dict[str, str]:
    client.force_login(user)
    return {}
{%- endif %}
