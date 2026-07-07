import pytest
from django.contrib.auth import get_user_model

from apps.core.models import {% if cookiecutter.use_example_api == "yes" and cookiecutter.api_auth == "token" %}Token, User{% else %}User{% endif %}

pytestmark = pytest.mark.django_db


def test_get_user_model_returns_custom_user_when_project_is_configured() -> None:
    assert get_user_model() is User
{%- if cookiecutter.use_example_api == "yes" and cookiecutter.api_auth == "token" %}


def test_token_issue_returns_raw_token_and_stores_only_digest(user: User) -> None:
    raw_token, token = Token.issue(name="test token", user=user)

    assert raw_token
    assert token.digest == Token.hash(raw_token)
    assert token.digest != raw_token


def test_token_str_returns_token_name(user: User) -> None:
    _, token = Token.issue(name="test token", user=user)

    assert str(token) == "test token"
{%- endif %}


def test_user_str_returns_username_for_created_user(user: User) -> None:
    assert str(user) == user.username
