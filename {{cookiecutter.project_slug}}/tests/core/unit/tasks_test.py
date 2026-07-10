from datetime import timedelta
from typing import TYPE_CHECKING

import pytest
{% if cookiecutter.email_provider != "none" -%}
from django.conf import settings
{% endif -%}
from django.contrib.sessions.models import Session
{% if cookiecutter.email_provider != "none" -%}
from django.core import mail
{% endif -%}
from django.utils import timezone
{% if cookiecutter.use_example_api == "yes" and cookiecutter.api_auth == "jwt" -%}
from ninja_jwt.token_blacklist.models import OutstandingToken
{% endif %}
from apps.core.tasks import (
    clear_expired_sessions,
    {%- if cookiecutter.use_example_api == "yes" and cookiecutter.api_auth == "jwt" %}
    flush_expired_tokens,
    {%- endif %}
    {%- if cookiecutter.email_provider != "none" %}
    send_email,
    {%- endif %}
)

if TYPE_CHECKING:
    from faker import Faker

pytestmark = pytest.mark.django_db


def test_clear_expired_sessions_deletes_expired_rows_when_dispatched_eagerly(
    faker: Faker,
) -> None:
    # Session is a third-party model with no registered factory, and expiry
    # timestamps are the behavior under test, so create rows directly.
    expired = Session.objects.create(
        expire_date=timezone.now() - timedelta(days=1),
        session_data="expired",
        session_key=faker.unique.uuid4(),
    )
    live = Session.objects.create(
        expire_date=timezone.now() + timedelta(days=1),
        session_data="live",
        session_key=faker.unique.uuid4(),
    )

    clear_expired_sessions.delay()

    assert not Session.objects.filter(pk=expired.pk).exists()
    assert Session.objects.filter(pk=live.pk).exists()


def test_clear_expired_sessions_uses_at_least_once_delivery_semantics() -> None:
    assert clear_expired_sessions.acks_late is True
    assert clear_expired_sessions.reject_on_worker_lost is True
{%- if cookiecutter.use_example_api == "yes" and cookiecutter.api_auth == "jwt" %}


def test_flush_expired_tokens_deletes_expired_rows_when_dispatched_eagerly(
    faker: Faker,
) -> None:
    # OutstandingToken is a third-party model with no registered factory, and
    # expiry timestamps are the behavior under test, so create rows directly.
    expired = OutstandingToken.objects.create(
        expires_at=timezone.now() - timedelta(days=1),
        jti=faker.unique.uuid4(),
        token="expired",  # noqa: S106 -- opaque test token, not a password.
    )
    live = OutstandingToken.objects.create(
        expires_at=timezone.now() + timedelta(days=1),
        jti=faker.unique.uuid4(),
        token="live",  # noqa: S106 -- opaque test token, not a password.
    )

    flush_expired_tokens.delay()

    assert not OutstandingToken.objects.filter(pk=expired.pk).exists()
    assert OutstandingToken.objects.filter(pk=live.pk).exists()
{%- endif %}
{%- if cookiecutter.email_provider != "none" %}


def test_send_email_delivers_message_when_dispatched_eagerly(faker: Faker) -> None:
    message = faker.paragraph()
    recipient = faker.email()
    subject = faker.sentence()

    send_email.delay(message=message, recipient_list=[recipient], subject=subject)

    assert len(mail.outbox) == 1
    assert mail.outbox[0].body == message
    assert mail.outbox[0].from_email == settings.DEFAULT_FROM_EMAIL
    assert mail.outbox[0].subject == subject
    assert mail.outbox[0].to == [recipient]


def test_send_email_uses_at_most_once_delivery_semantics() -> None:
    assert send_email.acks_late is False
    assert send_email.reject_on_worker_lost is False
{%- endif %}
