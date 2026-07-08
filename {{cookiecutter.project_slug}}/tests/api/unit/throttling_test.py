from django.conf import settings
from django.contrib.auth.models import AnonymousUser
from django.test import RequestFactory
from django.test import override_settings
from ninja_extra.throttling import BaseThrottle

from apps.api.throttling import get_public_api_throttles


@override_settings(API_THROTTLE_ANON_RATE="2/min", API_THROTTLE_USER_RATE=None)
def test_get_public_api_throttles_returns_anon_throttle_when_anon_rate_is_set(
) -> None:
    throttles = get_public_api_throttles()

    assert len(throttles) == 1
    assert isinstance(throttles[0], BaseThrottle)


@override_settings(API_THROTTLE_ANON_RATE=None, API_THROTTLE_USER_RATE=None)
def test_public_api_throttle_allows_requests_when_rates_are_unset() -> None:
    request = RequestFactory().get("/api/v1/notes")
    request.user = AnonymousUser()

    assert get_public_api_throttles()[0].allow_request(request)


def test_ninja_extra_throttle_rates_are_env_driven() -> None:
    assert settings.NINJA_EXTRA["THROTTLE_RATES"] == {}


@override_settings(API_THROTTLE_ANON_RATE=None, API_THROTTLE_USER_RATE="3/min")
def test_get_public_api_throttles_returns_user_throttle_when_user_rate_is_set() -> None:
    throttles = get_public_api_throttles()

    assert len(throttles) == 1
    assert isinstance(throttles[0], BaseThrottle)
