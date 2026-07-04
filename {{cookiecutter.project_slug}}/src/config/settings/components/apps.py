INSTALLED_APPS = [
    # Admin theme must precede django.contrib.admin.
    "unfold",
    # Django
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Third-party
    "django_celery_results",
    "django_structlog",
    "extra_checks",
    # Project
    "apps.api",
    "apps.core",
]
