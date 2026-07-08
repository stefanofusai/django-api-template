from collections.abc import Callable

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
        if _should_throttle_anonymous_request(request):
            throttle = _get_request_throttle(request)

            if throttle is not None and not throttle.allow_request(request):
                return JsonResponse(
                    {"detail": "Request was throttled."},
                    status=429,
                )

        return self.get_response(request)


def get_public_api_throttles() -> list[BaseThrottle]:
    return [DynamicPublicAPIThrottle()]


# Utils


def _should_throttle_anonymous_request(request: HttpRequest) -> bool:
    return all(
        (
            settings.API_THROTTLE_ANON_RATE is not None,
            not getattr(request.user, "is_authenticated", False),
            request.method != "OPTIONS",
            not request.headers.get("authorization"),
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
