{% if cookiecutter.use_example_api == "yes" -%}
from typing import TYPE_CHECKING

{% endif -%}
import pytest
import schemathesis
{% if cookiecutter.use_example_api == "yes" and cookiecutter.api_auth == "session" -%}
from django.conf import settings
from django.test import Client
{% endif -%}
from schemathesis import Case, CheckFunction
from schemathesis.checks import CHECKS, load_all_checks
{% if cookiecutter.use_example_api == "yes" and cookiecutter.api_auth == "token" %}
from apps.core.models import Token
{% endif %}
# Production serves ASGI (config.asgi), but the OpenAPI schema is identical
# under either protocol and Schemathesis' ASGI transport runs the ASGI
# lifespan protocol, which Django's ASGIHandler rejects. Load the WSGI app
# for the contract test.
from config.wsgi import application
{% if cookiecutter.use_example_api == "yes" %}
if TYPE_CHECKING:
    from apps.core.models import User
    from tests.factories import NoteFactory
{% endif %}
OPENAPI_CONTRACT_CHECK_NAMES = (
    "content_type_conformance",
    "not_a_server_error",
    "response_schema_conformance",
    "status_code_conformance",
)

load_all_checks()

OPENAPI_CONTRACT_CHECKS: list[CheckFunction] = CHECKS.get_by_names(
    OPENAPI_CONTRACT_CHECK_NAMES
)
{% if cookiecutter.use_example_api == "yes" %}

@pytest.fixture(params=["/api/openapi.json", "/api/v1/openapi.json"])
def api_schema(request: pytest.FixtureRequest) -> object:
    return schemathesis.openapi.from_wsgi(
        request.param,
        application,
    )
{%- else %}

@pytest.fixture
def api_schema() -> object:
    return schemathesis.openapi.from_wsgi(
        "/api/openapi.json",
        application,
    )
{%- endif %}


schema = schemathesis.pytest.from_fixture("api_schema")
{% if cookiecutter.use_example_api == "yes" %}

@pytest.fixture
def authenticated_schema_headers(
    note_factory: type[NoteFactory],
    user: User,
) -> dict[str, str]:
    note_factory.create(body="Contract body", owner=user, title="Contract note")
    {%- if cookiecutter.api_auth == "token" %}
    raw_token, _ = Token.issue(name="contract test token", user=user)

    return {
        "Authorization": f"Bearer {raw_token}",
    }
    {%- else %}
    client = Client()
    client.force_login(user)
    session_cookie = client.cookies[settings.SESSION_COOKIE_NAME].value

    return {
        "Cookie": f"{settings.SESSION_COOKIE_NAME}={session_cookie}",
    }
    {%- endif %}
{%- endif %}
{% if cookiecutter.use_example_api == "yes" %}

# transaction=True avoids Django's request_finished signal closing the
# connection mid-test: Hypothesis calls the WSGI app many times per test, and
# the notes routes run real queries (session lookup) unlike the probes below.
@pytest.mark.django_db(transaction=True)
{%- else %}
@pytest.mark.django_db
{%- endif %}
@schema.parametrize()
def test_api_schema_conforms_to_openapi_contract_when_anonymous(case: Case) -> None:
    case.call_and_validate(checks=OPENAPI_CONTRACT_CHECKS)
{%- if cookiecutter.use_example_api == "yes" %}


# transaction=True avoids Django's request_finished signal closing the
# connection mid-test: Hypothesis calls the WSGI app many times per test, and
# the notes routes run real queries (session lookup) unlike the probes below.
@pytest.mark.django_db(transaction=True)
@schema.parametrize()
def test_api_schema_conforms_to_openapi_contract_when_authenticated(
    authenticated_schema_headers: dict[str, str],
    case: Case,
) -> None:
    if case.method.upper() == "GET" and case.path == "/api/v1/notes":
        case.query = {"limit": 1, "offset": 0}

    case.call_and_validate(
        checks=OPENAPI_CONTRACT_CHECKS,
        headers=authenticated_schema_headers,
    )
{%- endif %}
{%- if cookiecutter.use_example_api == "no" %}


# The v1 API exposes zero routes until the first business endpoint is added,
# so schemathesis has no operations to parametrize against
# `/api/v1/openapi.json` (`schema.parametrize()` fails outright with "does not
# match any API operations" rather than skipping). Assert the empty schema is
# still well-formed and served; fold this into the parametrized fixture above
# once v1 gains routes.
@pytest.mark.django_db
def test_v1_openapi_schema_is_well_formed_when_template_is_fresh() -> None:
    v1_schema = schemathesis.openapi.from_wsgi("/api/v1/openapi.json", application)

    assert v1_schema.raw_schema["info"]["version"] == "1.0.0"
    assert v1_schema.raw_schema["paths"] == {}
{%- endif %}
