from celery import Celery
from django_structlog.celery.steps import DjangoStructLogInitStep

app = Celery("{{ cookiecutter.project_slug }}")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
app.steps["worker"].add(DjangoStructLogInitStep)  # ty: ignore[not-subscriptable]
