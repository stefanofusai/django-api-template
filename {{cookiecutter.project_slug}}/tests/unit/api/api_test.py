from apps.api.api import api
from config.pyproject import project_name, project_version


def test_api_uses_project_metadata_from_pyproject() -> None:
    assert api.title == project_name
    assert api.version == str(project_version)
