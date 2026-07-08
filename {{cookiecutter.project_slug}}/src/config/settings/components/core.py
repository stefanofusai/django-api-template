from config.settings import env

ALLOWED_HOSTS = env.list("ALLOWED_HOSTS")
API_DOCS_DECORATOR = "apps.api.docs.public"
{%- if cookiecutter.api_throttling == "basic" %}
API_THROTTLE_ANON_RATE = env("API_THROTTLE_ANON_RATE", default=None)
API_THROTTLE_USER_RATE = env("API_THROTTLE_USER_RATE", default=None)
{%- endif %}
ASGI_APPLICATION = "config.asgi.application"
{%- if cookiecutter.use_cors == "yes" %}
CORS_ALLOWED_ORIGINS = env.list("CORS_ALLOWED_ORIGINS")
CORS_ALLOW_CREDENTIALS = env.bool("CORS_ALLOW_CREDENTIALS", default=False)
{%- endif %}
DEBUG = False
{%- if cookiecutter.api_throttling == "basic" %}
NINJA_EXTRA = {"THROTTLE_RATES": {}}

if API_THROTTLE_ANON_RATE is not None:
    NINJA_EXTRA["THROTTLE_RATES"]["anon"] = API_THROTTLE_ANON_RATE

if API_THROTTLE_USER_RATE is not None:
    NINJA_EXTRA["THROTTLE_RATES"]["user"] = API_THROTTLE_USER_RATE
{% endif %}
ROOT_URLCONF = "config.urls"
SECRET_KEY = env("SECRET_KEY")
TIME_ZONE = "UTC"
