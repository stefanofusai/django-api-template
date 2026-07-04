from django.apps import AppConfig


class ApiConfig(AppConfig):
    label = "api"
    name = "apps.api"

    def ready(self) -> None:
        from . import signals  # noqa: F401, PLC0415
