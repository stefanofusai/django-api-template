DEBUG = True
INSTALLED_APPS.append("django_extensions")  # noqa: F821  # ty: ignore[unresolved-reference]
INSTALLED_APPS.append("zeal")  # noqa: F821  # ty: ignore[unresolved-reference]
LOGGING["handlers"]["console"]["formatter"] = "console"  # noqa: F821  # ty: ignore[unresolved-reference]
MIDDLEWARE.append("zeal.middleware.zeal_middleware")  # noqa: F821  # ty: ignore[unresolved-reference]
# Mirrors the test-only allow-list in environments/ci.py: the middleware
# gives each real request its own N+1-detection window, so this can't
# actually happen here, but kept in sync so dev and tests agree on what's
# allowed. See ci.py for the cross-request aggregation explanation.
ZEAL_ALLOWLIST = [
    {"model": "core.User", "field": "get()"},
    {"model": "sessions.Session", "field": "get()"},
]
