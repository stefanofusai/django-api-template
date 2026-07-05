from ninja import NinjaAPI

from config.pyproject import project_name

from .routes import health_router, ready_router

ops_api = NinjaAPI(
    title=f"{project_name} (operations)",
    urls_namespace="ops",
)
ops_api.add_router("", health_router)
ops_api.add_router("", ready_router)

v1_api = NinjaAPI(
    title=project_name,
    urls_namespace="v1",
    version="1.0.0",
)
