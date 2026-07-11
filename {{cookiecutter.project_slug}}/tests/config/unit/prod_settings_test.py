import json
import os
import subprocess
import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from faker import Faker


def test_ci_settings_preserves_locmem_cache_configuration(faker: Faker) -> None:
    result = _run_prod_settings_script(
        faker,
        {"CACHE_URL": "locmemcache://", "DJANGO_ENV": "ci"},
        (
            "import config.settings as s; "
            "cache = s.CACHES['default']; "
            "print(cache['BACKEND']); "
            "print(cache.get('OPTIONS', {}))"
        ),
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.splitlines() == [
        "django.core.cache.backends.locmem.LocMemCache",
        "{}",
    ]


def test_prod_settings_configures_database_timeouts(faker: Faker) -> None:
    result = _run_prod_settings_script(
        faker,
        {},
        (
            "import config.settings as s; "
            "options = s.DATABASES['default']['OPTIONS']; "
            "print(options['connect_timeout']); "
            "print(options['options'])"
        ),
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.splitlines() == [
        "5",
        "-c lock_timeout=5000 -c statement_timeout=15000",
    ]

{% if cookiecutter.use_s3_media == "no" %}
def test_prod_settings_configures_local_media_storage(faker: Faker) -> None:
    result = _run_prod_settings_script(
        faker,
        {},
        (
            "import json; import config.settings as s; "
            "print(json.dumps({"
            "'media_root': str(s.MEDIA_ROOT), "
            "'storage': s.STORAGES['default']"
            "}, default=str, sort_keys=True))"
        ),
    )

    assert result.returncode == 0, result.stderr
    values = json.loads(result.stdout)
    assert values == {
        "media_root": values["storage"]["OPTIONS"]["location"],
        "storage": {
            "BACKEND": "django.core.files.storage.FileSystemStorage",
            "OPTIONS": {"location": values["media_root"]},
        },
    }

{% endif -%}
{% if cookiecutter.email_provider == "none" %}
def test_prod_settings_configures_no_email_provider(faker: Faker) -> None:
    result = _run_prod_settings_script(
        faker,
        {},
        (
            "import json; import config.settings as s; "
            "print(json.dumps({"
            "'backend': s.EMAIL_BACKEND, "
            "'default_from_email': getattr(s, 'DEFAULT_FROM_EMAIL', None)"
            "}, sort_keys=True))"
        ),
    )

    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == {
        "backend": "django.core.mail.backends.console.EmailBackend",
        "default_from_email": None,
    }

{% endif -%}
{% if cookiecutter.use_traefik == "yes" or cookiecutter.behind_proxy == "yes" %}
def test_prod_settings_configures_proxy_security_settings(faker: Faker) -> None:
    result = _run_prod_settings_script(
        faker,
        {},
        (
            "import config.settings as s; "
            "print(s.CSRF_COOKIE_SECURE); "
            "print(s.CSRF_TRUSTED_ORIGINS); "
            "print(s.SECURE_HSTS_INCLUDE_SUBDOMAINS); "
            "print(s.SECURE_HSTS_PRELOAD); "
            "print(s.SECURE_HSTS_SECONDS); "
            "print(s.SECURE_PROXY_SSL_HEADER); "
            "print(s.SECURE_REDIRECT_EXEMPT); "
            "print(s.SECURE_SSL_REDIRECT); "
            "print(s.SESSION_COOKIE_SECURE)"
        ),
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.splitlines() == [
        "True",
        "['https://api.example.test']",
        "True",
        "True",
        "31536000",
        "('HTTP_X_FORWARDED_PROTO', 'https')",
        "['^api/health$', '^api/ready$']",
        "True",
        "True",
    ]

{% endif %}
def test_prod_settings_configures_redis_cache_timeouts(faker: Faker) -> None:
    result = _run_prod_settings_script(
        faker,
        {},
        (
            "import config.settings as s; "
            "cache = s.CACHES['default']; "
            "print(cache['BACKEND']); "
            "print(cache['OPTIONS']['SOCKET_CONNECT_TIMEOUT']); "
            "print(cache['OPTIONS']['SOCKET_TIMEOUT'])"
        ),
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.splitlines() == [
        "django_redis.cache.RedisCache",
        "1",
        "1",
    ]

{% if cookiecutter.email_provider == "resend" %}
def test_prod_settings_configures_resend_email(faker: Faker) -> None:
    resend_api_key = f"re_{faker.pystr(min_chars=24, max_chars=24)}"
    result = _run_prod_settings_script(
        faker,
        {"RESEND_API_KEY": resend_api_key},
        (
            "import json; import config.settings as s; "
            "print(json.dumps({"
            "'anymail': s.ANYMAIL, "
            "'backend': s.EMAIL_BACKEND, "
            "'default_from_email': s.DEFAULT_FROM_EMAIL"
            "}, sort_keys=True))"
        ),
    )

    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == {
        "anymail": {"RESEND_API_KEY": resend_api_key},
        "backend": "anymail.backends.resend.EmailBackend",
        "default_from_email": "noreply@example.test",
    }

{% endif -%}
{% if cookiecutter.use_s3_media == "yes" %}
def test_prod_settings_configures_s3_media_storage(faker: Faker) -> None:
    bucket_name = faker.slug()
    result = _run_prod_settings_script(
        faker,
        {
            "AWS_ACCESS_KEY_ID": "mock-access-key",
            "AWS_S3_CUSTOM_DOMAIN": "media.example.test",
            "AWS_S3_ENDPOINT_URL": "https://s3.example.test",
            "AWS_S3_REGION_NAME": "eu-west-1",
            "AWS_SECRET_ACCESS_KEY": "mock-secret-access-key",
            "AWS_STORAGE_BUCKET_NAME": bucket_name,
        },
        (
            "import json; import config.settings as s; "
            "print(json.dumps(s.STORAGES['default'], sort_keys=True))"
        ),
    )

    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == {
        "BACKEND": "storages.backends.s3.S3Storage",
        "OPTIONS": {
            "access_key": "mock-access-key",
            "bucket_name": bucket_name,
            "custom_domain": "media.example.test",
            "default_acl": None,
            "endpoint_url": "https://s3.example.test",
            "file_overwrite": False,
            "querystring_auth": True,
            "querystring_expire": 900,
            "region_name": "eu-west-1",
            "secret_key": "mock-secret-access-key",
        },
    }

{% endif -%}
{% if cookiecutter.email_provider == "smtp" %}
def test_prod_settings_configures_smtp_email(faker: Faker) -> None:
    result = _run_prod_settings_script(
        faker,
        {
            "EMAIL_HOST_PASSWORD": "mock-smtp-password",
            "EMAIL_HOST_USER": "mock-smtp-user",
            "EMAIL_PORT": "2525",
            "EMAIL_USE_TLS": "false",
        },
        (
            "import json; import config.settings as s; "
            "print(json.dumps({"
            "'backend': s.EMAIL_BACKEND, "
            "'default_from_email': s.DEFAULT_FROM_EMAIL, "
            "'host': s.EMAIL_HOST, "
            "'password': s.EMAIL_HOST_PASSWORD, "
            "'port': s.EMAIL_PORT, "
            "'tls': s.EMAIL_USE_TLS, "
            "'user': s.EMAIL_HOST_USER"
            "}, sort_keys=True))"
        ),
    )

    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == {
        "backend": "django.core.mail.backends.smtp.EmailBackend",
        "default_from_email": "noreply@example.test",
        "host": "smtp.example.test",
        "password": "mock-smtp-password",
        "port": 2525,
        "tls": False,
        "user": "mock-smtp-user",
    }

{% endif %}
def test_prod_settings_configures_static_files_and_logging(faker: Faker) -> None:
    result = _run_prod_settings_script(
        faker,
        {},
        (
            "import json; import config.settings as s; "
            "print(json.dumps({"
            "'content_type_nosniff': s.SECURE_CONTENT_TYPE_NOSNIFF, "
            "'console_formatter': s.LOGGING['handlers']['console']['formatter'], "
            "'staticfiles': s.STORAGES['staticfiles']"
            "}, sort_keys=True))"
        ),
    )

    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == {
        "console_formatter": "json",
        "content_type_nosniff": True,
        "staticfiles": {
            "BACKEND": ("whitenoise.storage.CompressedManifestStaticFilesStorage")
        },
    }


def test_prod_settings_honors_database_timeout_overrides_when_configured(
    faker: Faker,
) -> None:
    result = _run_prod_settings_script(
        faker,
        {
            "DATABASE_CONNECT_TIMEOUT": "7",
            "DATABASE_LOCK_TIMEOUT": "8000",
            "DATABASE_STATEMENT_TIMEOUT": "45000",
        },
        (
            "import config.settings as s; "
            "options = s.DATABASES['default']['OPTIONS']; "
            "print(options['connect_timeout']); "
            "print(options['options'])"
        ),
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.splitlines() == [
        "7",
        "-c lock_timeout=8000 -c statement_timeout=45000",
    ]

{% if cookiecutter.use_traefik == "no" and cookiecutter.behind_proxy == "no" %}
def test_prod_settings_leaves_proxy_security_settings_disabled_without_proxy(
    faker: Faker,
) -> None:
    result = _run_prod_settings_script(
        faker,
        {},
        (
            "import config.settings as s; "
            "print(getattr(s, 'CSRF_COOKIE_SECURE', False)); "
            "print(getattr(s, 'SECURE_HSTS_INCLUDE_SUBDOMAINS', False)); "
            "print(getattr(s, 'SECURE_HSTS_PRELOAD', False)); "
            "print(getattr(s, 'SECURE_HSTS_SECONDS', 0)); "
            "print(getattr(s, 'SECURE_PROXY_SSL_HEADER', None)); "
            "print(getattr(s, 'SECURE_REDIRECT_EXEMPT', [])); "
            "print(getattr(s, 'SECURE_SSL_REDIRECT', False)); "
            "print(getattr(s, 'SESSION_COOKIE_SECURE', False))"
        ),
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.splitlines() == [
        "False",
        "False",
        "False",
        "0",
        "None",
        "[]",
        "False",
        "False",
    ]

{% endif %}
def test_prod_settings_place_whitenoise_directly_after_security_middleware(
    faker: Faker,
) -> None:
    env = os.environ | _base_prod_env(faker)
    env["PYTHONPATH"] = "src"
    script = (
        "import config.settings as s; "
        "security = s.MIDDLEWARE.index('django.middleware.security.SecurityMiddleware'); "
        "whitenoise = s.MIDDLEWARE.index('whitenoise.middleware.WhiteNoiseMiddleware'); "
        "raise SystemExit(0 if whitenoise == security + 1 else 1)"
    )

    result = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True,
        check=False,
        env=env,
        text=True,
    )

    assert result.returncode == 0, result.stderr


def test_prod_settings_preserves_database_url_options_when_setting_timeouts(
    faker: Faker,
) -> None:
    result = _run_prod_settings_script(
        faker,
        {
            "DATABASE_STATEMENT_TIMEOUT": "45000",
            "DATABASE_URL": (
                "postgres://my_project:mock-postgres-password@postgres:5432/"
                "my_project?connect_timeout=10&options=-c%20statement_timeout%3D99"
                "&sslmode=require"
            ),
            "POSTGRES_PASSWORD": "mock-postgres-password",
        },
        (
            "import config.settings as s; "
            "options = s.DATABASES['default']['OPTIONS']; "
            "print(options['connect_timeout']); "
            "print(options['options']); "
            "print(options['sslmode'])"
        ),
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.splitlines() == [
        "10",
        "-c lock_timeout=5000 -c statement_timeout=45000",
        "require",
    ]


def test_prod_settings_reject_default_database_password_when_scaffold_value_is_kept(
    faker: Faker,
) -> None:
    result = _import_prod_settings(
        faker,
        {
            "DATABASE_URL": (
                "postgres://{{ cookiecutter.project_slug.replace('-', '_') }}:{{ cookiecutter.project_slug.replace('-', '_') }}@postgres:5432/{{ cookiecutter.project_slug.replace('-', '_') }}"
            ),
        },
    )

    assert result.returncode != 0
    assert (
        "The default database password must be replaced with a securely "
        "generated value in production." in result.stderr
    )


{% if cookiecutter.redis == "compose" -%}
def test_prod_settings_reject_default_redis_password_when_scaffold_value_is_kept(
    faker: Faker,
) -> None:
    result = _import_prod_settings(
        faker,
        {"REDIS_PASSWORD": "{{ cookiecutter.project_slug.replace('-', '_') }}"},
    )

    assert result.returncode != 0
    assert (
        "The default Redis password must be replaced with a securely "
        "generated value in production." in result.stderr
    )


{% endif -%}
def test_prod_settings_reject_example_allowed_host_when_example_domain_is_configured(
    faker: Faker,
) -> None:
    result = _import_prod_settings(
        faker,
        {"ALLOWED_HOSTS": "localhost,127.0.0.1,example.com"},
    )

    assert result.returncode != 0
    assert "ALLOWED_HOSTS must not contain example.com in production." in result.stderr


def test_prod_settings_reject_insecure_secret_key_when_scaffold_value_is_kept(
    faker: Faker,
) -> None:
    result = _import_prod_settings(
        faker,
        {"SECRET_KEY": "django-insecure-mock-secret-key"},
    )

    assert result.returncode != 0
    assert (
        "SECRET_KEY must be replaced with a securely generated value in production."
        in result.stderr
    )


{% if cookiecutter.redis == "compose" -%}
{% if cookiecutter.use_celery != "none" -%}
def test_prod_settings_reject_mismatched_broker_password_when_redis_is_compose(
    faker: Faker,
) -> None:
    result = _import_prod_settings(
        faker,
        {"CELERY_BROKER_URL": "redis://:wrong@redis:6379/1"},
    )

    assert result.returncode != 0
    assert "CELERY_BROKER_URL password must match REDIS_PASSWORD." in result.stderr


{% endif -%}
def test_prod_settings_reject_mismatched_cache_password_when_redis_is_compose(
    faker: Faker,
) -> None:
    result = _import_prod_settings(
        faker,
        {"CACHE_URL": "rediscache://:wrong@redis:6379/0"},
    )

    assert result.returncode != 0
    assert "CACHE_URL password must match REDIS_PASSWORD." in result.stderr


{% endif -%}
{% if cookiecutter.postgres == "compose" -%}
def test_prod_settings_reject_mismatched_database_password_when_postgres_is_compose(
    faker: Faker,
) -> None:
    result = _import_prod_settings(
        faker,
        {"DATABASE_URL": "postgres://my_project:wrong@postgres:5432/my_project"},
    )

    assert result.returncode != 0
    assert "DATABASE_URL password must match POSTGRES_PASSWORD." in result.stderr


{% endif -%}
{% if cookiecutter.use_cors == "yes" -%}
def test_prod_settings_reject_missing_cors_allowed_origins_when_cors_is_enabled(
    faker: Faker,
) -> None:
    result = _import_prod_settings(
        faker,
        {"CORS_ALLOWED_ORIGINS": ""},
    )

    assert result.returncode != 0
    assert "CORS_ALLOWED_ORIGINS must not be empty in production." in result.stderr


{% endif -%}
# Utils


def _base_prod_env(faker: Faker) -> dict[str, str]:
    postgres_password = faker.bothify(text="mock-postgres-password-????????-########")
    redis_password = faker.bothify(text="mock-redis-password-????????-########")
    sentry_key = faker.hexify(text="^" * 32)

    return {
        "ALLOWED_HOSTS": "localhost,127.0.0.1,api.example.test",
        "AWS_STORAGE_BUCKET_NAME": faker.slug(),
        "CACHE_URL": f"rediscache://:{redis_password}@redis:6379/0",
        "CELERY_BROKER_URL": f"redis://:{redis_password}@redis:6379/1",
        "CORS_ALLOWED_ORIGINS": "https://app.example.test",
        "CSRF_TRUSTED_ORIGINS": "https://api.example.test",
        "DATABASE_URL": (
            f"postgres://my_project:{postgres_password}@postgres:5432/my_project"
        ),
        "DEFAULT_FROM_EMAIL": "noreply@example.test",
        "DJANGO_ENV": "prod",
{%- if cookiecutter.email_provider == "smtp" %}
        "EMAIL_HOST": "smtp.example.test",
{%- endif %}
        "POSTGRES_PASSWORD": postgres_password,
        "REDIS_PASSWORD": redis_password,
{%- if cookiecutter.email_provider == "resend" %}
        "RESEND_API_KEY": f"re_{faker.pystr(min_chars=24, max_chars=24)}",
{%- endif %}
        "SECRET_KEY": faker.bothify(text="mock-secret-key-????????-########-????????"),
        "SENTRY_DSN": f"https://{sentry_key}@sentry.example.test/1",
    }


def _import_prod_settings(
    faker: Faker,
    overrides: dict[str, str],
) -> subprocess.CompletedProcess[str]:
    return _run_prod_settings_script(faker, overrides, "import config.settings")


def _run_prod_settings_script(
    faker: Faker,
    overrides: dict[str, str],
    script: str,
) -> subprocess.CompletedProcess[str]:
    env = os.environ | _base_prod_env(faker) | overrides
    env["PYTHONPATH"] = "src"

    return subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True,
        check=False,
        env=env,
        text=True,
    )
