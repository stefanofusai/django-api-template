"""Check Postgres image pins agree across Compose and workflow files."""

import re
import sys
from pathlib import Path

CANONICAL = Path("{{cookiecutter.project_slug}}/.docker/compose/prod.yaml")
FILES = [
    Path("{{cookiecutter.project_slug}}/.docker/compose/ci-services.yaml"),
    Path("{{cookiecutter.project_slug}}/.docker/compose/dev.yaml"),
    Path("{{cookiecutter.project_slug}}/.github/workflows/migration-checks.yaml"),
    Path("{{cookiecutter.project_slug}}/.github/workflows/tests.yaml"),
    Path(".github/workflows/ci.yaml"),
]
PATTERN = re.compile(r"\bpostgres:(\d+\.\d+(?:\.\d+)?)\b")


def check(canonical_tags: set[str], file_tags: dict[Path, set[str]]) -> list[str]:
    """Return human-readable problems; empty list means the check passes."""
    if len(canonical_tags) != 1:
        return [
            f"expected exactly one postgres tag in {CANONICAL}, found {canonical_tags}",
        ]

    mismatches = [
        (path, tags) for path, tags in file_tags.items() if tags != canonical_tags
    ]

    if not mismatches:
        return []

    return [
        f"postgres image drift: canonical {canonical_tags} in {CANONICAL}",
        *[
            f"  {path}: {tags or 'NO postgres:<major.minor> tag found'}"
            for path, tags in mismatches
        ],
    ]


def main() -> int:
    """Return non-zero when Postgres image pins drift."""
    expected = _tags(CANONICAL)
    problems = check(expected, {path: _tags(path) for path in FILES})

    for problem in problems:
        sys.stderr.write(f"{problem}\n")

    return 1 if problems else 0


# Utils


def _tags(path: Path) -> set[str]:
    return set(PATTERN.findall(path.read_text()))


if __name__ == "__main__":
    sys.exit(main())
