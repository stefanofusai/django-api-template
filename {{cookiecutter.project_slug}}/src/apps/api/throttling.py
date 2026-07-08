from collections.abc import Callable

from django.conf import settings
from django.http import HttpRequest
from django.http import HttpResponse
from django.http import JsonResponse
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

            if not throttle.allow_request(request):
                return JsonResponse(
                    {"detail": "Request was throttled."},
                    status=429,
                )

        return self.get_response(request)


def get_public_api_throttles() -> tuple[BaseThrottle, ...]:
    return (DynamicPublicAPIThrottle(),)


# Utils


def _should_throttle_anonymous_request(request: HttpRequest) -> bool:
    if settings.API_THROTTLE_ANON_RATE is None:
        return False

    if getattr(request.user, "is_authenticated", False):
        return False

    if request.method == "OPTIONS":
        return False

    if request.META.get("HTTP_AUTHORIZATION"):
        return False

    return request.path_info.startswith("/api/v1/")


def _get_request_throttle(request: HttpRequest) -> BaseThrottle | None:
    if getattr(request.user, "is_authenticated", False):
        if settings.API_THROTTLE_USER_RATE is None:
            return None

        return UserRateThrottle(rate=settings.API_THROTTLE_USER_RATE)

    if settings.API_THROTTLE_ANON_RATE is None:
        return None

    return AnonRateThrottle(rate=settings.API_THROTTLE_ANON_RATE)
