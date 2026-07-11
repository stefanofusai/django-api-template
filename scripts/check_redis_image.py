"""Check Redis image pins agree across generated Compose files."""

import re
import sys
from pathlib import Path


CANONICAL = Path("{{cookiecutter.project_slug}}/.docker/compose/prod.yaml")
FILES = [
    Path("{{cookiecutter.project_slug}}/.docker/compose/ci-services.yaml"),
    Path("{{cookiecutter.project_slug}}/.docker/compose/dev.yaml"),
]
PATTERN = re.compile(r"\bredis:(\d+\.\d+(?:\.\d+)?)\b")


def check(canonical_tags: set[str], file_tags: dict[Path, set[str]]) -> list[str]:
    """Return actionable Redis image drift problems."""
    if len(canonical_tags) != 1:
        return [f"expected exactly one redis tag in {CANONICAL}, found {canonical_tags}"]

    mismatches = [
        (path, tags) for path, tags in file_tags.items() if tags != canonical_tags
    ]

    if not mismatches:
        return []

    return [
        f"redis image drift: canonical {canonical_tags} in {CANONICAL}",
        *[
            f"  {path}: {tags or 'NO redis:<major.minor> tag found'}"
            for path, tags in mismatches
        ],
    ]


def main() -> int:
    """Return non-zero when Redis image pins drift."""
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
