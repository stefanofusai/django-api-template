import re
from pathlib import Path

COMPOSE_FILE = Path(".docker/compose/prod.yaml")
DISABLED_API_SECTIONS = {
    "ALLOW_PAUSE",
    "ALLOW_RESTARTS",
    "ALLOW_START",
    "ALLOW_STOP",
    "ALLOW_UNPAUSE",
    "AUTH",
    "BUILD",
    "COMMIT",
    "CONFIGS",
    "DISTRIBUTION",
    "EXEC",
    "GRPC",
    "IMAGES",
    "INFO",
    "NODES",
    "PLUGINS",
    "POST",
    "SECRETS",
    "SERVICES",
    "SESSION",
    "SWARM",
    "SYSTEM",
    "TASKS",
    "VOLUMES",
}
DOCKER_SOCKET_PROXY_IMAGE = (
    "ghcr.io/tecnativa/docker-socket-proxy:v0.4.2@"
    "sha256:1f3a6f303320723d199d2316a3e82b2e2685d86c275d5e3deeaf182573b47476"
)
ENABLED_API_SECTIONS = {
    "CONTAINERS",
    "EVENTS",
    "NETWORKS",
    "PING",
    "VERSION",
}
TRAEFIK_ENABLED = {{ cookiecutter.use_traefik == "yes" }}


def test_docker_socket_proxy_allows_only_required_read_api_sections() -> None:
    proxy = _service_block("docker-socket-proxy")

    for section in ENABLED_API_SECTIONS:
        assert (f'{section}: "1"' in proxy) is TRAEFIK_ENABLED

    for section in DISABLED_API_SECTIONS:
        assert (f'{section}: "0"' in proxy) is TRAEFIK_ENABLED


def test_docker_socket_proxy_is_pinned_and_private() -> None:
    compose = _template_text()
    proxy = _service_block("docker-socket-proxy")

    assert (f"image: {DOCKER_SOCKET_PROXY_IMAGE}" in proxy) is TRAEFIK_ENABLED
    assert ("/var/run/docker.sock:/var/run/docker.sock:ro" in proxy) is TRAEFIK_ENABLED
    assert "ports:" not in proxy
    assert "expose:" not in proxy
    assert ("networks:\n      - docker-socket-proxy" in proxy) is TRAEFIK_ENABLED
    assert (
        "networks:\n  docker-socket-proxy:\n    internal: true" in compose
    ) is TRAEFIK_ENABLED


def test_traefik_uses_healthy_docker_socket_proxy_dependency() -> None:
    traefik = _service_block("traefik")

    assert (
        "docker-socket-proxy:\n        condition: service_healthy" in traefik
    ) is TRAEFIK_ENABLED
    assert (
        "--providers.docker.endpoint=tcp://docker-socket-proxy:2375" in traefik
    ) is TRAEFIK_ENABLED
    assert (
        "networks:\n      - default\n      - docker-socket-proxy" in traefik
    ) is TRAEFIK_ENABLED
    assert "/var/run/docker.sock" not in traefik


# Utils


def _service_block(name: str) -> str:
    pattern = rf"(?ms)^  {re.escape(name)}:\n(.*?)(?=^  \S|^\S|\Z)"

    return [*re.findall(pattern, _template_text()), ""][0]


def _template_text() -> str:
    return COMPOSE_FILE.read_text()
