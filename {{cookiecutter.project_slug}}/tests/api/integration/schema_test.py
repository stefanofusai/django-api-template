import pytest
import schemathesis
from schemathesis import Case

# Production serves ASGI (config.asgi), but the OpenAPI schema is identical
# under either protocol and Schemathesis' ASGI transport runs the ASGI
# lifespan protocol, which Django's ASGIHandler rejects. Load the WSGI app
# for the contract test.
from config.wsgi import application
{%- if cookiecutter.use_example_api == "yes" %}


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


{% if cookiecutter.use_example_api == "yes" -%}
# transaction=True avoids Django's request_finished signal closing the
# connection mid-test: Hypothesis calls the WSGI app many times per test, and
# the notes routes run real queries (session lookup) unlike the probes below.
@pytest.mark.django_db(transaction=True)
{%- else -%}
@pytest.mark.django_db
{%- endif %}
@schema.parametrize()
def test_api_schema_conforms_to_openapi_contract(case: Case) -> None:
    case.call_and_validate()
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
