{%- if cookiecutter.email_provider != "none" -%}
from config.settings import env

DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL")
{% endif -%}
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
