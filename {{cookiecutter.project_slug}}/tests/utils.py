from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ninja.testing import TestClient
    from ninja.testing.client import NinjaResponse

    from apps.core.models import User


class AuthenticatedTestClient:
    def __init__(
        self,
        client: TestClient,
        user: User,
        {%- if cookiecutter.use_example_api == "yes" and cookiecutter.api_auth == "token" %}
        headers: dict[str, str],
        {%- endif %}
    ) -> None:
        self._client = client
        self.user = user
{%- if cookiecutter.use_example_api == "yes" and cookiecutter.api_auth == "token" %}
        self._headers = headers
{%- endif %}

    def delete(self, path: str) -> NinjaResponse:
        {%- if cookiecutter.use_example_api == "yes" and cookiecutter.api_auth == "token" %}
        return self._client.delete(path, headers=self._headers)
        {%- else %}
        return self._client.delete(path, user=self.user)
        {%- endif %}

    def get(
        self, path: str, query_params: dict[str, object] | None = None
    ) -> NinjaResponse:
        {%- if cookiecutter.use_example_api == "yes" and cookiecutter.api_auth == "token" %}
        return self._client.get(path, headers=self._headers, query_params=query_params)
        {%- else %}
        return self._client.get(path, query_params=query_params, user=self.user)
        {%- endif %}

    def post(self, path: str, json: dict[str, object] | None = None) -> NinjaResponse:
        {%- if cookiecutter.use_example_api == "yes" and cookiecutter.api_auth == "token" %}
        return self._client.post(path, headers=self._headers, json=json)
        {%- else %}
        return self._client.post(path, json=json, user=self.user)
        {%- endif %}

    def put(self, path: str, json: dict[str, object] | None = None) -> NinjaResponse:
        {%- if cookiecutter.use_example_api == "yes" and cookiecutter.api_auth == "token" %}
        return self._client.put(path, headers=self._headers, json=json)
        {%- else %}
        return self._client.put(path, json=json, user=self.user)
        {%- endif %}
