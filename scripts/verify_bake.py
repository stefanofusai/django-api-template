import argparse
import shutil
import subprocess
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    args = _parse_args()
    output = args.output or Path(tempfile.mkdtemp(prefix="verify-bake-"))
    remove_output = args.output is None
    options = dict(args.option)
    project_slug = options.get(
        "project_slug",
        options.get("project_name", "My Project").lower().replace(" ", "-").replace("_", "-"),
    )
    project = output / project_slug
    compose = [
        "docker",
        "compose",
        "-f",
        ".docker/compose/dev.yaml",
        "--env-file=.env",
    ]
    succeeded = False

    try:
        _run(
            [
                "uv",
                "run",
                "--locked",
                "cookiecutter",
                ".",
                "-o",
                str(output),
                "--no-input",
                *(f"{key}={value}" for key, value in args.option),
            ],
            cwd=ROOT,
        )
        shutil.copyfile(project / ".env.example", project / ".env")
        _run([*compose, "up", "-d", "--wait", "postgres"], cwd=project)
        _run(["uv", "run", "pytest"], cwd=project)
        _run(["git", "add", "-A"], cwd=project)
        _run(["uv", "run", "pre-commit", "run", "--all-files"], cwd=project)
        succeeded = True

    finally:
        if project.exists():
            subprocess.run([*compose, "down", "-v"], check=False, cwd=project)

        if remove_output and succeeded:
            shutil.rmtree(output)

        elif not succeeded:
            print(f"Failed bake retained at {output}")


def _option(value: str) -> tuple[str, str]:
    key, separator, option_value = value.partition("=")

    if not separator or not key or not option_value:
        msg = "options must use non-empty key=value syntax"
        raise argparse.ArgumentTypeError(msg)

    return key, option_value


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Bake and verify the Django template.")
    parser.add_argument("--option", action="append", default=[], type=_option)
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


def _run(command: list[str], *, cwd: Path) -> None:
    subprocess.run(command, check=True, cwd=cwd)


if __name__ == "__main__":
    main()
