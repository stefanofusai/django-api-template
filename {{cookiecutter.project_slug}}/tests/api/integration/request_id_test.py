from http import HTTPStatus
from typing import TYPE_CHECKING
from uuid import UUID

import structlog
from django.http import HttpResponse
from django_structlog import signals

from apps.api.signals import REQUEST_ID_MAX_LENGTH

if TYPE_CHECKING:
    from django.test import Client
    from faker import Faker


def test_failure_response_includes_request_id_when_signal_context_has_request_id(
    faker: Faker,
) -> None:
    logger = structlog.get_logger()
    request_id = faker.uuid4()
    response = HttpResponse(status=HTTPStatus.INTERNAL_SERVER_ERROR)
    structlog.contextvars.bind_contextvars(request_id=request_id)

    try:
        signals.update_failure_response.send(
            sender=object,
            logger=logger,
            response=response,
        )

        assert response.headers["X-Request-ID"] == request_id

    finally:
        structlog.contextvars.clear_contextvars()


def test_request_id_is_regenerated_when_client_sends_malformed_value(
    client: Client,
) -> None:
    response = client.get("/api/missing", headers={"X-Request-ID": "not-a-request-id"})

    assert response.status_code == HTTPStatus.NOT_FOUND
    request_id = response.headers["X-Request-ID"]
    UUID(request_id)
    assert request_id != "not-a-request-id"


def test_request_id_response_is_bounded_when_client_sends_overlong_value(
    client: Client,
) -> None:
    request_id = "a" * (REQUEST_ID_MAX_LENGTH + 1)

    response = client.get("/api/missing", headers={"X-Request-ID": request_id})

    assert response.status_code == HTTPStatus.NOT_FOUND
    response_request_id = response.headers["X-Request-ID"]
    UUID(response_request_id)
    assert response_request_id != request_id
    assert len(response_request_id) <= REQUEST_ID_MAX_LENGTH


def test_response_includes_generated_request_id_when_client_sends_no_request_id(
    client: Client,
) -> None:
    response = client.get("/api/missing")

    assert response.status_code == HTTPStatus.NOT_FOUND
    UUID(response.headers["X-Request-ID"])


def test_response_preserves_supplied_request_id_when_client_sends_valid_value(
    client: Client, faker: Faker
) -> None:
    request_id = faker.uuid4()

    response = client.get("/api/missing", headers={"X-Request-ID": request_id})

    assert response.status_code == HTTPStatus.NOT_FOUND
    assert response.headers["X-Request-ID"] == request_id
