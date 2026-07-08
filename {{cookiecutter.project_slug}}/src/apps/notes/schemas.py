import uuid
from datetime import datetime

from ninja import Field, Schema

NO_NUL_PATTERN = r"^[^\x00]*$"


class NoteInSchema(Schema):
    title: str = Field(pattern=NO_NUL_PATTERN)
    body: str = Field("", pattern=NO_NUL_PATTERN)


class NoteOutSchema(Schema):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    title: str
    body: str
