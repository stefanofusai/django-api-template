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
{%- if cookiecutter.use_celery == "worker+beat" %}
    "django_celery_beat",
{%- endif %}
{%- if cookiecutter.use_celery != "none" %}
    "django_celery_results",
{%- endif %}
{%- if cookiecutter.use_cors == "yes" %}
    "corsheaders",
{%- endif %}
    "django_structlog",
    "extra_checks",
    # Project
    "apps.api",
    "apps.core",
{%- if cookiecutter.use_example_api == "yes" %}
    "apps.notes",
{%- endif %}
]
