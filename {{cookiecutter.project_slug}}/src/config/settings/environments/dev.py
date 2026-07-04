DEBUG = True
INSTALLED_APPS.append("django_extensions")  # noqa: F821  # ty: ignore[unresolved-reference]
LOGGING["handlers"]["console"]["formatter"] = "console"  # noqa: F821  # ty: ignore[unresolved-reference]
