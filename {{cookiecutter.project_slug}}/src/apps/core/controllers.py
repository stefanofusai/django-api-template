from typing import cast

from django.db.models import QuerySet
from django.http import HttpRequest
from django.shortcuts import get_object_or_404
from django.utils import timezone
from ninja import Status
from ninja_extra import (
    ControllerBase,
    api_controller,
    http_delete,
    http_get,
    http_post,
)
from ninja_extra.pagination import paginate
from ninja_extra.schemas import NinjaPaginationResponseSchema

from apps.api.auth import bearer_token_auth
from apps.api.pagination import BoundedLimitOffsetPagination
from apps.api.schemas import ErrorSchema, ValidationErrorSchema

from .models import Token, User
from .schemas import TokenCreatedSchema, TokenCreateSchema, TokenOutSchema


@api_controller(
    "/tokens",
    auth=bearer_token_auth,
    tags=["tokens"],
    use_unique_op_id=False,
)
class TokensController(ControllerBase):
    @http_post(
        "",
        response={
            201: TokenCreatedSchema,
            400: ErrorSchema,
            401: ErrorSchema,
            422: ValidationErrorSchema,
        },
    )
    def create_token(
        self, request: HttpRequest, payload: TokenCreateSchema
    ) -> Status[TokenCreatedSchema]:
        user = cast("User", request.user)
        raw_token, token = Token.issue(
            expires_at=payload.expires_at,
            name=payload.name,
            user=user,
        )
        return Status(
            201,
            TokenCreatedSchema(
                id=token.pk,
                created_at=token.created_at,
                expires_at=token.expires_at,
                last_used_at=token.last_used_at,
                revoked_at=token.revoked_at,
                name=token.name,
                prefix=token.prefix,
                token=raw_token,
            ),
        )

    @http_delete(
        "/{token_id}",
        response={
            204: None,
            400: ErrorSchema,
            401: ErrorSchema,
            404: ErrorSchema,
            422: ValidationErrorSchema,
        },
    )
    def revoke_token(self, request: HttpRequest, token_id: int) -> Status[None]:
        token = get_object_or_404(
            Token, id=token_id, user=request.user, revoked_at__isnull=True
        )
        token.revoked_at = timezone.now()
        token.save(update_fields=("revoked_at",))
        return Status(204, None)

    @http_get(
        "",
        response={
            200: NinjaPaginationResponseSchema[TokenOutSchema],
            401: ErrorSchema,
            422: ValidationErrorSchema,
        },
    )
    @paginate(BoundedLimitOffsetPagination)
    def list_tokens(self, request: HttpRequest) -> QuerySet[Token]:
        return Token.objects.filter(user=request.user)
