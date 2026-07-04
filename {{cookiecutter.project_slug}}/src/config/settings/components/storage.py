from config.settings import BASE_DIR

MEDIA_ROOT = BASE_DIR / "media"
MEDIA_URL = "media/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATIC_URL = "static/"
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
        "OPTIONS": {"location": MEDIA_ROOT},
    },
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
    },
}
