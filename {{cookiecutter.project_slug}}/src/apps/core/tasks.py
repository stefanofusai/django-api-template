from celery import shared_task
from django.core.mail import send_mail


@shared_task
def send_email(*, message: str, recipient_list: list[str], subject: str) -> None:
    send_mail(
        from_email=None, message=message, recipient_list=recipient_list, subject=subject
    )
