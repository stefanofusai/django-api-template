from pathlib import Path
import json
import re
import shutil
import subprocess

COMPOSE_MIN_VERSION = (5, 3, 0)
COMPOSE_VERSION_WARNING = (
    "WARNING: Docker Compose 5.3.0 or newer is required for the generated "
    "Compose files because they use pre_start lifecycle hooks"
)
GIT_INIT_WARNING = (
    "WARNING: git repository was not initialized; run git init "
    "--initial-branch=main manually"
)
MARKDOWN_FILES = [
    "AGENTS.md",
    "README.md",
]
POSTGRES = {{ cookiecutter.postgres | tojson }}
TRAEFIK_TLS = {{ cookiecutter.traefik_tls | tojson }}
USE_CELERY = {{ cookiecutter.use_celery | tojson }}
USE_EXAMPLE_API = {{ cookiecutter.use_example_api | tojson }}
USE_SENTRY = {{ cookiecutter.use_sentry | tojson }}
USE_TRAEFIK = {{ cookiecutter.use_traefik | tojson }}
UV_LOCK_WARNING = (
    "WARNING: uv.lock was not generated; CI, the ty hook, and uv-audit use "
    "--locked and will fail until you run uv lock"
)

REMOVED_DIRS = [
    *(
        [".agents/skills/django-celery-expert"]
        if USE_CELERY == "none"
        else []
    ),
    *(["src/apps/notes", "tests/notes"] if USE_EXAMPLE_API == "no" else []),
]
REMOVED_PATHS = [
    *(
        [
            ".docker/scripts/postgres-backup.sh",
            ".docker/scripts/postgres-restore.sh",
        ]
        if POSTGRES != "compose"
        else []
    ),
    *(
        [
            ".docker/scripts/celery-beat.sh",
            ".docker/scripts/celery-worker.sh",
            "src/config/celery.py",
            "src/config/settings/components/celery.py",
        ]
        if USE_CELERY == "none"
        else []
    ),
    *([".docker/scripts/celery-beat.sh"] if USE_CELERY == "worker" else []),
    *(
        ["src/apps/core/tasks.py", "tests/core/unit/tasks_test.py"]
        if USE_CELERY == "none"
        else []
    ),
    *(
        ["src/config/settings/components/sentry.py"]
        if USE_SENTRY == "no"
        else []
    ),
    *(
        [".docker/traefik-dynamic.yaml"]
        if not (USE_TRAEFIK == "yes" and TRAEFIK_TLS == "external")
        else []
    ),
]

def main() -> None:
    for removed_path in REMOVED_PATHS:
        Path(removed_path).unlink()

    for removed_dir in REMOVED_DIRS:
        shutil.rmtree(removed_dir)

    if USE_CELERY == "none":
        _prune_celery_skill_metadata()

    for markdown_file in MARKDOWN_FILES:
        path = Path(markdown_file)
        text = path.read_text()
        path.write_text(re.sub(r"\n{3,}", "\n\n", text))

    if shutil.which("git"):
        try:
            subprocess.run(
                ["git", "init", "--initial-branch=main"],
                check=True,
            )

        except (OSError, subprocess.CalledProcessError):
            print(GIT_INIT_WARNING)

    else:
        print(GIT_INIT_WARNING)

    if shutil.which("uv"):
        try:
            subprocess.run(["uv", "lock"], check=True)
        except subprocess.CalledProcessError:
            print(UV_LOCK_WARNING)
    else:
        print(UV_LOCK_WARNING)

    _warn_on_unsupported_compose()

    print(
        "\nNext steps:\n"
        "  uv sync --locked\n"
        "  cp .env.example .env\n"
        "  uv run pre-commit install --install-hooks\n"
        "  git add -A && git commit -m 'feat: initial project scaffold'\n"
    )


# Utils


def _parse_compose_version(output: str) -> tuple[int, int, int] | None:
    parts = re.findall(r"\d+", output)
    if not parts:
        return None

    version = [int(part) for part in parts[:3]]
    while len(version) < 3:
        version.append(0)

    return tuple(version)


def _prune_celery_skill_metadata() -> None:
    lock_path = Path("skills-lock.json")
    lock = json.loads(lock_path.read_text())
    lock["skills"].pop("django-celery-expert", None)
    lock_path.write_text(json.dumps(lock, indent=2) + "\n")

    readme_path = Path(".agents/README.md")
    lines = readme_path.read_text().splitlines(keepends=True)
    kept = [line for line in lines if "`django-celery-expert`:" not in line]
    readme_path.write_text("".join(kept))


def _warn_on_unsupported_compose() -> None:
    if not shutil.which("docker"):
        print(f"{COMPOSE_VERSION_WARNING}; docker was not found.")
        return

    try:
        result = subprocess.run(
            ["docker", "compose", "version", "--short"],
            capture_output=True,
            check=True,
            text=True,
        )

    except (OSError, subprocess.CalledProcessError):
        print(f"{COMPOSE_VERSION_WARNING}; docker compose version could not be checked.")
        return

    compose_version = _parse_compose_version(result.stdout)
    if compose_version is None:
        print(f"{COMPOSE_VERSION_WARNING}; docker compose version could not be parsed.")
        return

    if compose_version < COMPOSE_MIN_VERSION:
        version_text = ".".join(str(part) for part in compose_version)
        print(
            f"{COMPOSE_VERSION_WARNING}; detected Docker Compose "
            f"{version_text}."
        )


if __name__ == "__main__":
    main()
