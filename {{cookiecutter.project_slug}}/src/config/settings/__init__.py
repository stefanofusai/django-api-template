from pathlib import Path

import django_stubs_ext
import environ
from split_settings.tools import include

BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent

env = environ.Env()
environ.Env.read_env(env_file=BASE_DIR / ".env")

DJANGO_ENV = env("DJANGO_ENV")

settings_files = [
    "components/core.py",
    "components/apps.py",
    "components/middleware.py",
    "components/authentication.py",
    "components/templates.py",
    "components/database.py",
    "components/cache.py",
    "components/celery.py",
    "components/email.py",
    "components/logging.py",
    "components/storage.py",
    "components/checks.py",
    f"environments/{DJANGO_ENV}.py",
]

if DJANGO_ENV == "prod":  # pragma: no cover
    settings_files.append("components/sentry.py")

include(*settings_files)

# See: https://github.com/typeddjango/django-stubs?tab=readme-ov-file#i-cannot-use-queryset-or-manager-with-type-annotations
django_stubs_ext.monkeypatch()
