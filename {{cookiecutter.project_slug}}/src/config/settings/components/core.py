from config.settings import env

ALLOWED_HOSTS = env.list("ALLOWED_HOSTS")
API_DOCS_DECORATOR = "apps.api.docs.public"
DEBUG = False
ROOT_URLCONF = "config.urls"
SECRET_KEY = env("SECRET_KEY")
TIME_ZONE = "UTC"
WSGI_APPLICATION = "config.wsgi.application"
