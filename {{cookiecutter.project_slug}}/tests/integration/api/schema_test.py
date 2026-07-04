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
