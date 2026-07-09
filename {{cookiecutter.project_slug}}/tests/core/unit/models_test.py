{% if cookiecutter.use_example_api == "yes" and cookiecutter.api_auth == "token" -%}
from collections.abc import Callable
from contextlib import AbstractContextManager
from datetime import timedelta

{% endif -%}
import pytest
from django.contrib.auth import get_user_model
{% if cookiecutter.use_example_api == "yes" and cookiecutter.api_auth == "token" -%}
from django.utils import timezone
{% endif %}
from apps.core.models import {% if cookiecutter.use_example_api == "yes" and cookiecutter.api_auth == "token" %}Token, {% endif %}User

pytestmark = pytest.mark.django_db


def test_get_user_model_returns_custom_user_when_project_is_configured() -> None:
    assert get_user_model() is User
{%- if cookiecutter.use_example_api == "yes" and cookiecutter.api_auth == "token" %}


def test_is_revoked_returns_false_when_not_revoked(token: Token) -> None:
    assert token.is_revoked() is False


def test_is_revoked_returns_true_when_revoked(revoked_token: Token) -> None:
    assert revoked_token.is_revoked() is True


def test_mark_used_skips_write_when_last_used_at_is_fresh(
    django_assert_num_queries: Callable[[int], AbstractContextManager[None]],
    token: Token,
) -> None:
    last_used_at = timezone.now()
    token.last_used_at = last_used_at
    token.save(update_fields=("last_used_at",))

    with django_assert_num_queries(0):
        token.mark_used()

    assert token.last_used_at == last_used_at


def test_mark_used_writes_when_last_used_at_is_stale(token: Token) -> None:
    last_used_at = timezone.now() - timedelta(minutes=2)
    token.last_used_at = last_used_at
    token.save(update_fields=("last_used_at",))

    token.mark_used()

    token.refresh_from_db()
    assert token.last_used_at is not None
    assert token.last_used_at > last_used_at


def test_token_issue_returns_pat_token_and_stores_prefix_and_digest(
    user: User,
) -> None:
    raw_token, token = Token.issue(name="test token", user=user)

    token.refresh_from_db()
    assert raw_token.startswith(f"pat_{token.prefix}_")
    assert token.digest == Token.hash(raw_token)
    assert token.digest != raw_token
    assert token.created_at is not None
    assert token.expires_at is None
    assert token.last_used_at is None
    assert token.prefix


def test_token_issue_stores_optional_expiration(user: User) -> None:
    expires_at = timezone.now() + timedelta(days=7)

    _, token = Token.issue(expires_at=expires_at, name="test token", user=user)

    assert token.expires_at == expires_at


def test_token_prefix_from_returns_none_when_token_shape_is_invalid() -> None:
    assert Token.prefix_from("jwt_deadbeefcafe_test-secret") is None
    assert Token.prefix_from("pat__test-secret") is None
    assert Token.prefix_from("pat_deadbeefcafe_") is None


def test_token_prefix_from_returns_prefix_when_token_shape_is_valid() -> None:
    assert Token.prefix_from("pat_deadbeefcafe_test-secret") == "deadbeefcafe"


def test_token_str_returns_token_name(token: Token) -> None:
    assert str(token) == "test token"
{%- endif %}


def test_user_str_returns_username_for_created_user(user: User) -> None:
    assert str(user) == user.username
