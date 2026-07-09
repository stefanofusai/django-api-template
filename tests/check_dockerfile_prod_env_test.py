import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts/check_dockerfile_prod_env.py"
SPEC = importlib.util.spec_from_file_location(
    "check_dockerfile_prod_env",
    SCRIPT_PATH,
)

if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"could not load {SCRIPT_PATH}")

check_dockerfile_prod_env = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(check_dockerfile_prod_env)


def test_matching_inputs_pass() -> None:
    dockerfile = """
POSTGRES_PASSWORD=mock-postgres-password
CACHE_URL=rediscache://:mock-redis-password@localhost:6379/0
REDIS_PASSWORD=mock-redis-password
CELERY_BROKER_URL=redis://:mock-redis-password@localhost:6379/1
"""
    prod_settings = """
env("POSTGRES_PASSWORD")
env("REDIS_PASSWORD")
env("CELERY_BROKER_URL")
"""

    assert check_dockerfile_prod_env.check(dockerfile, prod_settings) == []


def test_missing_env_reports_exact_line() -> None:
    dockerfile = """
POSTGRES_PASSWORD=mock-postgres-password
CACHE_URL=rediscache://:mock-redis-password@localhost:6379/0
CELERY_BROKER_URL=redis://:mock-redis-password@localhost:6379/1
"""
    prod_settings = """
env("POSTGRES_PASSWORD")
env("REDIS_PASSWORD")
env("CELERY_BROKER_URL")
"""

    assert check_dockerfile_prod_env.check(dockerfile, prod_settings) == [
        "{{cookiecutter.project_slug}}/.docker/Dockerfile: "
        "collectstatic build env is missing "
        "REDIS_PASSWORD=mock-redis-password",
    ]


def test_unrecognized_prod_settings_fail_closed() -> None:
    problems = check_dockerfile_prod_env.check(
        dockerfile="",
        prod_settings="SECRET_KEY = env('SECRET_KEY')",
    )

    assert len(problems) == 1
    assert "no known env(...) accesses found" in problems[0]
