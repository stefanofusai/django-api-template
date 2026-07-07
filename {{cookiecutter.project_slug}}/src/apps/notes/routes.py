import uuid

from django.db.models import QuerySet
from django.http import HttpRequest
from django.shortcuts import get_object_or_404
from ninja import Router, Status
from ninja.pagination import paginate
{%- if cookiecutter.api_auth == "session" %}
from ninja.security import django_auth
{%- endif %}

{% if cookiecutter.api_auth == "token" -%}
from apps.api.auth import bearer_token_auth
{% endif -%}
from apps.api.pagination import BoundedLimitOffsetPagination
from apps.api.schemas import ErrorSchema

from .models import Note
from .schemas import NoteInSchema, NoteOutSchema

{% if cookiecutter.api_auth == "token" -%}
router = Router(auth=bearer_token_auth, tags=["notes"])
{% else -%}
router = Router(auth=django_auth, tags=["notes"])
{% endif %}

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
