from uuid import UUID, uuid4

import structlog
from django.dispatch import receiver
from django.http import HttpResponseBase  # noqa: TC002
from django_structlog import signals

REQUEST_ID_MAX_LENGTH = 200


@receiver(signals.update_failure_response)
def add_request_id_to_failure_response(
    sender: object,  # noqa: ARG001
    logger: structlog.stdlib.BoundLogger,
    response: HttpResponseBase,
    **kwargs: object,  # noqa: ARG001
) -> None:
    _add_request_id(logger, response)


@receiver(signals.bind_extra_request_finished_metadata)
def add_request_id_to_response(
    sender: object,  # noqa: ARG001
    logger: structlog.stdlib.BoundLogger,
    response: HttpResponseBase,
    **kwargs: object,  # noqa: ARG001
) -> None:
    _add_request_id(logger, response)


# Utils


def _add_request_id(
    logger: structlog.stdlib.BoundLogger, response: HttpResponseBase
) -> None:
    request_id = _normalize_request_id(
        structlog.contextvars.get_merged_contextvars(logger)["request_id"]
    )
    structlog.contextvars.bind_contextvars(request_id=request_id)
    response.headers["X-Request-ID"] = request_id


def _normalize_request_id(value: object) -> str:
    request_id = str(value)

    if len(request_id) > REQUEST_ID_MAX_LENGTH:
        return str(uuid4())

    try:
        UUID(request_id)
    
    except ValueError:
        return str(uuid4())

    return request_id
