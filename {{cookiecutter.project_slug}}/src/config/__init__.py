import os

# Importing this package is what configures Django for every process:
# gunicorn (config.wsgi) and celery (-A config) both import it before
# touching settings. The celery import below must stay AFTER setdefault.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

from .celery import app as celery_app

__all__ = ("celery_app",)
