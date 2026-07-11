import json
from pathlib import Path

import pytest
from jinja2 import Environment


ROOT = Path(__file__).resolve().parents[1]
PROD_COMPOSE = ROOT / "{{cookiecutter.project_slug}}/.docker/compose/prod.yaml"


@pytest.mark.parametrize(
    ("overrides", "expected"),
    [
        ({"postgres": "external", "redis": "external", "traefik_tls": "external", "use_s3_media": "yes", "use_traefik": "no"}, set()),
        ({"postgres": "external", "redis": "external", "traefik_tls": "external", "use_s3_media": "no", "use_traefik": "no"}, {"media_data"}),
        ({"postgres": "compose", "redis": "external", "traefik_tls": "external", "use_s3_media": "yes", "use_traefik": "no"}, {"postgres_data"}),
        ({"postgres": "external", "redis": "compose", "traefik_tls": "external", "use_s3_media": "yes", "use_traefik": "no"}, {"redis_data"}),
        ({"postgres": "external", "redis": "external", "traefik_tls": "letsencrypt", "use_s3_media": "yes", "use_traefik": "yes"}, {"traefik_data"}),
    ],
)
def test_volume_predicate_renders_exact_named_volumes(
    overrides: dict[str, str], expected: set[str]
) -> None:
    rendered = _render(**overrides)
    marker = "\nvolumes:\n"

    if not expected:
        assert marker not in rendered
        return

    section = rendered.split(marker, maxsplit=1)[1]
    names = {
        line.strip().removesuffix(":")
        for line in section.splitlines()
        if line.startswith("  ")
    }
    assert names == expected


def _render(**overrides: str) -> str:
    context = json.loads((ROOT / "cookiecutter.json").read_text())
    values = {
        key: value[0] if isinstance(value, list) else value
        for key, value in context.items()
        if not key.startswith("_")
    }
    values |= overrides
    values["project_slug"] = "my-project"
    return Environment(autoescape=False).from_string(PROD_COMPOSE.read_text()).render(
        cookiecutter=values
    )
