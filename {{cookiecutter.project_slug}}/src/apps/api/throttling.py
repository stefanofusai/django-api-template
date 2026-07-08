"""
Public API throttling for the template's two-tier throttle design.

Every unauthenticated request to /api/v1/ is subject to the anonymous IP
budget: header-less requests are pre-checked and counted, while header-bearing
requests are pre-checked against the existing budget and counted when they
result in 401.
"""

from collections.abc import Callable
from http import HTTPStatus
from typing import cast

from django.conf import settings
from django.http import HttpRequest, HttpResponse, JsonResponse
from ninja_extra.throttling import AnonRateThrottle, BaseThrottle, UserRateThrottle


class DynamicPublicAPIThrottle(BaseThrottle):
    def allow_request(self, request: HttpRequest) -> bool:
        throttle = _get_request_throttle(request)

        if throttle is None:
            return True

        return throttle.allow_request(request)

    def wait(self) -> float | None:
        return None


class PublicAPIThrottleMiddleware:
    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        if not _should_throttle_public_api_anonymous_request(request):
            return self.get_response(request)

        throttle = cast("AnonRateThrottle", _get_request_throttle(request))

        if not _has_authorization_header(request):
            if not throttle.allow_request(request):
                return _throttled_response()

            return self.get_response(request)

        if _anon_budget_exhausted(
            throttle,
            request,
        ):
            return _throttled_response()

        response = self.get_response(request)

        if response.status_code == HTTPStatus.UNAUTHORIZED:
            throttle.allow_request(request)

        return response


def get_public_api_throttles() -> list[BaseThrottle]:
    return [DynamicPublicAPIThrottle()]


# Utils


def _anon_budget_exhausted(
    throttle: AnonRateThrottle,
    request: HttpRequest,
) -> bool:
    key = throttle.get_cache_key(request)

    if key is None:
        return False

    duration = cast("int", throttle.duration)
    now = throttle.timer()
    num_requests = cast("int", throttle.num_requests)
    history = [
        timestamp
        for timestamp in throttle.cache.get(key, [])
        if timestamp > now - duration
    ]
    return len(history) >= num_requests


def _has_authorization_header(request: HttpRequest) -> bool:
    return bool(request.headers.get("authorization"))


def _should_throttle_public_api_anonymous_request(request: HttpRequest) -> bool:
    return all(
        (
            settings.API_THROTTLE_ANON_RATE is not None,
            not getattr(request.user, "is_authenticated", False),
            request.method != "OPTIONS",
            request.path_info.startswith("/api/v1/"),
        )
    )


def _get_request_throttle(request: HttpRequest) -> BaseThrottle | None:
    if getattr(request.user, "is_authenticated", False):
        if settings.API_THROTTLE_USER_RATE is None:
            return None

        return UserRateThrottle(rate=settings.API_THROTTLE_USER_RATE)

    if settings.API_THROTTLE_ANON_RATE is None:
        return None

    return AnonRateThrottle(rate=settings.API_THROTTLE_ANON_RATE)


def _throttled_response() -> JsonResponse:
    return JsonResponse(
        {"detail": "Request was throttled."},
        status=HTTPStatus.TOO_MANY_REQUESTS,
    )
