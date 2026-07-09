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
{%- if cookiecutter.use_cors == "yes" %}
    "components/cors.py",
{%- endif %}
{%- if cookiecutter.use_csp == "yes" %}
    "components/csp.py",
{%- endif %}
    "components/permissions_policy.py",
{%- if cookiecutter.api_throttling == "basic" %}
    "components/throttling.py",
{%- endif %}
    "components/apps.py",
    "components/middleware.py",
    "components/authentication.py",
{%- if cookiecutter.use_example_api == "yes" and cookiecutter.api_auth == "jwt" %}
    "components/jwt.py",
{%- endif %}
    "components/templates.py",
    "components/database.py",
    "components/cache.py",
{%- if cookiecutter.use_celery != "none" %}
    "components/celery.py",
{%- endif %}
    "components/email.py",
    "components/logging.py",
    "components/storage.py",
    "components/checks.py",
    f"environments/{DJANGO_ENV}.py",
]
{%- if cookiecutter.use_sentry == "yes" %}

if DJANGO_ENV == "prod":  # pragma: no cover
    settings_files.append("components/sentry.py")
{%- endif %}

# include() executes every file below in one shared namespace, in order:
# components define names (MIDDLEWARE, LOGGING, STORAGES, ...) that the
# environment overlay at the end mutates. The overlays' noqa: F821 markers
# exist because linters cannot see this shared namespace.
include(*settings_files)

# See: https://github.com/typeddjango/django-stubs?tab=readme-ov-file#i-cannot-use-queryset-or-manager-with-type-annotations
django_stubs_ext.monkeypatch()
