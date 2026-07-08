from django.core.cache import cache
from django.db import DatabaseError, connections
from django.http import HttpRequest
from django_redis.exceptions import ConnectionInterrupted
{% if cookiecutter.use_celery != "none" -%}
from kombu.exceptions import OperationalError
{% endif -%}
from ninja import Router, Status
from redis.exceptions import RedisError

from apps.api.schemas import ReadyError, ReadyErrorSchema, ReadyOkSchema
{% if cookiecutter.use_celery != "none" -%}
from config.celery import app
{% endif %}
router = Router(tags=["ready"])


@router.get("/ready", response={200: ReadyOkSchema, 503: ReadyErrorSchema})
def ready(
    request: HttpRequest,  # noqa: ARG001
) -> Status[ReadyOkSchema] | Status[ReadyErrorSchema]:
    errors: list[ReadyError] = []

    if not _cache_ready():
        errors.append("cache")

    if not _database_ready():
        errors.append("database")

    {% if cookiecutter.use_celery != "none" -%}
    if not _broker_ready():
        errors.append("broker")

    {% endif -%}
    if errors:
        return Status(503, ReadyErrorSchema(status="error", errors=errors))

    return Status(200, ReadyOkSchema(status="ok"))


# Utils


{% if cookiecutter.use_celery != "none" -%}
def _broker_ready() -> bool:
    try:
        # max_retries=0 and a 1s timeout keep the probe bounded: /ready is
        # polled every few seconds and must never hang on a dead broker.
        # kombu wraps every underlying connection failure (DNS, socket,
        # transport-specific errors) into a single OperationalError as long
        # as reraise_as_library_errors stays at its default of True.
        with app.connection_for_read() as connection:
            connection.ensure_connection(max_retries=0, timeout=1)

    except OperationalError:
        return False

    return True


{% endif -%}
def _cache_ready() -> bool:
    cache_key = "ready-check"
    cache_value = "ok"

    try:
        # cache.set returns None on backends that do not report an outcome;
        # only an explicit False means the backend rejected the write. The get
        # round-trip below verifies the None case.
        if cache.set(cache_key, cache_value, timeout=1) is False:
            return False

        return cache.get(cache_key) == cache_value

    # Parenthesis-free except tuples are PEP 758 syntax (Python 3.14+).
    except ConnectionInterrupted, OSError, RedisError:
        return False


def _database_ready() -> bool:
    try:
        connections["default"].ensure_connection()

    except DatabaseError:
        return False

    return True
