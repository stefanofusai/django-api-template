from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CI_WORKFLOW = ROOT / ".github/workflows/ci.yaml"
BAKE_CASES = {
    "csp-example-api": "use_csp=yes use_example_api=yes",
    "default": "",
    "example-jwt-auth-throttling": (
        "use_example_api=yes api_auth=jwt api_throttling=basic"
    ),
    "external-backing": "postgres=external redis=external use_traefik=no",
    "external-postgres": "postgres=external",
    "external-redis": "redis=external",
    "minimal": (
        "use_celery=none email_provider=none use_sentry=no "
        "use_s3_media=no use_traefik=no"
    ),
}
SMOKE_VARIANTS = {
    "default": "",
    "external-backing": "postgres=external redis=external use_traefik=no",
    "external-redis": "redis=external use_traefik=no",
    "minimal": (
        "use_celery=none email_provider=none use_sentry=no "
        "use_s3_media=no use_traefik=no"
    ),
}


def test_bake_matrix_covers_supported_option_interactions() -> None:
    workflow = CI_WORKFLOW.read_text()

    for case, extra_args in BAKE_CASES.items():
        rendered_args = '""' if not extra_args else extra_args
        entry = (
            f"          - case: {case}\n"
            "            project_name: My Project\n"
            f"            extra-args: {rendered_args}\n"
            "            slug: my-project"
        )

        assert entry in workflow


def test_smoke_matrix_covers_supported_backing_topologies() -> None:
    workflow = CI_WORKFLOW.read_text()

    for variant, extra_args in SMOKE_VARIANTS.items():
        rendered_args = '""' if not extra_args else extra_args
        entry = (
            f"          - variant: {variant}\n            extra-args: {rendered_args}"
        )

        assert entry in workflow


def test_smoke_uses_rendered_environment_helper() -> None:
    workflow = CI_WORKFLOW.read_text()

    assert workflow.count("./.github/scripts/docker-smoke.sh") == 1
    assert "sed -i" not in workflow
