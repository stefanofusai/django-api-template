import tomllib
from pathlib import Path

PYPROJECT_PATH = Path(__file__).resolve().parent.parent.parent / "pyproject.toml"

with PYPROJECT_PATH.open("rb") as pyproject_file:
    pyproject = tomllib.load(pyproject_file)

project_metadata = pyproject.get("project")

if project_metadata is None:
    msg = "pyproject.toml must include [project] metadata."
    raise RuntimeError(msg)

project_name = project_metadata["name"]
project_version = project_metadata.get("version")

if project_version is None:
    msg = "pyproject.toml must include project.version."
    raise RuntimeError(msg)
