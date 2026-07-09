from typing import TYPE_CHECKING

from django.urls import reverse

if TYPE_CHECKING:
    from django.test import Client

EXPECTED_CSP = (
    "default-src 'self'; img-src 'self' data:; "
    "script-src 'self' 'unsafe-eval'; style-src 'self' 'unsafe-inline'"
)


def test_admin_login_returns_content_security_policy(client: Client) -> None:
    response = client.get("/admin/login/")

    assert response.headers["Content-Security-Policy"] == EXPECTED_CSP


def test_api_docs_return_content_security_policy(client: Client) -> None:
    response = client.get(reverse("internal:openapi-view"))

    assert response.headers["Content-Security-Policy"] == EXPECTED_CSP
