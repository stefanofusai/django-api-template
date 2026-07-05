{% if cookiecutter.use_celery != "none" -%}
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True
CELERY_TASK_STORE_EAGER_RESULT = True
{% endif -%}
{% if cookiecutter.email_provider != "none" -%}
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
{% endif -%}
STORAGES["default"] = {  # noqa: F821  # ty: ignore[unresolved-reference]
    "BACKEND": "django.core.files.storage.InMemoryStorage",
}
