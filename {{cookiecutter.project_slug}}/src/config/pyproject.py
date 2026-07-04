from pyproject_parser import PyProject

pyproject = PyProject.load("pyproject.toml")
project_metadata = pyproject.project

if project_metadata is None:
    msg = "pyproject.toml must include [project] metadata."
    raise RuntimeError(msg)

project_name = project_metadata["name"]
project_version = project_metadata["version"]

if project_version is None:
    msg = "pyproject.toml must include project.version."
    raise RuntimeError(msg)
