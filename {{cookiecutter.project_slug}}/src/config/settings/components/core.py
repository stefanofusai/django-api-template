from config.settings import env

ALLOWED_HOSTS = env.list("ALLOWED_HOSTS")
API_DOCS_DECORATOR = "apps.api.docs.public"
ASGI_APPLICATION = "config.asgi.application"
{%- if cookiecutter.use_cors == "yes" %}
CORS_ALLOWED_ORIGINS = env.list("CORS_ALLOWED_ORIGINS")
CORS_ALLOW_CREDENTIALS = env.bool("CORS_ALLOW_CREDENTIALS", default=False)
{%- endif %}
DEBUG = False
ROOT_URLCONF = "config.urls"
SECRET_KEY = env("SECRET_KEY")
TIME_ZONE = "UTC"
