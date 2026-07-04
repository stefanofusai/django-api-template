from http import HTTPStatus
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ninja.testing import TestClient


def test_health_endpoint_returns_ok_without_touching_dependencies(
    api_client: TestClient,
) -> None:
    response = api_client.get("/health")

    assert response.status_code == HTTPStatus.OK
    assert response.data == {"status": "ok"}
