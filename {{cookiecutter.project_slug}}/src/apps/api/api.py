from ninja import NinjaAPI

from config.pyproject import project_name, project_version

from .routes import health_router, ready_router

api = NinjaAPI(title=project_name, version=str(project_version))
api.add_router("", health_router)
api.add_router("", ready_router)
