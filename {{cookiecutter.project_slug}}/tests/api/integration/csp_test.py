from django.test import Client
from django.urls import reverse

EXPECTED_CSP_DIRECTIVES = [
    "default-src 'self'",
    "img-src 'self' data:",
    "script-src 'self' 'unsafe-inline'",
    "style-src 'self' 'unsafe-inline'",
]


def test_admin_login_returns_content_security_policy(client: Client) -> None:
    response = client.get("/admin/login/")

    assert _content_security_policy(response) is not None
    assert all(
        directive in _content_security_policy(response)
        for directive in EXPECTED_CSP_DIRECTIVES
    )


def test_api_docs_return_content_security_policy(client: Client) -> None:
    response = client.get(reverse("internal:openapi-view"))

    assert _content_security_policy(response) is not None
    assert all(
        directive in _content_security_policy(response)
        for directive in EXPECTED_CSP_DIRECTIVES
    )


# Utils


def _content_security_policy(response) -> str | None:
    return response.headers.get("Content-Security-Policy")
