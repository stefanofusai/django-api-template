import shutil
import subprocess

GIT_INIT_WARNING = (
    "WARNING: git repository was not initialized; run git init "
    "--initial-branch=main manually"
)
UV_LOCK_WARNING = (
    "WARNING: uv.lock was not generated; CI, the ty hook, and uv-audit use "
    "--locked and will fail until you run uv lock"
)


def main() -> None:
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
