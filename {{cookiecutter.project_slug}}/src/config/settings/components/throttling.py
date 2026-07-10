{% if cookiecutter.use_traefik == "no" and cookiecutter.behind_proxy == "yes" -%}
from django.core.exceptions import ImproperlyConfigured

{% endif -%}
from config.settings import env

API_THROTTLE_ANON_RATE = env("API_THROTTLE_ANON_RATE", default=None)
API_THROTTLE_USER_RATE = env("API_THROTTLE_USER_RATE", default=None)
NINJA_NUM_PROXIES = {% if cookiecutter.use_traefik == "yes" %}1{% elif cookiecutter.behind_proxy == "yes" %}env.int("TRUSTED_PROXY_COUNT", default=1){% else %}0{% endif %}
{% if cookiecutter.use_traefik == "no" and cookiecutter.behind_proxy == "yes" %}
if NINJA_NUM_PROXIES < 0:
    msg = "TRUSTED_PROXY_COUNT must not be negative."
    raise ImproperlyConfigured(msg)

{% endif -%}
NINJA_EXTRA = {
    "NUM_PROXIES": NINJA_NUM_PROXIES,
    "THROTTLE_RATES": dict(
        filter(
            lambda rate: rate[1] is not None,
            (
                ("anon", API_THROTTLE_ANON_RATE),
                ("user", API_THROTTLE_USER_RATE),
            ),
        )
    ),
}
