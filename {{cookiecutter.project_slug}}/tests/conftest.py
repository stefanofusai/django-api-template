from collections.abc import Iterator
{%- if cookiecutter.use_example_api == "yes" or cookiecutter.use_celery != "none" %}
from typing import TYPE_CHECKING
{%- endif %}

import pytest
from django.core.cache import cache
from hypothesis import settings as hypothesis_settings
from ninja.testing import TestClient
from pytest_factoryboy import register
from zeal import zeal_context

from apps.api.api import internal_api, v1_api
from tests.factories import {% if cookiecutter.use_example_api == "yes" and cookiecutter.api_auth == "token" %}NoteFactory, TokenFactory, UserFactory{% elif cookiecutter.use_example_api == "yes" %}NoteFactory, UserFactory{% else %}UserFactory{% endif %}
{%- if cookiecutter.use_example_api == "yes" %}
from tests.utils import AuthenticatedTestClient
{%- endif %}
{%- if cookiecutter.use_example_api == "yes" or cookiecutter.use_celery != "none" %}

if TYPE_CHECKING:
    {%- if cookiecutter.use_celery != "none" and cookiecutter.use_example_api == "yes" %}
    from pytest_mock import MockerFixture

    from apps.core.models import User
    {%- elif cookiecutter.use_celery != "none" %}
    from pytest_mock import MockerFixture
    {%- elif cookiecutter.use_example_api == "yes" %}
    from apps.core.models import User
    {%- endif %}
{%- endif %}


TEST_TYPE_MARKERS = {
    "integration": pytest.mark.integration,
    "unit": pytest.mark.unit,
}


# Cold database connections can exceed Hypothesis' default deadline under xdist.
hypothesis_settings.register_profile("ci", deadline=None, max_examples=50)
hypothesis_settings.load_profile("ci")

register(UserFactory)
{%- if cookiecutter.use_example_api == "yes" %}
register(NoteFactory)
{%- endif %}
{%- if cookiecutter.use_example_api == "yes" and cookiecutter.api_auth == "token" %}
register(TokenFactory)
{%- endif %}


# Fixtures


@pytest.fixture(autouse=True)
def _clear_cache() -> None:
    # Throttle counters, axes lockouts, and readiness keys share the
    # Django cache; clear it so no test sees a neighbor's state.
    cache.clear()


@pytest.fixture(autouse=True)
def _zeal(request: pytest.FixtureRequest) -> Iterator[None]:
    # Schemathesis re-invokes the request-handling code path many times per
    # Hypothesis example within a single test function; the fixture's
    # per-test-function detection window then aggregates those unrelated,
    # per-request queries into one false N+1 site. Skip detection for the
    # contract test — determinism beats coverage here.
    if request.node.path.name == "schema_test.py":
        yield
        return

    with zeal_context():
        yield


{% if cookiecutter.use_celery != "none" -%}
@pytest.fixture(autouse=True)
def _broker_ready_default(mocker: MockerFixture) -> None:
    # The broker is unreachable in the test environment (no CELERY_BROKER_URL
    # is configured), so default every test to a healthy broker; tests that
    # care about broker state override this patch in their own body.
    mocker.patch("apps.api.routes.ready._broker_ready", return_value=True)


{% endif -%}
{% if cookiecutter.use_example_api == "yes" -%}
@pytest.fixture
def authenticated_v1_api_client(
    v1_api_client: TestClient, user: User
) -> AuthenticatedTestClient:
    return AuthenticatedTestClient(v1_api_client, user)


{% endif -%}
@pytest.fixture
def internal_api_client() -> TestClient:
    return TestClient(internal_api)


@pytest.fixture
def v1_api_client() -> TestClient:
    return TestClient(v1_api)


# Hooks


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    for item in items:
        segments = item.nodeid.split("/")

        for segment, marker in TEST_TYPE_MARKERS.items():
            if segment in segments:
                item.add_marker(marker)
