import uuid

from django.db.models import QuerySet
from django.http import HttpRequest
from django.shortcuts import get_object_or_404
from ninja import Router, Schema, Status
from ninja.pagination import paginate
from ninja.security import django_auth

from apps.api.pagination import BoundedLimitOffsetPagination

from .models import Note
from .schemas import NoteInSchema, NoteOutSchema

router = Router(auth=django_auth, tags=["notes"])


class ErrorSchema(Schema):
    detail: str


@router.post("", response={201: NoteOutSchema, 401: ErrorSchema, 403: ErrorSchema})
def create_note(request: HttpRequest, payload: NoteInSchema) -> Status[Note]:
    note = Note.objects.create(owner=request.user, **payload.dict())
    return Status(201, note)


@router.delete(
    "/{note_id}",
    response={204: None, 401: ErrorSchema, 403: ErrorSchema, 404: ErrorSchema},
)
def delete_note(request: HttpRequest, note_id: uuid.UUID) -> Status[None]:
    note = get_object_or_404(Note, id=note_id, owner=request.user)
    note.delete()
    return Status(204, None)


@router.get(
    "/{note_id}", response={200: NoteOutSchema, 401: ErrorSchema, 404: ErrorSchema}
)
def get_note(request: HttpRequest, note_id: uuid.UUID) -> Note:
    return get_object_or_404(Note, id=note_id, owner=request.user)


@router.get("", response={200: list[NoteOutSchema], 401: ErrorSchema})
@paginate(BoundedLimitOffsetPagination)
def list_notes(request: HttpRequest) -> QuerySet[Note]:
    return Note.objects.filter(owner=request.user)


@router.put(
    "/{note_id}",
    response={
        200: NoteOutSchema,
        401: ErrorSchema,
        403: ErrorSchema,
        404: ErrorSchema,
    },
)
def update_note(
    request: HttpRequest, note_id: uuid.UUID, payload: NoteInSchema
) -> Note:
    note = get_object_or_404(Note, id=note_id, owner=request.user)
    note.body = payload.body
    note.title = payload.title
    note.save()
    return note
