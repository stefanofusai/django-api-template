"""Check the vendored agent skills match the hashes in skills-lock.json."""

import hashlib
import json
import sys
from pathlib import Path


LOCK_PATH = Path("{{cookiecutter.project_slug}}/skills-lock.json")
SKILLS_DIR = Path("{{cookiecutter.project_slug}}/.agents/skills")


def check(lock_text: str | None, actual_hashes: dict[str, str]) -> list[str]:
    """Return human-readable problems; empty list means the check passes."""
    if lock_text is None:
        return [f"{LOCK_PATH}: skills lock file is missing"]

    try:
        lock = json.loads(lock_text)
    except json.JSONDecodeError as exc:
        return [f"{LOCK_PATH}: skills lock is not valid JSON: {exc}"]

    skills = lock.get("skills") or {}
    if not skills:
        return [f"{LOCK_PATH}: skills lock records no skills"]

    problems = []

    for name, entry in sorted(skills.items()):
        actual = actual_hashes.get(name)

        if actual is None:
            problems.append(f"{SKILLS_DIR}/{name}/SKILL.md: vendored skill file is missing")
        elif actual != entry.get("computedHash"):
            problems.append(
                f"{SKILLS_DIR}/{name}/SKILL.md: hash {actual} does not match "
                f"{entry.get('computedHash')} recorded in {LOCK_PATH}",
            )

    return problems


def main() -> int:
    """Return non-zero when the vendored skills drift from the lock."""
    lock_text = LOCK_PATH.read_text() if LOCK_PATH.exists() else None
    actual_hashes = {
        path.parent.name: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(SKILLS_DIR.glob("*/SKILL.md"))
    }

    problems = check(lock_text, actual_hashes)

    for problem in problems:
        print(problem)

    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
