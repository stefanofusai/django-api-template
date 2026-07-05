from ninja import NinjaAPI

from config.pyproject import project_name

from .routes import health_router, ready_router

internal_api = NinjaAPI(
    title=f"{project_name} (internal)",
    urls_namespace="internal",
)
internal_api.add_router("", health_router)
internal_api.add_router("", ready_router)

v1_api = NinjaAPI(
    title=project_name,
    urls_namespace="v1",
    version="1.0.0",
)
