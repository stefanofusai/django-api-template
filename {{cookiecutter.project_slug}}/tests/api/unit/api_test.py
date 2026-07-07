from apps.api.api import internal_api, v1_api
from config.pyproject import project_name


def test_internal_api_uses_project_name_in_internal_title_when_created() -> None:
    assert internal_api.title == f"{project_name} (internal)"


def test_v1_api_uses_project_name_and_contract_version_when_created() -> None:
    assert v1_api.title == project_name
    assert v1_api.version == "1.0.0"
