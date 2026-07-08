from django.conf import settings
from django.utils.module_loading import import_string
from ninja import NinjaAPI

{% if cookiecutter.use_example_api == "yes" -%}
from apps.notes.routes import router as notes_router
{% endif -%}
{% if cookiecutter.api_throttling == "basic" -%}
from apps.api.throttling import get_public_api_throttles
{% endif -%}
from config.pyproject import project_name

from .routes import health_router, ready_router

docs_decorator = import_string(settings.API_DOCS_DECORATOR)

internal_api = NinjaAPI(
    title=f"{project_name} (internal)",
    docs_decorator=docs_decorator,
    urls_namespace="internal",
)
internal_api.add_router("", health_router)
internal_api.add_router("", ready_router)

v1_api = NinjaAPI(
    title=project_name,
    version="1.0.0",
    docs_decorator=docs_decorator,
    urls_namespace="v1",
)
{%- if cookiecutter.use_example_api == "yes" %}
v1_api.add_router(
    "/notes",
    notes_router,
{%- if cookiecutter.api_throttling == "basic" %}
    throttle=get_public_api_throttles(),
{%- endif %}
)
{%- endif %}
