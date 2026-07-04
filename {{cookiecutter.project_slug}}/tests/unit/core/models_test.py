import pytest
from django.contrib.auth import get_user_model

from apps.core.models import User

pytestmark = pytest.mark.django_db


def test_get_user_model_returns_custom_user_when_project_is_configured() -> None:
    assert get_user_model() is User


def test_user_str_returns_username_for_created_user(user: User) -> None:
    assert str(user) == user.username
