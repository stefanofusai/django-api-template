from typing import TYPE_CHECKING

import pytest
from ninja.testing import TestClient
from pytest_factoryboy import register

from apps.api.api import internal_api, v1_api
from tests.factories import {% if cookiecutter.use_example_api == "yes" %}NoteFactory, UserFactory{% else %}UserFactory{% endif %}

if TYPE_CHECKING:
    from ninja.testing.client import NinjaResponse

    from apps.core.models import User

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


@pytest.fixture
def authenticated_client(v1_api_client: TestClient, user: User) -> _AuthenticatedClient:
    return _AuthenticatedClient(v1_api_client, user)


# Hooks


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    for item in items:
        for nodeid_prefix, marker in TEST_TYPE_MARKERS.items():
            if item.nodeid.startswith(nodeid_prefix):
                item.add_marker(marker)


# Utils


class _AuthenticatedClient:
    def __init__(self, client: TestClient, user: User) -> None:
        self._client = client
        self.user = user

    def delete(self, path: str) -> NinjaResponse:
        return self._client.delete(path, user=self.user)

    def get(
        self, path: str, query_params: dict[str, object] | None = None
    ) -> NinjaResponse:
        return self._client.get(path, user=self.user, query_params=query_params)

    def post(self, path: str, json: dict[str, object] | None = None) -> NinjaResponse:
        return self._client.post(path, user=self.user, json=json)

    def put(self, path: str, json: dict[str, object] | None = None) -> NinjaResponse:
        return self._client.put(path, user=self.user, json=json)
