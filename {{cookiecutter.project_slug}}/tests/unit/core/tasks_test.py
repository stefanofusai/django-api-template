from typing import TYPE_CHECKING

from django.core import mail

from apps.core.tasks import send_email

if TYPE_CHECKING:
    from faker import Faker


def test_send_email_delivers_message_when_dispatched_eagerly(faker: Faker) -> None:
    message = faker.paragraph()
    recipient = faker.email()
    subject = faker.sentence()

    send_email.delay(message=message, recipient_list=[recipient], subject=subject)

    assert len(mail.outbox) == 1
    assert mail.outbox[0].body == message
    assert mail.outbox[0].subject == subject
    assert mail.outbox[0].to == [recipient]
