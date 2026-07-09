from datetime import UTC, datetime

from ninja import Field, Schema
from pydantic import field_validator

NO_NUL_PATTERN = r"^[^\x00]*$"


class TokenCreateSchema(Schema):
    name: str = Field(max_length=100, min_length=1, pattern=NO_NUL_PATTERN)
    expires_at: datetime | None = None

    @field_validator("expires_at")
    @classmethod
    def _normalize_expires_at_to_utc(cls, value: datetime | None) -> datetime | None:
        # Python's datetime (and Pydantic) accepts UTC offsets up to +/-24h,
        # but Postgres's timestamptz literal parser rejects offsets beyond
        # +/-15:59:59 ("time zone displacement out of range"). Normalize to
        # UTC here so no offset ever reaches the database.
        if value is None:
            return None

        try:
            return value.astimezone(UTC)
        except OverflowError as exc:
            # A value near datetime.min/max combined with an extreme offset
            # (e.g. year 9999 at -23:00) overflows on conversion to UTC.
            # Surface this as a validation error (422) rather than letting
            # OverflowError propagate into an unhandled 500.
            msg = "expires_at is out of range once normalized to UTC"
            raise ValueError(msg) from exc


class TokenOutSchema(Schema):
    id: int
    created_at: datetime
    expires_at: datetime | None
    last_used_at: datetime | None
    revoked_at: datetime | None
    name: str
    prefix: str


class TokenCreatedSchema(TokenOutSchema):
    token: str
