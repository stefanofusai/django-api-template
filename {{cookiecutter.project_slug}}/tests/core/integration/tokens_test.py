from datetime import UTC, datetime
from http import HTTPStatus
from typing import TYPE_CHECKING

import pytest

from apps.core.models import Token

if TYPE_CHECKING:
    from ninja.testing import TestClient

    from tests.utils import AuthenticatedTestClient

pytestmark = pytest.mark.django_db


def test_create_token_accepts_explicit_null_expires_at(
    authenticated_v1_api_client: AuthenticatedTestClient,
) -> None:
    response = authenticated_v1_api_client.post(
        "/tokens", json={"name": "ci token", "expires_at": None}
    )

    assert response.status_code == HTTPStatus.CREATED
    token = Token.objects.get(id=response.data["id"])
    assert token.expires_at is None


def test_create_token_normalizes_expires_at_to_utc_when_offset_given(
    authenticated_v1_api_client: AuthenticatedTestClient,
) -> None:
    response = authenticated_v1_api_client.post(
        "/tokens",
        json={"name": "ci token", "expires_at": "2027-01-01T00:00:00+05:00"},
    )

    assert response.status_code == HTTPStatus.CREATED
    token = Token.objects.get(id=response.data["id"])
    assert token.expires_at == datetime(2026, 12, 31, 19, 0, tzinfo=UTC)


def test_create_token_returns_201_and_raw_token_when_authenticated(
    authenticated_v1_api_client: AuthenticatedTestClient,
    v1_api_client: TestClient,
) -> None:
    response = authenticated_v1_api_client.post("/tokens", json={"name": "ci token"})

    assert response.status_code == HTTPStatus.CREATED
    payload = response.data
    assert payload["name"] == "ci token"
    assert payload["token"].startswith("pat_")
    assert "digest" not in payload
    token = Token.objects.get(id=payload["id"])
    assert token.user == authenticated_v1_api_client.user

    follow_up = v1_api_client.post(
        "/tokens",
        json={"name": "second token"},
        headers={"Authorization": f"Bearer {payload['token']}"},
    )
    assert follow_up.status_code == HTTPStatus.CREATED
    assert "digest" not in follow_up.data


def test_create_token_returns_401_when_anonymous(v1_api_client: TestClient) -> None:
    response = v1_api_client.post("/tokens", json={"name": "ci token"})

    assert response.status_code == HTTPStatus.UNAUTHORIZED


def test_create_token_returns_422_when_expires_at_overflows_utc_normalization(
    authenticated_v1_api_client: AuthenticatedTestClient,
) -> None:
    response = authenticated_v1_api_client.post(
        "/tokens",
        json={"name": "ci token", "expires_at": "9999-12-31T23:59:59-23:00"},
    )

    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    assert not Token.objects.filter(name="ci token").exists()


def test_create_token_returns_422_when_name_exceeds_max_length(
    authenticated_v1_api_client: AuthenticatedTestClient,
) -> None:
    name = "x" * 101

    response = authenticated_v1_api_client.post("/tokens", json={"name": name})

    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    assert not Token.objects.filter(name=name).exists()


def test_create_token_returns_422_when_name_is_empty(
    authenticated_v1_api_client: AuthenticatedTestClient,
) -> None:
    response = authenticated_v1_api_client.post("/tokens", json={"name": ""})

    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    assert not Token.objects.filter(name="").exists()


def test_list_tokens_includes_revoked_tokens_when_authenticated(
    authenticated_v1_api_client: AuthenticatedTestClient,
    revoked_token: Token,
) -> None:
    response = authenticated_v1_api_client.get("/tokens")

    assert response.status_code == HTTPStatus.OK
    payload = response.data
    item = next(item for item in payload["items"] if item["id"] == revoked_token.pk)
    assert item["revoked_at"] is not None


def test_list_tokens_returns_401_when_anonymous(v1_api_client: TestClient) -> None:
    response = v1_api_client.get("/tokens")

    assert response.status_code == HTTPStatus.UNAUTHORIZED


def test_list_tokens_returns_only_callers_tokens_when_authenticated(
    authenticated_v1_api_client: AuthenticatedTestClient,
    token: Token,
    token_1: Token,
) -> None:
    response = authenticated_v1_api_client.get("/tokens")

    assert response.status_code == HTTPStatus.OK
    payload = response.data
    item_ids = [item["id"] for item in payload["items"]]
    assert token.pk in item_ids
    assert token_1.pk not in item_ids
    for item in payload["items"]:
        assert "digest" not in item


def test_revoke_token_returns_204_and_refuses_reuse(
    authenticated_v1_api_client: AuthenticatedTestClient,
    raw_token: str,
    token: Token,
    v1_api_client: TestClient,
) -> None:
    response = authenticated_v1_api_client.delete(f"/tokens/{token.pk}")

    assert response.status_code == HTTPStatus.NO_CONTENT
    token.refresh_from_db()
    assert token.revoked_at is not None

    follow_up = v1_api_client.get(
        "/tokens", headers={"Authorization": f"Bearer {raw_token}"}
    )
    assert follow_up.status_code == HTTPStatus.UNAUTHORIZED


def test_revoke_token_returns_401_when_anonymous(v1_api_client: TestClient) -> None:
    response = v1_api_client.delete("/tokens/1")

    assert response.status_code == HTTPStatus.UNAUTHORIZED


def test_revoke_token_returns_404_when_already_revoked(
    authenticated_v1_api_client: AuthenticatedTestClient,
    revoked_token: Token,
) -> None:
    response = authenticated_v1_api_client.delete(f"/tokens/{revoked_token.pk}")

    assert response.status_code == HTTPStatus.NOT_FOUND


def test_revoke_token_returns_404_when_owned_by_other_user(
    authenticated_v1_api_client: AuthenticatedTestClient,
    token_1: Token,
) -> None:
    response = authenticated_v1_api_client.delete(f"/tokens/{token_1.pk}")

    assert response.status_code == HTTPStatus.NOT_FOUND
    token_1.refresh_from_db()
    assert token_1.revoked_at is None


def test_revoke_token_returns_404_when_token_does_not_exist(
    authenticated_v1_api_client: AuthenticatedTestClient,
) -> None:
    response = authenticated_v1_api_client.delete("/tokens/999999999")

    assert response.status_code == HTTPStatus.NOT_FOUND
