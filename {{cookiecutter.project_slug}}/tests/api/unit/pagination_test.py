import importlib
import importlib.util
import math
from collections.abc import Iterator, Sequence
from types import ModuleType
from typing import Protocol, overload

import ninja.conf
import pytest
from annotated_types import Ge, Le
from django.test import override_settings

from apps.api import pagination

TEST_MAX_LIMIT = 500


@pytest.fixture
def finite_pagination_max_limit() -> Iterator[None]:
    try:
        with override_settings(NINJA_PAGINATION_MAX_LIMIT=TEST_MAX_LIMIT):
            importlib.reload(ninja.conf)
            yield
    finally:
        importlib.reload(ninja.conf)


@pytest.mark.usefixtures("finite_pagination_max_limit")
def test_bounded_pagination_caps_limit_at_max_limit_when_setting_is_finite() -> None:
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

    assert _constraint(limit_field, Le).le == TEST_MAX_LIMIT


def test_bounded_pagination_caps_limit_at_per_page_when_max_limit_is_unset() -> None:
    assert math.isinf(ninja.conf.settings.PAGINATION_MAX_LIMIT)

    input_fields = pagination.BoundedLimitOffsetPagination.Input.model_fields

    limit_field = input_fields["limit"]
    offset_field = input_fields["offset"]

    assert limit_field.default == pagination.settings.PAGINATION_PER_PAGE
    assert _constraint(limit_field, Ge).ge == 1
    assert _constraint(limit_field, Le).le == pagination.settings.PAGINATION_PER_PAGE
    assert offset_field.default == 0
    assert _constraint(offset_field, Ge).ge == 0
    assert _constraint(offset_field, Le).le == pagination.settings.PAGINATION_MAX_OFFSET


# Utils


class _FieldWithMetadata(Protocol):
    metadata: Sequence[object]


@overload
def _constraint(field: _FieldWithMetadata, kind: type[Ge]) -> Ge: ...


@overload
def _constraint(field: _FieldWithMetadata, kind: type[Le]) -> Le: ...


def _constraint(field: _FieldWithMetadata, kind: type[Ge | Le]) -> Ge | Le:
    return next(m for m in field.metadata if isinstance(m, kind))
