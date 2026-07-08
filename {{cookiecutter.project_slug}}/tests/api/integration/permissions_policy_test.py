from typing import TYPE_CHECKING

from django.conf import settings

if TYPE_CHECKING:
    from django.test import Client


def test_responses_carry_permissions_policy_header(client: Client) -> None:
    response = client.get("/api/health")
    policy = response.headers["Permissions-Policy"]
    directives = [directive.strip() for directive in policy.split(",")]
    expected_directives = {f"{name}=()" for name in settings.PERMISSIONS_POLICY}

    assert len(directives) == len(expected_directives)
    assert set(directives) == expected_directives
