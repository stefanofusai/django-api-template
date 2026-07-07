from http import HTTPStatus
from typing import TYPE_CHECKING
from unittest.mock import Mock

import pytest
from ninja.errors import HttpError

from apps.api.auth import BearerTokenAuth
from apps.core.models import Token

if TYPE_CHECKING:
    from apps.core.models import User

pytestmark = pytest.mark.django_db


def test_authenticate_raises_401_when_token_is_unknown() -> None:
    auth = BearerTokenAuth()

    with pytest.raises(HttpError) as exc_info:
        auth.authenticate(Mock(), "unknown-token")

    assert exc_info.value.status_code == HTTPStatus.UNAUTHORIZED


def test_authenticate_returns_user_and_sets_request_user_when_token_is_valid(
    user: User,
) -> None:
    raw_token, _ = Token.issue(name="test token", user=user)
    auth = BearerTokenAuth()
    request = Mock()

    result = auth.authenticate(request, raw_token)

    assert result == user
    assert request.user == user
