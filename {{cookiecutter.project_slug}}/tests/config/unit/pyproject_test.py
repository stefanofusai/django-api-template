import importlib
import sys
from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest

from config.pyproject import project_metadata, project_name, project_version, pyproject

if TYPE_CHECKING:
    from faker import Faker


def test_pyproject_has_ninja_extra_only_for_enabled_features() -> None:
    dependencies = project_metadata["dependencies"]

    assert ("django-ninja-extra==0.31.5" in dependencies) is {{ cookiecutter.api_throttling == "basic" or cookiecutter.use_example_api == "yes" }}


def test_pyproject_loads_project_metadata_when_tomllib_is_available() -> None:
    assert isinstance(pyproject, dict)
    assert project_metadata == pyproject["project"]
    assert project_name == project_metadata["name"]
    assert project_version == project_metadata["version"]


def test_pyproject_raises_when_project_metadata_is_missing() -> None:
    try:
        with patch("tomllib.load", return_value={}):
            sys.modules.pop("config.pyproject", None)

            with pytest.raises(RuntimeError, match=r"\[project\] metadata"):
                importlib.import_module("config.pyproject")

    finally:
        _restore_pyproject_module()


def test_pyproject_raises_when_project_version_is_missing(faker: Faker) -> None:
    try:
        with patch("tomllib.load", return_value={"project": {"name": faker.slug()}}):
            sys.modules.pop("config.pyproject", None)

            with pytest.raises(RuntimeError, match=r"project\.version"):
                importlib.import_module("config.pyproject")

    finally:
        _restore_pyproject_module()


# Utils


def _restore_pyproject_module() -> None:
    sys.modules.pop("config.pyproject", None)
    importlib.import_module("config.pyproject")
