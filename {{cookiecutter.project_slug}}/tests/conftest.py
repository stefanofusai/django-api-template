from collections.abc import Iterator
{%- if cookiecutter.use_example_api == "yes" or cookiecutter.use_celery != "none" %}
from typing import TYPE_CHECKING
{%- endif %}

import pytest
from django.core.cache import cache
{% if cookiecutter.use_example_api == "yes" and cookiecutter.api_auth == "token" -%}
from django.utils import timezone
{% endif -%}
from hypothesis import settings as hypothesis_settings
from ninja.testing import TestClient
from pytest_factoryboy import {% if cookiecutter.use_example_api == "yes" and cookiecutter.api_auth == "token" %}LazyFixture, {% endif %}register
from zeal import zeal_context

from apps.api.api import internal_api, v1_api
{% if cookiecutter.use_example_api == "yes" and cookiecutter.api_auth == "token" -%}
from apps.core.models import Token
{% endif -%}
from tests.factories import {% if cookiecutter.use_example_api == "yes" and cookiecutter.api_auth == "token" %}TEST_TOKEN_SECRET, NoteFactory, TokenFactory, UserFactory{% elif cookiecutter.use_example_api == "yes" %}NoteFactory, UserFactory{% else %}UserFactory{% endif %}
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
{%- if cookiecutter.use_example_api == "yes" and cookiecutter.api_auth == "token" %}
register(TokenFactory)
register(TokenFactory, "auth_token", user=LazyFixture("user"))
{%- endif %}
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


{% if cookiecutter.use_celery != "none" -%}
@pytest.fixture(autouse=True)
def _broker_ready_default(mocker: MockerFixture) -> None:
    # The broker is unreachable in the test environment (no CELERY_BROKER_URL
    # is configured), so default every test to a healthy broker; tests that
    # care about broker state override this patch in their own body.
    mocker.patch("apps.api.routes.ready._broker_ready", return_value=True)


{% endif -%}
{% if cookiecutter.use_example_api == "yes" and cookiecutter.api_auth == "token" -%}
@pytest.fixture
def raw_token(token: Token) -> str:
    return f"pat_{token.prefix}_{TEST_TOKEN_SECRET}"


@pytest.fixture
def auth_raw_token(auth_token: Token) -> str:
    return f"pat_{auth_token.prefix}_{TEST_TOKEN_SECRET}"


@pytest.fixture
def token_auth_headers(auth_raw_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {auth_raw_token}"}


@pytest.fixture
def revoked_token(token: Token) -> Token:
    token.revoked_at = timezone.now()
    token.save(update_fields=("revoked_at",))
    return token


{% endif -%}
{% if cookiecutter.use_example_api == "yes" -%}
@pytest.fixture
def authenticated_v1_api_client(
    v1_api_client: TestClient,
    user: User,{% if cookiecutter.api_auth == "token" %}
    token_auth_headers: dict[str, str],{% endif %}
) -> AuthenticatedTestClient:
    {%- if cookiecutter.api_auth == "token" %}
    return AuthenticatedTestClient(v1_api_client, user, token_auth_headers)
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
