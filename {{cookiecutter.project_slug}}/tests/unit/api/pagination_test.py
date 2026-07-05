import importlib
import importlib.util
from types import ModuleType

import ninja.conf
from django.test import override_settings

from apps.api import pagination

TEST_MAX_LIMIT = 500


@override_settings(NINJA_PAGINATION_MAX_LIMIT=TEST_MAX_LIMIT)
def test_bounded_pagination_caps_limit_at_max_limit_when_setting_is_finite() -> None:
    importlib.reload(ninja.conf)
    spec = importlib.util.spec_from_file_location(
        "_pagination_with_finite_max_limit",
        pagination.__file__,
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert isinstance(module, ModuleType)

    assert module.PAGINATION_MAX_LIMIT == TEST_MAX_LIMIT
    limit_field = module.BoundedLimitOffsetPagination.Input.model_fields["limit"]

    assert limit_field.metadata[1].le == TEST_MAX_LIMIT


def test_bounded_pagination_caps_limit_at_per_page_when_max_limit_is_unset() -> None:
    input_fields = pagination.BoundedLimitOffsetPagination.Input.model_fields

    limit_field = input_fields["limit"]
    offset_field = input_fields["offset"]

    assert limit_field.default == pagination.settings.PAGINATION_PER_PAGE
    assert limit_field.metadata[0].ge == 1
    assert limit_field.metadata[1].le == pagination.settings.PAGINATION_PER_PAGE
    assert offset_field.default == 0
    assert offset_field.metadata[0].ge == 0
    assert offset_field.metadata[1].le == pagination.settings.PAGINATION_MAX_OFFSET
