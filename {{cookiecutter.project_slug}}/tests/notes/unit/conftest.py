import pytest
from ninja_extra.testing import TestClient

from apps.notes.controllers import NotesController


@pytest.fixture
def notes_controller_client() -> TestClient:
    return TestClient(NotesController)
