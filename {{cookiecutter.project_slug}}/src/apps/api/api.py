from django.conf import settings
from django.utils.module_loading import import_string
from ninja import NinjaAPI
{%- if cookiecutter.use_example_api == "yes" %}
from ninja_extra import NinjaExtraAPI
{%- endif %}

{% if cookiecutter.use_example_api == "yes" -%}
{% if cookiecutter.api_auth == "token" -%}
from apps.core.controllers import TokensController
{% endif -%}
from apps.notes.controllers import NotesController
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

v1_api = {% if cookiecutter.use_example_api == "yes" %}NinjaExtraAPI{% else %}NinjaAPI{% endif %}(
    title=project_name,
    version="1.0.0",
    docs_decorator=docs_decorator,
    urls_namespace="v1",
)
{%- if cookiecutter.use_example_api == "yes" %}
v1_api.register_controllers(NotesController)
{%- if cookiecutter.api_auth == "token" %}
v1_api.register_controllers(TokensController)
{%- endif %}
{%- endif %}
