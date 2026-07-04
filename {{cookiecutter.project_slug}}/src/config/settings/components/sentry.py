import sentry_sdk
from django.core.exceptions import ImproperlyConfigured
from sentry_sdk.integrations.celery import CeleryIntegration

from config.pyproject import project_version
from config.settings import env

SENTRY_DSN = env("SENTRY_DSN")
SENTRY_ENABLE_LOGS = env.bool("SENTRY_ENABLE_LOGS", default=False)
SENTRY_PROFILE_SESSION_SAMPLE_RATE = env.float(
    "SENTRY_PROFILE_SESSION_SAMPLE_RATE", default=1.0
)
SENTRY_TRACES_SAMPLE_RATE = env.float("SENTRY_TRACES_SAMPLE_RATE", default=1.0)

if not SENTRY_DSN:
    msg = "SENTRY_DSN must be set in production."
    raise ImproperlyConfigured(msg)

sentry_sdk.init(
    dsn=SENTRY_DSN,
    release=project_version,
    environment="prod",
    send_default_pii=False,
    integrations=[CeleryIntegration(monitor_beat_tasks=True)],
    traces_sample_rate=SENTRY_TRACES_SAMPLE_RATE,
    profile_lifecycle="trace",
    profile_session_sample_rate=SENTRY_PROFILE_SESSION_SAMPLE_RATE,
    enable_logs=SENTRY_ENABLE_LOGS,
)
