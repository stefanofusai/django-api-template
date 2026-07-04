from ninja import Field
from ninja.conf import settings
from ninja.pagination import LimitOffsetPagination

PAGINATION_MAX_LIMIT = min(settings.PAGINATION_MAX_LIMIT, settings.PAGINATION_PER_PAGE)


class BoundedLimitOffsetPagination(LimitOffsetPagination):
    class Input(LimitOffsetPagination.Input):
        limit: int = Field(
            settings.PAGINATION_PER_PAGE,
            ge=1,
            le=PAGINATION_MAX_LIMIT,
        )
        offset: int = Field(0, ge=0, le=settings.PAGINATION_MAX_OFFSET)
