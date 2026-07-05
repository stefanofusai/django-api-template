from django.conf import settings
from django.utils.module_loading import import_string
from ninja import NinjaAPI

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
