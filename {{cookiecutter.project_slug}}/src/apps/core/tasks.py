{%- if cookiecutter.email_provider != "none" -%}
from celery import shared_task
from django.core.mail import send_mail
from django.core.management import call_command
{%- else -%}
from celery import shared_task
from django.core.management import call_command
{%- endif %}


@shared_task
def clear_expired_sessions() -> None:
    call_command("clearsessions")
{%- if cookiecutter.use_example_api == "yes" and cookiecutter.api_auth == "jwt" %}


@shared_task
def flush_expired_tokens() -> None:
    call_command("flushexpiredtokens")
{%- endif %}
{%- if cookiecutter.email_provider != "none" %}


@shared_task(acks_late=False, reject_on_worker_lost=False)
def send_email(*, message: str, recipient_list: list[str], subject: str) -> None:
    send_mail(
        from_email=None, message=message, recipient_list=recipient_list, subject=subject
    )
{%- endif %}
