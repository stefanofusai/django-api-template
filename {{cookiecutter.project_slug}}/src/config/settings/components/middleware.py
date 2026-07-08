MIDDLEWARE = [
{%- if cookiecutter.use_cors == "yes" %}
    "corsheaders.middleware.CorsMiddleware",
{%- endif %}
    "django.middleware.security.SecurityMiddleware",
{%- if cookiecutter.use_csp == "yes" %}
    "django.middleware.csp.ContentSecurityPolicyMiddleware",
{%- endif %}
    "django_structlog.middlewares.RequestMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
{%- if cookiecutter.api_throttling == "basic" %}
    "apps.api.throttling.PublicAPIThrottleMiddleware",
{%- endif %}
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "axes.middleware.AxesMiddleware",
]
