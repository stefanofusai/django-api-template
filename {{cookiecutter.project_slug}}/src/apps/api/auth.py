from typing import TYPE_CHECKING

from ninja.errors import HttpError
from ninja.security import HttpBearer

from apps.core.models import Token, User

if TYPE_CHECKING:
    from django.http import HttpRequest


class BearerTokenAuth(HttpBearer):
    def authenticate(self, request: HttpRequest, token: str) -> User:
        stored_token = (
            Token.objects.select_related("user")
            .filter(digest=Token.hash(token))
            .first()
        )

        if stored_token is None:
            raise HttpError(401, "Invalid token")

        request.user = stored_token.user
        return stored_token.user


bearer_token_auth = BearerTokenAuth()
