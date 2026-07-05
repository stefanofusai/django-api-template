import re
import sys

AUTHOR_EMAIL = {{ cookiecutter.author_email | tojson }}
AUTHOR_NAME = {{ cookiecutter.author_name | tojson }}
DESCRIPTION = {{ cookiecutter.description | tojson }}
DOMAIN_NAME = {{ cookiecutter.domain_name | tojson }}
GITHUB_USERNAME = {{ cookiecutter.github_username | tojson }}
PROJECT_SLUG = {{ cookiecutter.project_slug | tojson }}

DOMAIN_NAME_PATTERN = re.compile(
    r"^[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?(\.[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?)+$"
)
EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
FORBIDDEN_CHARS_PATTERN = re.compile(r'["\\\n\r]')
GITHUB_USERNAME_PATTERN = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})$")
MAX_SLUG_LENGTH = 50
SLUG_PATTERN = re.compile(r"^[a-z][a-z0-9]*(-[a-z0-9]+)*$")


def main() -> None:
    if not SLUG_PATTERN.fullmatch(PROJECT_SLUG):
        sys.exit(
            "project_slug (derived from project_name unless set explicitly) "
            "must start with a lowercase letter and contain only lowercase "
            "letters, digits, and single hyphen separators."
        )

    if len(PROJECT_SLUG) > MAX_SLUG_LENGTH:
        sys.exit(
            "project_slug (derived from project_name unless set explicitly) "
            "must be 50 characters or fewer because Postgres identifiers "
            "derived from it are capped at 63 bytes."
        )

    if not EMAIL_PATTERN.fullmatch(AUTHOR_EMAIL):
        sys.exit("author_email must be a valid email address.")

    if FORBIDDEN_CHARS_PATTERN.search(AUTHOR_NAME):
        sys.exit(
            "author_name must not contain double quotes, backslashes, or "
            "newlines because it is written into pyproject.toml."
        )

    if FORBIDDEN_CHARS_PATTERN.search(DESCRIPTION):
        sys.exit(
            "description must not contain double quotes, backslashes, or "
            "newlines because it is written into pyproject.toml."
        )

    if not DOMAIN_NAME_PATTERN.fullmatch(DOMAIN_NAME):
        sys.exit(
            "domain_name must be a bare lowercase hostname such as "
            "api.example.com (no scheme, port, path, or trailing dot)."
        )

    if not GITHUB_USERNAME_PATTERN.fullmatch(GITHUB_USERNAME):
        sys.exit(
            "github_username must be a valid GitHub username because it is "
            "written into dependabot.yml."
        )


if __name__ == "__main__":
    main()
