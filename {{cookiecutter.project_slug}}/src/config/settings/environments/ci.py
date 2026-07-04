CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True
CELERY_TASK_STORE_EAGER_RESULT = True
DEBUG = False
STORAGES["default"] = {  # noqa: F821  # ty: ignore[unresolved-reference]
    "BACKEND": "django.core.files.storage.InMemoryStorage",
}
