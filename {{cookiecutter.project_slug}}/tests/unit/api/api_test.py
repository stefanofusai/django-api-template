from apps.api.api import ops_api, v1_api
from config.pyproject import project_name


def test_ops_api_uses_project_name_in_operations_title() -> None:
    assert ops_api.title == f"{project_name} (operations)"


def test_v1_api_uses_project_name_and_contract_version() -> None:
    assert v1_api.title == project_name
    assert v1_api.version == "1.0.0"
