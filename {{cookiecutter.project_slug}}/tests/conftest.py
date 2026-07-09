from collections.abc import {% if cookiecutter.use_example_api == "yes" and cookiecutter.api_auth == "jwt" %}Callable, {% endif %}Iterator
from typing import TYPE_CHECKING

import pytest
from django.core.cache import cache
from hypothesis import settings as hypothesis_settings
from ninja.testing import TestClient
{% if cookiecutter.use_example_api == "yes" and cookiecutter.api_auth == "jwt" -%}
from ninja_jwt.tokens import RefreshToken
{% endif -%}
from pytest_factoryboy import register
from zeal import zeal_context

from apps.api.api import internal_api, v1_api
from tests.factories import {% if cookiecutter.use_example_api == "yes" %}NoteFactory, UserFactory{% else %}UserFactory{% endif %}
{%- if cookiecutter.use_example_api == "yes" %}
from tests.utils import AuthenticatedTestClient
{%- endif %}

if TYPE_CHECKING:
    from django.test import Client
    {%- if cookiecutter.use_celery != "none" %}
    from pytest_mock import MockerFixture
    {%- endif %}

    from apps.core.models import User

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


@pytest.fixture
def authenticated_client(client: Client, user: User) -> Client:
    client.force_login(user)
    return client


{% if cookiecutter.use_celery != "none" -%}
@pytest.fixture(autouse=True)
def _broker_ready_default(mocker: MockerFixture) -> None:
    # The broker is unreachable in the test environment (no CELERY_BROKER_URL
    # is configured), so default every test to a healthy broker; tests that
    # care about broker state override this patch in their own body.
    mocker.patch("apps.api.routes.ready._broker_ready", return_value=True)


{% endif -%}
{% if cookiecutter.use_example_api == "yes" and cookiecutter.api_auth == "jwt" -%}
@pytest.fixture
def jwt_auth_headers(
    user: User, jwt_auth_headers_for_user: Callable[[User], dict[str, str]]
) -> dict[str, str]:
    return jwt_auth_headers_for_user(user)


@pytest.fixture
def jwt_auth_headers_for_user() -> Callable[[User], dict[str, str]]:
    def make_auth_headers(user: User) -> dict[str, str]:
        refresh = RefreshToken.for_user(user)
        return {"Authorization": f"Bearer {refresh.access_token}"}  # ty: ignore[unresolved-attribute]

    return make_auth_headers


{% endif -%}
{% if cookiecutter.use_example_api == "yes" -%}
@pytest.fixture
def authenticated_v1_api_client(
    v1_api_client: TestClient,
    user: User,{% if cookiecutter.api_auth == "jwt" %}
    jwt_auth_headers: dict[str, str],{% endif %}
) -> AuthenticatedTestClient:
    {%- if cookiecutter.api_auth == "jwt" %}
    return AuthenticatedTestClient(v1_api_client, user, jwt_auth_headers)
    {%- else %}
    return AuthenticatedTestClient(v1_api_client, user)
    {%- endif %}


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
