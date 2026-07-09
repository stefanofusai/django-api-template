from django.test import Client, override_settings


@override_settings(CORS_ALLOWED_ORIGINS=["https://app.example.test"])
def test_allowed_origin_receives_cors_allow_origin_header(client: Client) -> None:
    response = client.get(
        "/api/health",
        headers={"origin": "https://app.example.test"},
    )

    assert response.headers["access-control-allow-origin"] == "https://app.example.test"


@override_settings(CORS_ALLOWED_ORIGINS=["https://app.example.test"])
def test_disallowed_origin_does_not_receive_cors_allow_origin_header(
    client: Client,
) -> None:
    response = client.get(
        "/api/health",
        headers={"origin": "https://evil.example.test"},
    )

    assert "access-control-allow-origin" not in response.headers


@override_settings(CORS_ALLOWED_ORIGINS=["https://app.example.test"])
def test_options_preflight_receives_cors_headers_for_allowed_origin(
    client: Client,
) -> None:
    response = client.options(
        "/api/v1/",
        headers={
            "access-control-request-method": "GET",
            "origin": "https://app.example.test",
        },
    )

    assert response.headers["access-control-allow-origin"] == "https://app.example.test"
