from http import HTTPStatus
from typing import TYPE_CHECKING
from uuid import UUID

import structlog
from django.http import HttpResponse

from apps.api.signals import add_request_id_to_failure_response

if TYPE_CHECKING:
    from django.test import Client


def test_failure_response_includes_request_id_from_context() -> None:
    logger = structlog.get_logger()
    response = HttpResponse(status=HTTPStatus.INTERNAL_SERVER_ERROR)
    structlog.contextvars.bind_contextvars(request_id="failed-request")

    try:
        add_request_id_to_failure_response(object(), logger, response)

        assert response.headers["X-Request-ID"] == "failed-request"

    finally:
        structlog.contextvars.clear_contextvars()


def test_response_includes_generated_request_id(client: Client) -> None:
    response = client.get("/api/missing")

    assert response.status_code == HTTPStatus.NOT_FOUND
    UUID(response.headers["X-Request-ID"])


def test_response_preserves_supplied_request_id(client: Client) -> None:
    request_id = "request-from-upstream"

    response = client.get("/api/missing", headers={"X-Request-ID": request_id})

    assert response.status_code == HTTPStatus.NOT_FOUND
    assert response.headers["X-Request-ID"] == request_id
