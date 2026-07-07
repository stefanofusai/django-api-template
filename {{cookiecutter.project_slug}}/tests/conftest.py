import pytest
from ninja.testing import TestClient
from pytest_factoryboy import register

from apps.api.api import internal_api, v1_api
from tests.factories import {% if cookiecutter.use_example_api == "yes" %}NoteFactory, UserFactory{% else %}UserFactory{% endif %}

TEST_TYPE_MARKERS = {
    "tests/integration/": pytest.mark.integration,
    "tests/unit/": pytest.mark.unit,
}

register(UserFactory)
{%- if cookiecutter.use_example_api == "yes" %}
register(NoteFactory)
{%- endif %}


# Fixtures


@pytest.fixture
def internal_api_client() -> TestClient:
    return TestClient(internal_api)


@pytest.fixture
def v1_api_client() -> TestClient:
    return TestClient(v1_api)


# Hooks


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    for item in items:
        for nodeid_prefix, marker in TEST_TYPE_MARKERS.items():
            if item.nodeid.startswith(nodeid_prefix):
                item.add_marker(marker)
