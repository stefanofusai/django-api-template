import pytest
from celery import shared_task

pytestmark = pytest.mark.django_db

EXPECTED_SUM = 5


@shared_task
def _add(x: int, y: int) -> int:
    return x + y


def test_shared_task_returns_result_when_executed_eagerly() -> None:
    result = _add.apply(kwargs={"x": 2, "y": 3})

    assert result.successful()
    assert result.get() == EXPECTED_SUM
