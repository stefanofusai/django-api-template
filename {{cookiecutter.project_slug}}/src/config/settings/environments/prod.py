from config.settings import env

CSRF_COOKIE_SECURE = True
CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS")
DEBUG = False
LOGGING["handlers"]["console"]["formatter"] = "json"  # noqa: F821  # ty: ignore[unresolved-reference]
MIDDLEWARE.insert(  # noqa: F821  # ty: ignore[unresolved-reference]
    1,
    "whitenoise.middleware.WhiteNoiseMiddleware",
)
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_HSTS_SECONDS = 31536000
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_REDIRECT_EXEMPT = [r"^api/ready$"]
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
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
STORAGES["staticfiles"] = {  # noqa: F821  # ty: ignore[unresolved-reference]
    "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
}
