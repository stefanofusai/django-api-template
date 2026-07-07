from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ninja.testing import TestClient
    from ninja.testing.client import NinjaResponse

    from apps.core.models import User


class AuthenticatedTestClient:
    def __init__(self, client: TestClient, user: User) -> None:
        self._client = client
        self.user = user

    def delete(self, path: str) -> NinjaResponse:
        return self._client.delete(path, user=self.user)

    def get(
        self, path: str, query_params: dict[str, object] | None = None
    ) -> NinjaResponse:
        return self._client.get(path, query_params=query_params, user=self.user)

    def patch(self, path: str, json: dict[str, object] | None = None) -> NinjaResponse:
        return self._client.patch(path, json=json, user=self.user)

    def post(self, path: str, json: dict[str, object] | None = None) -> NinjaResponse:
        return self._client.post(path, json=json, user=self.user)

    def put(self, path: str, json: dict[str, object] | None = None) -> NinjaResponse:
        return self._client.put(path, json=json, user=self.user)
