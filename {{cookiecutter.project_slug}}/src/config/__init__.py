import os

{% if cookiecutter.use_celery != "none" -%}
# Importing this package is what configures Django for every process:
# gunicorn (config.asgi) and celery (-A config) both import it before
# touching settings. The celery import below must stay AFTER setdefault.
{% else -%}
# Importing this package is what configures Django for the web process.
{% endif -%}
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
{%- if cookiecutter.use_celery != "none" %}

from .celery import app as celery_app

__all__ = ("celery_app",)
{%- endif %}
