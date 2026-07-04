from config.settings import env

CACHES = {"default": env.cache("CACHE_URL")}
