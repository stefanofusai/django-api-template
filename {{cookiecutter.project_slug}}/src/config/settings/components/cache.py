from config.settings import env

CACHES = {"default": env.cache("CACHE_URL")}

if CACHES["default"]["BACKEND"] == "django_redis.cache.RedisCache":
    CACHES["default"].setdefault("OPTIONS", {}).update(
        {
            "SOCKET_CONNECT_TIMEOUT": 1,
            "SOCKET_TIMEOUT": 1,
        }
    )
