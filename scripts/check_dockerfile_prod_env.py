from pathlib import Path


DOCKERFILE_PATH = Path("{{cookiecutter.project_slug}}/.docker/Dockerfile")
PROD_SETTINGS_PATH = Path(
    "{{cookiecutter.project_slug}}/src/config/settings/environments/prod.py",
)


def main() -> int:
    dockerfile = DOCKERFILE_PATH.read_text()
    prod_settings = PROD_SETTINGS_PATH.read_text()

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

    missing_env = [env for env in required_env if env not in dockerfile]

    if missing_env:
        for env in missing_env:
            print(f"{DOCKERFILE_PATH}: collectstatic build env is missing {env}")

        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
