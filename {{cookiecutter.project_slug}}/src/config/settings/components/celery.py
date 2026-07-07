{%- if cookiecutter.use_celery == "worker+beat" -%}
from celery.schedules import crontab

{% endif -%}
from config.settings import env

CELERY_ACCEPT_CONTENT = ["json"]
{%- if cookiecutter.use_celery == "worker+beat" %}
CELERY_BEAT_SCHEDULER = "django_celery_beat.schedulers:DatabaseScheduler"
# DatabaseScheduler copies this dict into its database tables on beat
# startup; the admin then owns the live schedule (edits there persist,
# but the entry reappears if deleted while this setting still defines it).
CELERY_BEAT_SCHEDULE = {
    "clear-expired-sessions": {
        "schedule": crontab(minute=0),
        "task": "apps.core.tasks.clear_expired_sessions",
    },
}
{%- endif %}
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True
CELERY_BROKER_URL = env("CELERY_BROKER_URL", default="redis://redis:6379/1")
# Results are opt-in per task: CELERY_TASK_IGNORE_RESULT discards results by
# default; pass ignore_result=False to @shared_task to persist that task's
# result (and its STARTED state, per CELERY_TASK_TRACK_STARTED) to
# django-celery-results.
CELERY_RESULT_BACKEND = "django-db"
CELERY_RESULT_EXTENDED = True
CELERY_RESULT_SERIALIZER = "json"
CELERY_TASK_ACKS_LATE = True
CELERY_TASK_IGNORE_RESULT = True
CELERY_TASK_REJECT_ON_WORKER_LOST = True
CELERY_TASK_SERIALIZER = "json"
CELERY_TASK_SOFT_TIME_LIMIT = 300
CELERY_TASK_TIME_LIMIT = 330
CELERY_TASK_TRACK_STARTED = True
CELERY_WORKER_HIJACK_ROOT_LOGGER = False
CELERY_WORKER_PREFETCH_MULTIPLIER = 1
DJANGO_STRUCTLOG_CELERY_ENABLED = True
