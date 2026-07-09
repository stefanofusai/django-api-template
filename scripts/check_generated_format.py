"""Check that rendered projects pass the pinned ruff format and check."""

import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Optional

COMBOS = {
    "default": [],
    "maximal": [
        "use_example_api=yes",
        "api_auth=jwt",
        "api_throttling=basic",
        "use_cors=yes",
        "use_csp=yes",
    ],
    "minimal": [
        "use_example_api=no",
        "use_celery=none",
        "email_provider=none",
        "use_sentry=no",
        "use_s3_media=no",
        "use_traefik=no",
    ],
    "throttling-only": ["api_throttling=basic"],
    "smtp": ["email_provider=smtp"],
}
REPO_ROOT = Path(__file__).resolve().parent.parent
RUFF_PIN_PATTERN = re.compile(
    r"repo:\s*https://github\.com/astral-sh/ruff-pre-commit\s*\n\s*rev:\s*v?([^\s]+)",
)
RUFF_PRE_COMMIT_CONFIG = (
    REPO_ROOT / "{{cookiecutter.project_slug}}/.pre-commit-config.yaml"
)


def main() -> int:
    """Return non-zero when a rendered combo fails ruff format or check."""
    ruff_pin = _ruff_pin()
    failures = []

    for name, knobs in COMBOS.items():
        tmp_dir = tempfile.mkdtemp(prefix="check-generated-format-")

        try:
            project_dir = _bake(name, knobs, tmp_dir)

            if project_dir is None:
                failures.append(name)
                continue

            if _ruff(name, ruff_pin, project_dir, "format", "--check", "."):
                failures.append(name)
                continue

            if _ruff(name, ruff_pin, project_dir, "check", "--no-fix", "."):
                failures.append(name)
                continue

            print(f"PASS {name}")

        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)

    if failures:
        sys.stderr.write(f"generated-format failures: {failures}\n")
        return 1

    return 0


# Utils


def _bake(name: str, knobs: list[str], tmp_dir: str) -> Optional[Path]:
    result = subprocess.run(
        [
            "uvx",
            "cookiecutter",
            str(REPO_ROOT),
            "-o",
            tmp_dir,
            "--no-input",
            *knobs,
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    if result.returncode != 0:
        sys.stderr.write(f"{name}: bake failed\n{result.stdout}\n{result.stderr}\n")
        return None

    project_dirs = list(Path(tmp_dir).iterdir())

    if len(project_dirs) != 1:
        sys.stderr.write(
            f"{name}: expected exactly one baked project, found {project_dirs}\n"
        )
        return None

    return project_dirs[0]


def _ruff(name: str, pin: str, project_dir: Path, *args: str) -> bool:
    result = subprocess.run(
        ["uvx", f"ruff@{pin}", *args],
        cwd=project_dir,
        capture_output=True,
        text=True,
        check=False,
    )

    if result.returncode != 0:
        sys.stderr.write(
            f"{name}: ruff {' '.join(args)} failed\n{result.stdout}\n{result.stderr}\n"
        )
        return True

    return False


def _ruff_pin() -> str:
    matches = RUFF_PIN_PATTERN.findall(RUFF_PRE_COMMIT_CONFIG.read_text())

    if len(matches) != 1:
        sys.stderr.write(
            f"expected exactly one astral-sh/ruff-pre-commit rev in "
            f"{RUFF_PRE_COMMIT_CONFIG}, found {matches}\n",
        )
        sys.exit(1)

    return matches[0]


if __name__ == "__main__":
    sys.exit(main())
