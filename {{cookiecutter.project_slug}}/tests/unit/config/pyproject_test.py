import importlib
import sys
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from pyproject_parser import PyProject

from config.pyproject import project_metadata, project_name, project_version, pyproject


def test_pyproject_loads_project_metadata_with_parser() -> None:
    assert isinstance(pyproject, PyProject)
    assert project_metadata == pyproject.project
    assert project_name == project_metadata["name"]
    assert project_version == project_metadata["version"]


def test_pyproject_raises_when_project_metadata_is_missing() -> None:
    parsed_pyproject = SimpleNamespace(project=None)

    try:
        with patch("pyproject_parser.PyProject.load", return_value=parsed_pyproject):
            sys.modules.pop("config.pyproject", None)

            with pytest.raises(RuntimeError, match=r"\[project\] metadata"):
                importlib.import_module("config.pyproject")

    finally:
        _restore_pyproject_module()


def test_pyproject_raises_when_project_version_is_missing() -> None:
    parsed_pyproject = SimpleNamespace(project={"name": "example", "version": None})

    try:
        with patch("pyproject_parser.PyProject.load", return_value=parsed_pyproject):
            sys.modules.pop("config.pyproject", None)

            with pytest.raises(RuntimeError, match=r"project\.version"):
                importlib.import_module("config.pyproject")

    finally:
        _restore_pyproject_module()


# Utils


def _restore_pyproject_module() -> None:
    sys.modules.pop("config.pyproject", None)
    importlib.import_module("config.pyproject")
