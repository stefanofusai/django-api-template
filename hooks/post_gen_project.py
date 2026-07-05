from pathlib import Path
import re
import shutil
import subprocess

EMAIL_PROVIDER = {{ cookiecutter.email_provider | tojson }}
TRAEFIK_TLS = {{ cookiecutter.traefik_tls | tojson }}
USE_CELERY = {{ cookiecutter.use_celery | tojson }}
USE_SENTRY = {{ cookiecutter.use_sentry | tojson }}
USE_TRAEFIK = {{ cookiecutter.use_traefik | tojson }}

GIT_INIT_WARNING = (
    "WARNING: git repository was not initialized; run git init "
    "--initial-branch=main manually"
)
UV_LOCK_WARNING = (
    "WARNING: uv.lock was not generated; CI, the ty hook, and uv-audit use "
    "--locked and will fail until you run uv lock"
)
REMOVED_PATHS = [
    *(
        [
            ".docker/scripts/celery-beat.sh",
            ".docker/scripts/celery-worker.sh",
            "src/config/celery.py",
            "src/config/settings/components/celery.py",
            "tests/unit/config/celery_test.py",
        ]
        if USE_CELERY == "none"
        else []
    ),
    *([".docker/scripts/celery-beat.sh"] if USE_CELERY == "worker" else []),
    *(
        ["src/apps/core/tasks.py", "tests/unit/core/tasks_test.py"]
        if USE_CELERY == "none" or EMAIL_PROVIDER == "none"
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
MARKDOWN_FILES = [
    "AGENTS.md",
    "README.md",
]


def main() -> None:
    for removed_path in REMOVED_PATHS:
        Path(removed_path).unlink()

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

    print(
        "\nNext steps:\n"
        "  uv sync --locked\n"
        "  cp .env.example .env\n"
        "  uv run pre-commit install --install-hooks\n"
        "  git add -A && git commit -m 'feat: initial project scaffold'\n"
    )


if __name__ == "__main__":
    main()
