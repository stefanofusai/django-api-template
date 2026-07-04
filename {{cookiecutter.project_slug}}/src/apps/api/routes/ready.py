from django.core.cache import cache
from django.db import DatabaseError, connections
from django.http import HttpRequest
from django_redis.exceptions import ConnectionInterrupted
from ninja import Router, Status
from redis.exceptions import RedisError

from apps.api.schemas import ReadyError, ReadyErrorSchema, ReadyOkSchema

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

    if errors:
        return Status(503, ReadyErrorSchema(status="error", errors=errors))

    return Status(200, ReadyOkSchema(status="ok"))


# Utils


def _cache_ready() -> bool:
    cache_key = "ready-check"
    cache_value = "ok"

    try:
        if cache.set(cache_key, cache_value, timeout=1) is False:
            return False

        return cache.get(cache_key) == cache_value

    except ConnectionInterrupted, OSError, RedisError:
        return False


def _database_ready() -> bool:
    try:
        connections["default"].ensure_connection()

    except DatabaseError:
        return False

    return True
