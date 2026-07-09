from datetime import timedelta

NINJA_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=15),
    "BLACKLIST_AFTER_ROTATION": True,
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "SIGNING_KEY": SECRET_KEY,  # noqa: F821  # ty: ignore[unresolved-reference]
    "UPDATE_LAST_LOGIN": True,
}
