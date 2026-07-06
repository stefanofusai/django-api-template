import pytest
import schemathesis
from schemathesis import Case

from config.wsgi import application


@pytest.fixture
def api_schema() -> object:
    return schemathesis.openapi.from_wsgi(
        "/api/openapi.json",
        application,
    )


schema = schemathesis.pytest.from_fixture("api_schema")


@pytest.mark.django_db
@schema.parametrize()
def test_api_schema_conforms_to_openapi_contract(case: Case) -> None:
    case.call_and_validate()


# The v1 API currently exposes zero routes, so schemathesis has no operations
# to parametrize against `/api/v1/openapi.json` (`schema.parametrize()` fails
# the test outright with "does not match any API operations" rather than
# skipping). Once plan 009 adds v1 routes, fold this back into a single
# fixture parametrized over both `/api/openapi.json` and
# `/api/v1/openapi.json`, as the internal-API test above already exercises.
@pytest.mark.django_db
def test_v1_openapi_schema_loads_into_schemathesis_when_template_is_fresh() -> None:
    v1_schema = schemathesis.openapi.from_wsgi("/api/v1/openapi.json", application)

    assert v1_schema is not None
