from typing import TYPE_CHECKING

from django.urls import reverse

if TYPE_CHECKING:
    from django.test import Client

EXPECTED_CSP_DIRECTIVES = [
    "default-src 'self'",
    "img-src 'self' data:",
    "script-src 'self' 'unsafe-inline'",
    "style-src 'self' 'unsafe-inline'",
]


def test_admin_login_returns_content_security_policy(client: Client) -> None:
    response = client.get("/admin/login/")
    policy = response.headers["Content-Security-Policy"]

    assert all(directive in policy for directive in EXPECTED_CSP_DIRECTIVES)


def test_api_docs_return_content_security_policy(client: Client) -> None:
    response = client.get(reverse("internal:openapi-view"))
    policy = response.headers["Content-Security-Policy"]

    assert all(directive in policy for directive in EXPECTED_CSP_DIRECTIVES)
