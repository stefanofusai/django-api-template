from http import HTTPStatus
from typing import TYPE_CHECKING

from django.urls import reverse

if TYPE_CHECKING:
    from django.test import Client


def test_api_docs_are_public_when_docs_decorator_is_identity(
    client: Client,
) -> None:
    response = client.get(reverse("internal:openapi-view"))

    assert response.status_code == HTTPStatus.OK


def test_openapi_schema_is_public_when_docs_decorator_is_identity(
    client: Client,
) -> None:
    response = client.get(reverse("internal:openapi-json"))

    assert response.status_code == HTTPStatus.OK
