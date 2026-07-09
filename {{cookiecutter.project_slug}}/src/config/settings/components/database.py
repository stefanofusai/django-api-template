from config.settings import env

DEFAULT_DATABASE = env.db("DATABASE_URL")
DEFAULT_DATABASE["CONN_HEALTH_CHECKS"] = True
DEFAULT_DATABASE["CONN_MAX_AGE"] = env.int(
    "DATABASE_CONN_MAX_AGE", default=env.int("CONN_MAX_AGE", default=60)
)
DEFAULT_DATABASE_OPTIONS = DEFAULT_DATABASE.setdefault("OPTIONS", {})
DEFAULT_DATABASE_OPTIONS.setdefault(
    "connect_timeout", env.int("DATABASE_CONNECT_TIMEOUT", default=5)
)
DEFAULT_DATABASE_OPTIONS["options"] = (
    f"-c statement_timeout={env.int('DATABASE_STATEMENT_TIMEOUT', default=15_000)}"
)
DATABASES = {"default": DEFAULT_DATABASE}
