{% if cookiecutter.use_celery != "none" -%}
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True
CELERY_TASK_STORE_EAGER_RESULT = True
{% endif -%}
{% if cookiecutter.email_provider != "none" -%}
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
{% endif -%}
INSTALLED_APPS.append("django_migration_linter")  # noqa: F821  # ty: ignore[unresolved-reference]
# zeal's AppConfig.ready() installs the ORM patches that its pytest fixture
# (tests/conftest.py) relies on; the fixture alone only toggles detection on
# and off around each test.
INSTALLED_APPS.append("zeal")  # noqa: F821  # ty: ignore[unresolved-reference]
# The autouse zeal fixture treats one test function as a single N+1-detection
# window. Tests that issue several independent client requests in one
# function (e.g. django-axes lockout tests posting to /admin/login/
# repeatedly, or force_login()'s internal session cycling) trip the
# threshold across those unrelated requests: zeal's caller-detection walks
# up to the first project-owned frame common to all of them and misreports
# the aggregate count as one N+1 site. In a real deployment each request
# gets its own context via the middleware, so this can't happen there.
# These are the two models affected by that cross-request aggregation.
ZEAL_ALLOWLIST = [
    {"model": "core.User", "field": "get()"},
    {"model": "sessions.Session", "field": "get()"},
]
STORAGES["default"] = {  # noqa: F821  # ty: ignore[unresolved-reference]
    "BACKEND": "django.core.files.storage.InMemoryStorage",
}
