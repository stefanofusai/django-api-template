import json
from pathlib import Path

import pytest
from jinja2 import Environment


ROOT = Path(__file__).resolve().parents[1]
README_TEMPLATE = ROOT / "{{cookiecutter.project_slug}}/README.md"


@pytest.mark.parametrize(
    ("api_auth", "use_example_api", "expected"),
    [
        ("jwt", "yes", "example notes API uses JWT authentication"),
        ("session", "yes", "example notes API uses session authentication"),
        ("session", "no", "The API itself ships unauthenticated"),
    ],
)
def test_api_authentication_prose_matches_rendered_features(
    api_auth: str, use_example_api: str, expected: str
) -> None:
    rendered = _render(api_auth=api_auth, use_example_api=use_example_api)

    assert expected in rendered
    assert ("The API itself ships unauthenticated" in rendered) is (
        use_example_api == "no"
    )


@pytest.mark.parametrize(
    ("postgres", "redis"),
    [
        ("compose", "compose"),
        ("compose", "external"),
        ("external", "compose"),
        ("external", "external"),
    ],
)
def test_password_prose_matches_rendered_backing_services(
    postgres: str, redis: str
) -> None:
    rendered = _render(postgres=postgres, redis=redis)

    assert ("set a strong\n`POSTGRES_PASSWORD`" in rendered) is (postgres == "compose")
    assert ("Set a strong `REDIS_PASSWORD`" in rendered) is (redis == "compose")


def _render(**overrides: str) -> str:
    context = json.loads((ROOT / "cookiecutter.json").read_text())
    values = {
        key: value[0] if isinstance(value, list) else value
        for key, value in context.items()
        if not key.startswith("_")
    }
    values |= overrides
    values["project_slug"] = "my-project"

    return (
        Environment(autoescape=False)
        .from_string(README_TEMPLATE.read_text())
        .render(cookiecutter=values)
    )
