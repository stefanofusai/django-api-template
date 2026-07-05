import pytest
from ninja.testing import TestClient
from pytest_factoryboy import register

from apps.api.api import ops_api, v1_api
from tests.factories import UserFactory

TEST_TYPE_MARKERS = {
    "tests/integration/": pytest.mark.integration,
    "tests/unit/": pytest.mark.unit,
}

register(UserFactory)


# Fixtures


@pytest.fixture
def api_client() -> TestClient:
    return TestClient(ops_api)


@pytest.fixture
def v1_client() -> TestClient:
    return TestClient(v1_api)


# Hooks


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    for item in items:
        for nodeid_prefix, marker in TEST_TYPE_MARKERS.items():
            if item.nodeid.startswith(nodeid_prefix):
                item.add_marker(marker)
