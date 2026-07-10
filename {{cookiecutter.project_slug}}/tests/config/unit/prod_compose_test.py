from pathlib import Path

import yaml

PROD_COMPOSE = Path(".docker/compose/prod.yaml")


def test_api_container_healthcheck_remains_liveness() -> None:
    compose = yaml.safe_load(PROD_COMPOSE.read_text())

    assert compose["services"]["api"]["healthcheck"]["test"][-1] == (
        "http://127.0.0.1:8000/api/health"
    )
{% if cookiecutter.use_traefik == "yes" %}

def test_traefik_protects_readiness_with_exact_path_routers() -> None:
    labels = _api_labels()

    assert labels[
        "traefik.http.middlewares.ready-allowlist.ipallowlist.sourcerange"
    ] == ("127.0.0.0/8,::1/128")
    assert labels["traefik.http.routers.api-ready-web.entrypoints"] == "web"
    assert labels["traefik.http.routers.api-ready-web.middlewares"] == (
        "ready-allowlist"
    )
    assert labels["traefik.http.routers.api-ready-web.priority"] == "100"
    assert labels["traefik.http.routers.api-ready-web.rule"] == "Path(`/api/ready`)"
    assert labels["traefik.http.routers.api-ready-websecure.entrypoints"] == "websecure"
    assert labels["traefik.http.routers.api-ready-websecure.middlewares"] == (
        "ready-allowlist"
    )
    assert labels["traefik.http.routers.api-ready-websecure.priority"] == "100"
    assert labels["traefik.http.routers.api-ready-websecure.rule"] == (
        "Path(`/api/ready`)"
    )


def test_traefik_publishes_private_readiness_entrypoint_on_host_loopback() -> None:
    compose = yaml.safe_load(PROD_COMPOSE.read_text())
    labels = _api_labels()

    assert (
        "--entrypoints.ready.address=:8082" in compose["services"]["traefik"]["command"]
    )
    assert "127.0.0.1:8082:8082" in compose["services"]["traefik"]["ports"]
    assert labels["traefik.http.routers.api-ready-private.entrypoints"] == "ready"
    assert "traefik.http.routers.api-ready-private.middlewares" not in labels
    assert labels["traefik.http.routers.api-ready-private.rule"] == (
        "Path(`/api/ready`)"
    )
    assert labels["traefik.http.routers.api-ready-private.service"] == "api"


def test_traefik_routes_only_ready_backends() -> None:
    labels = _api_labels()

    assert labels["traefik.http.services.api.loadbalancer.healthcheck.path"] == (
        "/api/ready"
    )


# Utils


def _api_labels() -> dict[str, str]:
    compose = yaml.safe_load(PROD_COMPOSE.read_text())

    return dict(
        label.split("=", maxsplit=1) for label in compose["services"]["api"]["labels"]
    )
{% endif -%}
