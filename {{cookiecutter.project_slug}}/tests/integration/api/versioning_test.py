from http import HTTPStatus
from typing import TYPE_CHECKING

from django.urls import reverse

if TYPE_CHECKING:
    from django.test import Client
{%- if cookiecutter.use_example_api == "no" %}
    from ninja.testing import TestClient
{%- endif %}


def test_v1_api_exposes_openapi_schema_at_versioned_path(client: Client) -> None:
    response = client.get(reverse("v1:openapi-json"))

    assert response.status_code == HTTPStatus.OK
    assert response.json()["info"]["version"] == "1.0.0"
{%- if cookiecutter.use_example_api == "no" %}


def test_v1_api_serves_empty_openapi_schema_when_template_is_fresh(
    v1_api_client: TestClient,
) -> None:
    response = v1_api_client.get("/openapi.json")

    assert response.status_code == HTTPStatus.OK
    assert response.json()["paths"] == {}


def test_v1_api_serves_no_routes_when_template_is_fresh(client: Client) -> None:
    # No route exists at this path, so there is nothing for reverse() to resolve.
    response = client.get("/api/v1/does-not-exist")

    assert response.status_code == HTTPStatus.NOT_FOUND
{%- else %}


def test_v1_api_exposes_notes_paths_when_example_api_is_enabled(
    client: Client,
) -> None:
    response = client.get(reverse("v1:openapi-json"))

    assert response.status_code == HTTPStatus.OK
    paths = response.json()["paths"]
    assert any(path.startswith("/api/v1/notes") for path in paths)
{%- endif %}
