import uuid
from datetime import datetime

from ninja import Schema


class NoteInSchema(Schema):
    title: str
    body: str = ""


class NoteOutSchema(Schema):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    title: str
    body: str
