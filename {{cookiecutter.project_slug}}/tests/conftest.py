import pytest
from ninja.testing import TestClient

from apps.api.api import api

TEST_TYPE_MARKERS = {
    "tests/integration/": pytest.mark.integration,
    "tests/unit/": pytest.mark.unit,
}


# Fixtures


@pytest.fixture
def api_client() -> TestClient:
    return TestClient(api)


# Hooks


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    for item in items:
        for nodeid_prefix, marker in TEST_TYPE_MARKERS.items():
            if item.nodeid.startswith(nodeid_prefix):
                item.add_marker(marker)
