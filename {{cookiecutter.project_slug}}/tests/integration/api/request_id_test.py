from http import HTTPStatus
from typing import TYPE_CHECKING
from uuid import UUID

import structlog
from django.http import HttpResponse

from apps.api.signals import add_request_id_to_failure_response

if TYPE_CHECKING:
    from django.test import Client
    from faker import Faker


def test_failure_response_includes_request_id_from_context(faker: Faker) -> None:
    logger = structlog.get_logger()
    request_id = faker.uuid4()
    response = HttpResponse(status=HTTPStatus.INTERNAL_SERVER_ERROR)
    structlog.contextvars.bind_contextvars(request_id=request_id)

    try:
        add_request_id_to_failure_response(object(), logger, response)

        assert response.headers["X-Request-ID"] == request_id

    finally:
        structlog.contextvars.clear_contextvars()


def test_response_includes_generated_request_id(client: Client) -> None:
    response = client.get("/api/missing")

    assert response.status_code == HTTPStatus.NOT_FOUND
    UUID(response.headers["X-Request-ID"])


def test_response_preserves_supplied_request_id(client: Client, faker: Faker) -> None:
    request_id = faker.uuid4()

    response = client.get("/api/missing", headers={"X-Request-ID": request_id})

    assert response.status_code == HTTPStatus.NOT_FOUND
    assert response.headers["X-Request-ID"] == request_id
