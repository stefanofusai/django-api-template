from typing import TYPE_CHECKING

import pytest
from ninja.testing import TestClient
from pytest_factoryboy import register

from apps.api.api import internal_api, v1_api
from tests.factories import {% if cookiecutter.use_example_api == "yes" %}NoteFactory, UserFactory{% else %}UserFactory{% endif %}
from tests.utils import AuthenticatedTestClient

if TYPE_CHECKING:
    from apps.core.models import User

TEST_TYPE_MARKERS = {
    "integration": pytest.mark.integration,
    "unit": pytest.mark.unit,
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


@pytest.fixture
def authenticated_v1_api_client(
    v1_api_client: TestClient, user: User
) -> AuthenticatedTestClient:
    return AuthenticatedTestClient(v1_api_client, user)


# Hooks


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    for item in items:
        segments = item.nodeid.split("/")

        for segment, marker in TEST_TYPE_MARKERS.items():
            if segment in segments:
                item.add_marker(marker)
