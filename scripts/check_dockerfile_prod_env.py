from pathlib import Path


DOCKERFILE_PATH = Path("{{cookiecutter.project_slug}}/.docker/Dockerfile")
PROD_SETTINGS_PATH = Path(
    "{{cookiecutter.project_slug}}/src/config/settings/environments/prod.py",
)


def check(dockerfile: str, prod_settings: str) -> list[str]:
    """Return human-readable problems; empty list means the check passes."""
    required_env = []

    if 'env("POSTGRES_PASSWORD")' in prod_settings:
        required_env.append("POSTGRES_PASSWORD=mock-postgres-password")

    if 'env("REDIS_PASSWORD")' in prod_settings:
        required_env.extend(
            [
                "CACHE_URL=rediscache://:mock-redis-password@localhost:6379/0",
                "REDIS_PASSWORD=mock-redis-password",
            ],
        )

    if 'env("CELERY_BROKER_URL")' in prod_settings:
        required_env.append(
            "CELERY_BROKER_URL=redis://:mock-redis-password@localhost:6379/1"
        )

    if not required_env:
        return [
            f"{PROD_SETTINGS_PATH}: no known env(...) accesses found; "
            "check_dockerfile_prod_env.py's detection is stale - update it",
        ]

    return [
        f"{DOCKERFILE_PATH}: collectstatic build env is missing {env}"
        for env in required_env
        if env not in dockerfile
    ]


def main() -> int:
    problems = check(DOCKERFILE_PATH.read_text(), PROD_SETTINGS_PATH.read_text())

    for problem in problems:
        print(problem)

    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
