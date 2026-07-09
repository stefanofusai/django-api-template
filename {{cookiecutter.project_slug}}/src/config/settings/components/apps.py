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
{%- if cookiecutter.email_provider == "resend" %}
    "anymail",
{%- endif %}
    "axes",
{%- if cookiecutter.use_cors == "yes" %}
    "corsheaders",
{%- endif %}
{%- if cookiecutter.use_celery == "worker+beat" %}
    "django_celery_beat",
{%- endif %}
{%- if cookiecutter.use_celery != "none" %}
    "django_celery_results",
{%- endif %}
    "django_structlog",
    "extra_checks",
{%- if cookiecutter.api_throttling == "basic" or cookiecutter.use_example_api == "yes" %}
    "ninja_extra",
{%- endif %}
    # Project
    "apps.api",
    "apps.core",
{%- if cookiecutter.use_example_api == "yes" %}
    "apps.notes",
{%- endif %}
    # Keep after apps.api so Django uses the project's export_openapi_schema command.
    "ninja",
]
