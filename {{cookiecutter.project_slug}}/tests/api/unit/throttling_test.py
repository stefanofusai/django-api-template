import json
import os
import subprocess
import sys
from http import HTTPStatus

from django.conf import settings
from django.contrib.auth.models import AnonymousUser, User
from django.http import HttpResponse
from django.test import RequestFactory, override_settings
from ninja_extra.throttling import AnonRateThrottle, BaseThrottle, UserRateThrottle

from apps.api.throttling import (
    DynamicPublicAPIThrottle,
    PublicAPIThrottleMiddleware,
    _anon_budget_exhausted,
    _get_request_throttle,
    get_public_api_throttles,
)


@override_settings(API_THROTTLE_ANON_RATE="2/min", API_THROTTLE_USER_RATE=None)
def test_anon_budget_exhausted_returns_false_when_request_has_no_cache_key() -> None:
    request = RequestFactory().get("/api/v1/notes")
    request.user = User(username="test-user")

    assert not _anon_budget_exhausted(AnonRateThrottle(rate="2/min"), request)


@override_settings(API_THROTTLE_ANON_RATE="2/min", API_THROTTLE_USER_RATE=None)
def test_get_public_api_throttles_returns_anon_throttle_when_anon_rate_is_set() -> None:
    throttles = get_public_api_throttles()

    assert len(throttles) == 1
    assert isinstance(throttles[0], BaseThrottle)


@override_settings(API_THROTTLE_ANON_RATE=None, API_THROTTLE_USER_RATE=None)
def test_public_api_throttle_allows_requests_when_rates_are_unset() -> None:
    request = RequestFactory().get("/api/v1/notes")
    request.user = AnonymousUser()

    assert get_public_api_throttles()[0].allow_request(request)


@override_settings(API_THROTTLE_ANON_RATE="2/min", API_THROTTLE_USER_RATE=None)
def test_dynamic_public_api_throttle_allow_request_delegates_when_throttle_is_configured() -> (
    None
):
    request = RequestFactory().get("/api/v1/notes")
    request.user = AnonymousUser()

    assert DynamicPublicAPIThrottle().allow_request(request)


def test_dynamic_public_api_throttle_wait_returns_none() -> None:
    assert DynamicPublicAPIThrottle().wait() is None


@override_settings(API_THROTTLE_ANON_RATE=None, API_THROTTLE_USER_RATE=None)
def test_get_request_throttle_returns_none_when_authenticated_user_rate_is_unset() -> (
    None
):
    request = RequestFactory().get("/api/v1/notes")
    request.user = User(username="test-user")

    assert _get_request_throttle(request) is None


@override_settings(API_THROTTLE_ANON_RATE=None, API_THROTTLE_USER_RATE="3/min")
def test_get_request_throttle_returns_user_throttle_when_authenticated_user_rate_is_set() -> (
    None
):
    request = RequestFactory().get("/api/v1/notes")
    request.user = User(username="test-user")

    assert isinstance(_get_request_throttle(request), UserRateThrottle)


def test_ninja_extra_throttle_rates_default_to_empty_when_env_is_unset() -> None:
    assert settings.NINJA_EXTRA["THROTTLE_RATES"] == {}


def test_ninja_extra_throttle_rates_are_populated_when_env_is_set() -> None:
    env = os.environ | {
        "API_THROTTLE_ANON_RATE": "60/minute",
        "API_THROTTLE_USER_RATE": "600/minute",
        "PYTHONPATH": "src",
    }
    script = (
        "import json; import config.settings as s; "
        "print(json.dumps(s.NINJA_EXTRA['THROTTLE_RATES']))"
    )
    result = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True,
        check=False,
        env=env,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == {"anon": "60/minute", "user": "600/minute"}


@override_settings(API_THROTTLE_ANON_RATE="1/min", API_THROTTLE_USER_RATE=None)
def test_public_api_middleware_counts_unauthorized_authorization_requests() -> None:
    request = RequestFactory().get(
        "/api/v1/notes",
        HTTP_AUTHORIZATION="Bearer garbage",
    )
    request.user = AnonymousUser()
    middleware = PublicAPIThrottleMiddleware(
        lambda _request: HttpResponse(status=HTTPStatus.UNAUTHORIZED),
    )

    assert middleware(request).status_code == HTTPStatus.UNAUTHORIZED
    assert middleware(request).status_code == HTTPStatus.TOO_MANY_REQUESTS


@override_settings(API_THROTTLE_ANON_RATE="1/min", API_THROTTLE_USER_RATE=None)
def test_public_api_middleware_does_not_count_non_401_authorization_requests() -> None:
    request = RequestFactory().get(
        "/api/v1/notes",
        HTTP_AUTHORIZATION="Bearer valid",
    )
    request.user = AnonymousUser()
    middleware = PublicAPIThrottleMiddleware(
        lambda _request: HttpResponse(status=HTTPStatus.OK),
    )

    assert middleware(request).status_code == HTTPStatus.OK
    assert middleware(request).status_code == HTTPStatus.OK


@override_settings(API_THROTTLE_ANON_RATE="1/min", API_THROTTLE_USER_RATE=None)
def test_public_api_middleware_allows_header_less_request_when_throttle_permits() -> (
    None
):
    request = RequestFactory().get("/api/v1/notes")
    request.user = AnonymousUser()
    middleware = PublicAPIThrottleMiddleware(
        lambda _request: HttpResponse(status=HTTPStatus.OK),
    )

    assert middleware(request).status_code == HTTPStatus.OK


@override_settings(API_THROTTLE_ANON_RATE="1/min", API_THROTTLE_USER_RATE=None)
def test_public_api_middleware_throttles_header_less_request_when_budget_exhausted() -> (
    None
):
    request = RequestFactory().get("/api/v1/notes")
    request.user = AnonymousUser()
    middleware = PublicAPIThrottleMiddleware(
        lambda _request: HttpResponse(status=HTTPStatus.OK),
    )

    assert middleware(request).status_code == HTTPStatus.OK
    assert middleware(request).status_code == HTTPStatus.TOO_MANY_REQUESTS


@override_settings(API_THROTTLE_ANON_RATE=None, API_THROTTLE_USER_RATE="3/min")
def test_get_public_api_throttles_returns_user_throttle_when_user_rate_is_set() -> None:
    throttles = get_public_api_throttles()

    assert len(throttles) == 1
    assert isinstance(throttles[0], BaseThrottle)
