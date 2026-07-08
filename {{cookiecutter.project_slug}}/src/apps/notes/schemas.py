import uuid
from datetime import datetime
from typing import Annotated

from ninja import Field, FilterLookup, FilterSchema, Schema

NO_NUL_PATTERN = r"^[^\x00]*$"


class NoteFilterSchema(FilterSchema):
    title: Annotated[str | None, FilterLookup("title__icontains")] = None


class NoteInSchema(Schema):
    title: str = Field(pattern=NO_NUL_PATTERN)
    body: str = Field("", pattern=NO_NUL_PATTERN)


class NoteOutSchema(Schema):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    title: str
    body: str
