import importlib
from typing import TYPE_CHECKING

from ninja.conf import settings

from apps.api import pagination

if TYPE_CHECKING:
    from pytest_mock import MockerFixture

TEST_MAX_LIMIT = 500


def test_bounded_pagination_caps_limit_at_max_limit_when_setting_is_finite(
    mocker: MockerFixture,
) -> None:
    mocker.patch.object(settings, "PAGINATION_MAX_LIMIT", TEST_MAX_LIMIT)

    module = importlib.reload(pagination)

    try:
        assert module.PAGINATION_MAX_LIMIT == TEST_MAX_LIMIT

    finally:
        mocker.stopall()
        importlib.reload(pagination)


def test_bounded_pagination_caps_limit_at_per_page_when_max_limit_is_unset() -> None:
    input_fields = pagination.BoundedLimitOffsetPagination.Input.model_fields

    limit_field = input_fields["limit"]
    offset_field = input_fields["offset"]

    assert limit_field.default == settings.PAGINATION_PER_PAGE
    assert limit_field.metadata[0].ge == 1
    assert limit_field.metadata[1].le == settings.PAGINATION_PER_PAGE
    assert offset_field.default == 0
    assert offset_field.metadata[0].ge == 0
    assert offset_field.metadata[1].le == settings.PAGINATION_MAX_OFFSET
