import math

from ninja import Field
from ninja.conf import settings
from ninja_extra.pagination import LimitOffsetPagination

# Ninja defaults PAGINATION_MAX_LIMIT to inf; fall back to the page size so the
# default stays bounded, while an explicit finite setting can raise the cap.
# Note: ninja's PAGINATION_MAX_OFFSET defaults to 100 — raise it via
# NINJA_PAGINATION_MAX_OFFSET when clients must page past the first ~200 rows.
PAGINATION_MAX_LIMIT = (
    settings.PAGINATION_PER_PAGE
    if math.isinf(settings.PAGINATION_MAX_LIMIT)
    else settings.PAGINATION_MAX_LIMIT
)


class BoundedLimitOffsetPagination(LimitOffsetPagination):
    class Input(LimitOffsetPagination.Input):
        limit: int = Field(
            settings.PAGINATION_PER_PAGE,
            ge=1,
            le=PAGINATION_MAX_LIMIT,
        )
        offset: int = Field(0, ge=0, le=settings.PAGINATION_MAX_OFFSET)
