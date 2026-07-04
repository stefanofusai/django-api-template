from ninja.conf import settings

from apps.api.pagination import BoundedLimitOffsetPagination


def test_bounded_limit_offset_pagination_uses_ninja_bounds() -> None:
    input_fields = BoundedLimitOffsetPagination.Input.model_fields

    limit_field = input_fields["limit"]
    offset_field = input_fields["offset"]

    assert limit_field.default == settings.PAGINATION_PER_PAGE
    assert limit_field.metadata[0].ge == 1
    assert limit_field.metadata[1].le == min(
        settings.PAGINATION_MAX_LIMIT,
        settings.PAGINATION_PER_PAGE,
    )
    assert offset_field.default == 0
    assert offset_field.metadata[0].ge == 0
    assert offset_field.metadata[1].le == settings.PAGINATION_MAX_OFFSET
