"""Check Postgres image pins agree across Compose and workflow files."""

import re
import sys
from pathlib import Path

CANONICAL = Path("{{cookiecutter.project_slug}}/.docker/compose/prod.yaml")
FILES = [
    Path("{{cookiecutter.project_slug}}/.docker/compose/dev.yaml"),
    Path("{{cookiecutter.project_slug}}/.github/workflows/migration-checks.yaml"),
    Path("{{cookiecutter.project_slug}}/.github/workflows/tests.yaml"),
    Path(".github/workflows/ci.yaml"),
]
PATTERN = re.compile(r"\bpostgres:(\d+\.\d+(?:\.\d+)?)\b")


def main() -> int:
    """Return non-zero when Postgres image pins drift."""
    expected = _tags(CANONICAL)

    if len(expected) != 1:
        sys.stderr.write(
            f"expected exactly one postgres tag in {CANONICAL}, found {expected}\n",
        )
        return 1

    mismatches = [
        (path, tags) for path in FILES for tags in [_tags(path)] if tags != expected
    ]

    if mismatches:
        sys.stderr.write(f"postgres image drift: canonical {expected} in {CANONICAL}\n")

        for path, tags in mismatches:
            sys.stderr.write(
                f"  {path}: {tags or 'NO postgres:<major.minor> tag found'}\n",
            )

        return 1

    return 0


# Utils


def _tags(path: Path) -> set[str]:
    return set(PATTERN.findall(path.read_text()))


if __name__ == "__main__":
    sys.exit(main())
