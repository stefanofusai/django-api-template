import uuid

from django.db.models import QuerySet
from django.http import HttpRequest
from django.shortcuts import get_object_or_404
from ninja import Status
from ninja_extra import (
    ControllerBase,
    api_controller,
    http_delete,
    http_get,
    http_post,
    http_put,
)
from ninja_extra.pagination import paginate
from ninja_extra.schemas import NinjaPaginationResponseSchema
{%- if cookiecutter.api_auth == "session" %}
from ninja.security import django_auth
{%- endif %}

{% if cookiecutter.api_auth == "token" -%}
from apps.api.auth import bearer_token_auth
{% endif -%}
from apps.api.pagination import BoundedLimitOffsetPagination
from apps.api.schemas import ErrorSchema, ValidationErrorSchema
{% if cookiecutter.api_throttling == "basic" -%}
from apps.api.throttling import get_public_api_throttles
{% endif %}
from .models import Note
from .schemas import NoteInSchema, NoteOutSchema


@api_controller(
    "/notes",
    auth={% if cookiecutter.api_auth == "token" %}bearer_token_auth{% else %}django_auth{% endif %},
    tags=["notes"],
{%- if cookiecutter.api_throttling == "basic" %}
    throttle=get_public_api_throttles(),
{%- endif %}
)
class NotesController(ControllerBase):
    @http_post(
        "",
        response={
            201: NoteOutSchema,
            400: ErrorSchema,
            401: ErrorSchema,
            403: ErrorSchema,
            422: ValidationErrorSchema,
        },
    )
    def create_note(self, request: HttpRequest, payload: NoteInSchema) -> Status[Note]:
        note = Note.objects.create(owner=request.user, **payload.dict())
        return Status(201, note)

    @http_delete(
        "/{note_id}",
        response={
            204: None,
            400: ErrorSchema,
            401: ErrorSchema,
            403: ErrorSchema,
            404: ErrorSchema,
            422: ValidationErrorSchema,
        },
    )
    def delete_note(self, request: HttpRequest, note_id: uuid.UUID) -> Status[None]:
        note = get_object_or_404(Note, id=note_id, owner=request.user)
        note.delete()
        return Status(204, None)

    @http_get(
        "/{note_id}",
        response={
            200: NoteOutSchema,
            400: ErrorSchema,
            401: ErrorSchema,
            404: ErrorSchema,
            422: ValidationErrorSchema,
        },
    )
    def get_note(self, request: HttpRequest, note_id: uuid.UUID) -> Note:
        return get_object_or_404(Note, id=note_id, owner=request.user)

    @http_get(
        "",
        response={
            200: NinjaPaginationResponseSchema[NoteOutSchema],
            401: ErrorSchema,
            422: ValidationErrorSchema,
        },
    )
    @paginate(BoundedLimitOffsetPagination)
    def list_notes(self, request: HttpRequest) -> QuerySet[Note]:
        return Note.objects.filter(owner=request.user)

    @http_put(
        "/{note_id}",
        response={
            200: NoteOutSchema,
            400: ErrorSchema,
            401: ErrorSchema,
            403: ErrorSchema,
            404: ErrorSchema,
            422: ValidationErrorSchema,
        },
    )
    def update_note(
        self, request: HttpRequest, note_id: uuid.UUID, payload: NoteInSchema
    ) -> Note:
        note = get_object_or_404(Note, id=note_id, owner=request.user)
        note.body = payload.body
        note.title = payload.title
        note.save()
        return note
