from django.core.exceptions import ImproperlyConfigured

from config.settings import env

if SECRET_KEY.startswith("django-insecure-"):  # noqa: F821  # ty: ignore[unresolved-reference]
    msg = "SECRET_KEY must be replaced with a securely generated value in production."
    raise ImproperlyConfigured(msg)
{%- if cookiecutter.email_provider == "resend" %}

ANYMAIL = {"RESEND_API_KEY": env("RESEND_API_KEY")}
{%- endif %}
API_DOCS_DECORATOR = "django.contrib.admin.views.decorators.staff_member_required"
{%- if cookiecutter.use_traefik == "yes" or cookiecutter.behind_proxy == "yes" %}
CSRF_COOKIE_SECURE = True
{%- endif %}
CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS")
{%- if cookiecutter.email_provider == "resend" %}
EMAIL_BACKEND = "anymail.backends.resend.EmailBackend"
{%- elif cookiecutter.email_provider == "smtp" %}
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = env("EMAIL_HOST")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", default="")
EMAIL_HOST_USER = env("EMAIL_HOST_USER", default="")
EMAIL_PORT = env.int("EMAIL_PORT", default=587)
EMAIL_USE_TLS = env.bool("EMAIL_USE_TLS", default=True)
{%- endif %}
LOGGING["handlers"]["console"]["formatter"] = "json"  # noqa: F821  # ty: ignore[unresolved-reference]
MIDDLEWARE.insert(  # noqa: F821  # ty: ignore[unresolved-reference]
    1,
    "whitenoise.middleware.WhiteNoiseMiddleware",
)
SECURE_CONTENT_TYPE_NOSNIFF = True
{%- if cookiecutter.use_traefik == "yes" or cookiecutter.behind_proxy == "yes" %}
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_HSTS_SECONDS = 31536000
# X-Forwarded-Proto is trusted here, which is only safe behind a proxy that
# overwrites the client-supplied header (see README, Production). The
# redirect-exempt patterns match request.path.lstrip("/") — no leading
# slash — and keep the plain-HTTP container healthchecks reachable.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_REDIRECT_EXEMPT = [r"^api/health$", r"^api/ready$"]
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
{%- endif %}
{%- if cookiecutter.use_s3_media == "yes" %}
STORAGES["default"] = {  # noqa: F821  # ty: ignore[unresolved-reference]
    "BACKEND": "storages.backends.s3.S3Storage",
    "OPTIONS": {
        "access_key": env("AWS_ACCESS_KEY_ID", default=None),
        "bucket_name": env("AWS_STORAGE_BUCKET_NAME"),
        "custom_domain": env("AWS_S3_CUSTOM_DOMAIN", default=None),
        "default_acl": None,
        "endpoint_url": env("AWS_S3_ENDPOINT_URL", default=None),
        "file_overwrite": False,
        "querystring_auth": True,
        "querystring_expire": 900,
        "region_name": env("AWS_S3_REGION_NAME", default=None),
        "secret_key": env("AWS_SECRET_ACCESS_KEY", default=None),
    },
}
{%- endif %}
STORAGES["staticfiles"] = {  # noqa: F821  # ty: ignore[unresolved-reference]
    "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
}
