from config.settings import env

DATABASES = {"default": env.db("DATABASE_URL")}
