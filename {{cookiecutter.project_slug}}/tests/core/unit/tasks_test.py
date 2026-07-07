from datetime import timedelta
{% if cookiecutter.email_provider != "none" -%}
from typing import TYPE_CHECKING

import pytest
from django.conf import settings
from django.contrib.sessions.models import Session
from django.core import mail
from django.utils import timezone

from apps.core.tasks import clear_expired_sessions, send_email

if TYPE_CHECKING:
    from faker import Faker
{% else %}
import pytest
from django.contrib.sessions.models import Session
from django.utils import timezone

from apps.core.tasks import clear_expired_sessions
{% endif %}
pytestmark = pytest.mark.django_db


def test_clear_expired_sessions_deletes_expired_rows_when_dispatched_eagerly() -> None:
    # Session is a third-party model with no registered factory, and expiry
    # timestamps are the behavior under test, so create rows directly.
    expired = Session.objects.create(
        expire_date=timezone.now() - timedelta(days=1),
        session_data="expired",
        session_key="plan010expired",
    )
    live = Session.objects.create(
        expire_date=timezone.now() + timedelta(days=1),
        session_data="live",
        session_key="plan010live",
    )

    clear_expired_sessions.delay()

    assert not Session.objects.filter(pk=expired.pk).exists()
    assert Session.objects.filter(pk=live.pk).exists()
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
{%- endif %}
