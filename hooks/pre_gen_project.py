import re
import sys

PROJECT_SLUG = "{{ cookiecutter.project_slug }}"
AUTHOR_EMAIL = "{{ cookiecutter.author_email }}"

SLUG_PATTERN = re.compile(r"^[a-z][a-z0-9]*(-[a-z0-9]+)*$")


def main() -> None:
    if not SLUG_PATTERN.fullmatch(PROJECT_SLUG):
        sys.exit(
            "project_slug must start with a lowercase letter and contain only "
            "lowercase letters, digits, and single hyphen separators."
        )

    if "@" not in AUTHOR_EMAIL:
        sys.exit("author_email must contain @.")


if __name__ == "__main__":
    main()
