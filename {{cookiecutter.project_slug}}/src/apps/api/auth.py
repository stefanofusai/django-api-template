from typing import TYPE_CHECKING

from ninja.errors import HttpError
from ninja.security import HttpBearer

from apps.core.models import Token, User

if TYPE_CHECKING:
    from django.http import HttpRequest


class BearerTokenAuth(HttpBearer):
    def authenticate(self, request: HttpRequest, token: str) -> User:
        prefix = Token.prefix_from(token)

        if prefix is None:
            raise HttpError(401, "Invalid token")

        stored_token = (
            Token.objects.select_related("user")
            .filter(digest=Token.hash(token), prefix=prefix)
            .first()
        )

        if stored_token is None or stored_token.is_expired():
            raise HttpError(401, "Invalid token")

        stored_token.mark_used()
        request.user = stored_token.user
        return stored_token.user


bearer_token_auth = BearerTokenAuth()
