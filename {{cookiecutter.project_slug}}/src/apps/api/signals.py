import structlog
from django.dispatch import receiver
from django.http import HttpResponseBase  # noqa: TC002
from django_structlog import signals


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
    request_id = structlog.contextvars.get_merged_contextvars(logger)["request_id"]
    response.headers["X-Request-ID"] = request_id
