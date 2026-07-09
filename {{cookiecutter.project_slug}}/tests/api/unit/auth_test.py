from datetime import timedelta
from http import HTTPStatus
from typing import TYPE_CHECKING

import pytest
from django.utils import timezone

from apps.api.auth import BearerTokenAuth
from apps.api.exceptions import InvalidTokenError
from apps.core.models import Token

if TYPE_CHECKING:
    from pytest_mock import MockerFixture

    from apps.core.models import User

pytestmark = pytest.mark.django_db


def test_authenticate_raises_401_when_token_is_expired(
    mocker: MockerFixture,
    user: User,
) -> None:
    raw_token, _ = Token.issue(
        expires_at=timezone.now() - timedelta(seconds=1),
        name="test token",
        user=user,
    )
    auth = BearerTokenAuth()

    with pytest.raises(InvalidTokenError) as exc_info:
        auth.authenticate(mocker.Mock(), raw_token)

    assert exc_info.value.status_code == HTTPStatus.UNAUTHORIZED


@pytest.mark.usefixtures("revoked_token")
def test_authenticate_raises_401_when_token_is_revoked(
    mocker: MockerFixture,
    raw_token: str,
) -> None:
    auth = BearerTokenAuth()

    with pytest.raises(InvalidTokenError) as exc_info:
        auth.authenticate(mocker.Mock(), raw_token)

    assert exc_info.value.status_code == HTTPStatus.UNAUTHORIZED


def test_authenticate_raises_401_when_token_is_unknown(mocker: MockerFixture) -> None:
    auth = BearerTokenAuth()

    with pytest.raises(InvalidTokenError) as exc_info:
        auth.authenticate(mocker.Mock(), "unknown-token")

    assert exc_info.value.status_code == HTTPStatus.UNAUTHORIZED


@pytest.mark.parametrize("user__is_active", [False])
def test_authenticate_raises_401_when_user_is_inactive(
    mocker: MockerFixture,
    raw_token: str,
) -> None:
    auth = BearerTokenAuth()

    with pytest.raises(InvalidTokenError) as exc_info:
        auth.authenticate(mocker.Mock(), raw_token)

    assert exc_info.value.status_code == HTTPStatus.UNAUTHORIZED


def test_authenticate_returns_user_and_sets_request_user_when_token_is_valid(
    mocker: MockerFixture,
    raw_token: str,
    user: User,
) -> None:
    auth = BearerTokenAuth()
    request = mocker.Mock()

    result = auth.authenticate(request, raw_token)

    assert result == user
    assert request.user == user


def test_authenticate_updates_last_used_at_when_token_is_valid(
    mocker: MockerFixture,
    raw_token: str,
    token: Token,
) -> None:
    auth = BearerTokenAuth()

    auth.authenticate(mocker.Mock(), raw_token)

    token.refresh_from_db()
    assert token.last_used_at is not None
