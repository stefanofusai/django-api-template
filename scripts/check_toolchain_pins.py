"""Check that root and generated-project toolchain pins stay synchronized."""

import re
import subprocess
import sys
import tomllib
from pathlib import Path


CONTRACT_PATHS = (
    Path(".github/workflows/ci.yaml"),
    Path(".pre-commit-config.yaml"),
    Path("CONTRIBUTING.md"),
    Path("README.md"),
    Path("hooks/post_gen_project.py"),
    Path("pyproject.toml"),
    Path("scripts/check_generated_format.py"),
    Path("uv.lock"),
    Path("{{cookiecutter.project_slug}}/.docker/Dockerfile"),
    Path("{{cookiecutter.project_slug}}/.pre-commit-config.yaml"),
    Path("{{cookiecutter.project_slug}}/pyproject.toml"),
)
ROOT = Path(__file__).resolve().parent.parent


def check_contract(root: Path = ROOT, *, check_lock: bool = True) -> list[str]:
    """Return actionable failures for every drifted toolchain surface."""
    failures = []
    root_pyproject_path = root / "pyproject.toml"
    root_pyproject = tomllib.loads(root_pyproject_path.read_text())
    required_version = root_pyproject["tool"]["uv"]["required-version"]
    version_match = re.fullmatch(
        r">=(?P<minimum>\d+\.\d+\.\d+),<(?P<maximum>\d+\.\d+\.\d+)",
        required_version,
    )

    if version_match is None or not _is_minor_series_range(version_match):
        failures.append(
            "pyproject.toml: expected a bounded uv minor-series requirement, found "
            f"{required_version!r}"
        )
        return failures

    uv_version = version_match.group("minimum")
    expected_dependencies = {
        "cookiecutter==2.7.1",
        "pre-commit==4.6.0",
        "pytest==9.1.1",
    }
    actual_dependencies = set(root_pyproject["dependency-groups"]["dev"])

    if actual_dependencies != expected_dependencies:
        failures.append(
            "pyproject.toml: expected exact root tools "
            f"{sorted(expected_dependencies)}, found {sorted(actual_dependencies)}"
        )

    for dependency in actual_dependencies:
        if re.fullmatch(r"[A-Za-z0-9_.-]+==[^=]+", dependency) is None:
            failures.append(
                f"pyproject.toml: root development dependency must use ==: {dependency}"
            )

    post_gen_hook_path = root / "hooks/post_gen_project.py"
    post_gen_version = _single_match(
        post_gen_hook_path,
        r'^UV_VERSION = "(?P<version>[^\"]+)"$',
    )
    _compare_version(
        failures,
        post_gen_hook_path.relative_to(root),
        uv_version,
        post_gen_version,
    )

    generated_pyproject_path = root / "{{cookiecutter.project_slug}}/pyproject.toml"
    generated_version = _single_match(
        generated_pyproject_path,
        r'^required-version = "(?P<version>[^\"]+)"$',
    )
    _compare_version(
        failures,
        generated_pyproject_path.relative_to(root),
        required_version,
        generated_version,
    )

    dockerfile_path = root / "{{cookiecutter.project_slug}}/.docker/Dockerfile"
    docker_version = _single_match(
        dockerfile_path,
        r"ghcr\.io/astral-sh/uv:(?P<version>[^\s/]+)",
    )
    _compare_version(
        failures,
        dockerfile_path.relative_to(root),
        uv_version,
        docker_version,
    )

    pre_commit_path = root / "{{cookiecutter.project_slug}}/.pre-commit-config.yaml"
    pre_commit_version = _single_match(
        pre_commit_path,
        r"repo: https://github\.com/astral-sh/uv-pre-commit\s+"
        r"rev: v?(?P<version>[^\s]+)",
    )
    _compare_version(
        failures,
        pre_commit_path.relative_to(root),
        uv_version,
        pre_commit_version,
    )

    for path in (
        Path(".github/workflows/ci.yaml"),
        Path(".pre-commit-config.yaml"),
        Path("CONTRIBUTING.md"),
        Path("README.md"),
        Path("scripts/check_generated_format.py"),
    ):
        text = (root / path).read_text()

        for floating_command in (
            "uvx cookiecutter",
            "uvx pre-commit",
            "uvx pytest",
        ):
            if floating_command in text:
                failures.append(
                    f"{path}: contains an unversioned {floating_command} command"
                )

    readme_text = (root / "README.md").read_text()

    if (
        "uvx --from=cookiecutter==2.7.1 cookiecutter" not in readme_text
        and "uvx cookiecutter" not in readme_text
    ):
        failures.append("README.md: missing exact Cookiecutter 2.7.1 selector")

    if check_lock:
        failures.extend(_setup_uv_failures(root))
        lock_result = subprocess.run(
            ["uv", "lock", "--check"],
            cwd=root,
            capture_output=True,
            check=False,
            text=True,
        )

        if lock_result.returncode != 0:
            failures.append("uv.lock: does not match pyproject.toml")

    return failures


def main() -> int:
    """Print failures and return non-zero when the contract has drifted."""
    failures = check_contract()

    if failures:
        sys.stderr.write("\n".join(failures) + "\n")
        return 1

    print("toolchain pins agree")
    return 0


# Utils


def _compare_version(
    failures: list[str],
    path: Path,
    expected: str,
    actual: str,
) -> None:
    if actual != expected:
        failures.append(f"{path}: expected uv {expected}, found {actual}")


def _is_minor_series_range(version_match: re.Match[str]) -> bool:
    minimum = tuple(int(part) for part in version_match.group("minimum").split("."))
    maximum = tuple(int(part) for part in version_match.group("maximum").split("."))

    return maximum == (minimum[0], minimum[1] + 1, 0)


def _single_match(path: Path, pattern: str) -> str:
    matches = re.findall(pattern, path.read_text(), flags=re.MULTILINE)

    if len(matches) != 1:
        return f"{len(matches)} matching pins"

    return matches[0]


def _setup_uv_failures(root: Path) -> list[str]:
    failures = []
    workflow_roots = (
        root / ".github/workflows",
        root / "{{cookiecutter.project_slug}}/.github/workflows",
    )

    for workflow_root in workflow_roots:
        for workflow_path in workflow_root.glob("*.yaml"):
            text = workflow_path.read_text()

            if "uses: astral-sh/setup-uv@" not in text:
                continue

            setup_blocks = re.findall(
                r"uses: astral-sh/setup-uv@[^\n]+(?:\n {8,}[^\n]+)*",
                text,
            )

            if any(re.search(r"\n\s+version:", block) for block in setup_blocks):
                failures.append(
                    f"{workflow_path.relative_to(root)}: setup-uv must discover "
                    "the required version from pyproject.toml"
                )

    return failures


if __name__ == "__main__":
    sys.exit(main())
