from http import HTTPStatus
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from django.test import Client
    from ninja.testing import TestClient


def test_v1_api_exposes_openapi_schema_at_versioned_path(client: Client) -> None:
    response = client.get("/api/v1/openapi.json")

    assert response.status_code == HTTPStatus.OK
    assert response.json()["info"]["version"] == "1.0.0"


def test_v1_api_serves_empty_openapi_schema_when_template_is_fresh(
    v1_client: TestClient,
) -> None:
    response = v1_client.get("/openapi.json")

    assert response.status_code == HTTPStatus.OK
    assert response.json()["paths"] == {}


def test_v1_api_serves_no_operations_when_template_is_fresh(client: Client) -> None:
    response = client.get("/api/v1/does-not-exist")

    assert response.status_code == HTTPStatus.NOT_FOUND
