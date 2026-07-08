import sentry_sdk
from django.core.exceptions import ImproperlyConfigured
{%- if cookiecutter.use_celery != "none" %}
from sentry_sdk.integrations.celery import CeleryIntegration
{%- endif %}

from config.pyproject import project_version
from config.settings import env

SENTRY_DSN = env("SENTRY_DSN")
SENTRY_ENABLE_LOGS = env.bool("SENTRY_ENABLE_LOGS", default=False)
# 10% keeps tracing/profiling affordable at production volume; raise via env for low-traffic services.
SENTRY_PROFILE_SESSION_SAMPLE_RATE = env.float(
    "SENTRY_PROFILE_SESSION_SAMPLE_RATE", default=0.1
)
SENTRY_TRACES_SAMPLE_RATE = env.float("SENTRY_TRACES_SAMPLE_RATE", default=0.1)

if not SENTRY_DSN:
    msg = "SENTRY_DSN must be set in production."
    raise ImproperlyConfigured(msg)

sentry_sdk.init(
    dsn=SENTRY_DSN,
    release=project_version,
    environment="prod",
    send_default_pii=False,
{%- if cookiecutter.use_celery == "worker+beat" %}
    integrations=[CeleryIntegration(monitor_beat_tasks=True)],
{%- elif cookiecutter.use_celery == "worker" %}
    integrations=[CeleryIntegration()],
{%- endif %}
    traces_sample_rate=SENTRY_TRACES_SAMPLE_RATE,
    profile_lifecycle="trace",
    profile_session_sample_rate=SENTRY_PROFILE_SESSION_SAMPLE_RATE,
    enable_logs=SENTRY_ENABLE_LOGS,
)
