import uuid

from django.db.models import QuerySet
from django.http import HttpRequest
from django.shortcuts import get_object_or_404
from ninja import Query, Status
{%- if cookiecutter.api_auth == "session" %}
from ninja.security import django_auth
{%- endif %}
from ninja_extra import (
    ControllerBase,
    api_controller,
    http_delete,
    http_get,
    http_post,
    http_put,
)
from ninja_extra.ordering import Ordering, ordering
from ninja_extra.pagination import paginate
from ninja_extra.schemas import NinjaPaginationResponseSchema
from ninja_extra.searching import Searching, searching

{% if cookiecutter.api_auth == "jwt" -%}
from apps.api.auth import jwt_auth
{% endif -%}
from apps.api.pagination import BoundedLimitOffsetPagination
from apps.api.schemas import ErrorSchema, ValidationErrorSchema
{% if cookiecutter.api_throttling == "basic" -%}
from apps.api.throttling import get_public_api_throttles
{% endif %}
from .models import Note
from .schemas import NoteFilterSchema, NoteInSchema, NoteOutSchema


class TotalOrdering(Ordering):
    def get_ordering(
        self, items: QuerySet[Note] | list[object], value: str | None
    ) -> list[str]:
        fields = super().get_ordering(items, value)

        if fields and not any(field.lstrip("-") == "id" for field in fields):
            fields.append("-id")

        return fields


@api_controller(
    "/notes",
    auth={% if cookiecutter.api_auth == "jwt" %}jwt_auth{% else %}django_auth{% endif %},
    tags=["notes"],
{%- if cookiecutter.api_throttling == "basic" %}
    throttle=get_public_api_throttles(),
{%- endif %}
    use_unique_op_id=False,
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
    @ordering(TotalOrdering, ordering_fields=["created_at", "title"])
    @searching(Searching, search_fields=["body", "title"])
    def list_notes(
        self, request: HttpRequest, filters: Query[NoteFilterSchema]
    ) -> QuerySet[Note]:
        return filters.filter(Note.objects.filter(owner=request.user))

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
