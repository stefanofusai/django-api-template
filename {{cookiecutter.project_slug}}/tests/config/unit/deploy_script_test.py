import os
import stat
import subprocess
from pathlib import Path

import pytest

AWK_FAILURE = 47
DEPLOY_SCRIPT = Path(".docker/scripts/deploy.sh").resolve()
DOCKER_FAILURE = 41
PRIVATE_FILE_MODE = 0o600
READINESS_FAILURE = 22
USAGE_ERROR = 2


def test_deploy_script_adds_app_version_when_missing(tmp_path: Path) -> None:
    (tmp_path / ".env").write_text("DATABASE_URL=postgres://db.example.test/app\n")

    result = _run_deploy_script(tmp_path, "v1.2.3")

    assert result.returncode == 0, result.stderr
    assert (tmp_path / ".env").read_text() == (
        "DATABASE_URL=postgres://db.example.test/app\nAPP_VERSION=v1.2.3\n"
    )
    assert (tmp_path / "docker.log").read_text().splitlines() == _docker_calls()


def test_deploy_script_canonicalizes_duplicate_app_versions(
    tmp_path: Path,
) -> None:
    env_path = tmp_path / ".env"
    env_path.write_text(
        "APP_VERSION=v0.1.0\n"
        "DATABASE_URL=postgres://db.example.test/app\n"
        "APP_VERSION=v0.2.0\n"
        "OTHER=value\n"
        "APP_VERSION=v0.3.0\n",
    )
    env_path.chmod(0o666)

    result = _run_deploy_script(tmp_path, "v1.2.3", permissive_umask=True)

    assert result.returncode == 0, result.stderr
    assert env_path.read_text() == (
        "APP_VERSION=v1.2.3\nDATABASE_URL=postgres://db.example.test/app\nOTHER=value\n"
    )
    assert list(tmp_path.glob(".env.tmp.*")) == []
    assert (tmp_path / "docker.log").read_text().splitlines() == _docker_calls()


def test_deploy_script_exits_nonzero_when_readiness_fails(tmp_path: Path) -> None:
    (tmp_path / ".env").write_text(
        "DATABASE_URL=postgres://db.example.test/app\nAPP_VERSION=v0.1.0\n"
    )

    result = _run_deploy_script(
        tmp_path,
        "v1.2.3",
        readiness_exit_code=READINESS_FAILURE,
    )

    assert result.returncode == READINESS_FAILURE
    assert (tmp_path / "docker.log").read_text().splitlines() == _docker_calls()


@pytest.mark.parametrize(
    "failure_phase",
    [
        "pull",
{%- if cookiecutter.use_traefik == "yes" %}
        "rollout",
{%- endif %}
        "up",
        "readiness",
    ],
)
def test_deploy_script_exits_on_each_failed_docker_phase(
    tmp_path: Path,
    failure_phase: str,
) -> None:
    (tmp_path / ".env").write_text(
        "DATABASE_URL=postgres://db.example.test/app\nAPP_VERSION=v0.1.0\n"
    )

    result = _run_deploy_script(
        tmp_path,
        "v1.2.3",
        docker_failure_phase=failure_phase,
    )

    assert result.returncode == DOCKER_FAILURE
    phases = [
        "pull",
{%- if cookiecutter.use_traefik == "yes" %}
        "rollout",
{%- endif %}
        "up",
        "readiness",
    ]
    expected_calls = _docker_calls()[: phases.index(failure_phase) + 1]
    assert (tmp_path / "docker.log").read_text().splitlines() == expected_calls


def test_deploy_script_help_does_not_require_environment(tmp_path: Path) -> None:
    result = _run_deploy_script(tmp_path, "--help")

    assert result.returncode == 0
    assert result.stdout == "usage: deploy.sh <tag, e.g. v1.2.3>\n"
    assert result.stderr == ""
    assert not (tmp_path / "docker.log").exists()


def test_deploy_script_rejects_missing_environment(tmp_path: Path) -> None:
    result = _run_deploy_script(tmp_path, "v1.2.3")

    assert result.returncode == USAGE_ERROR
    assert result.stderr == "no .env here; run from the project root\n"
    assert not (tmp_path / "docker.log").exists()


def test_deploy_script_rejects_missing_tag(tmp_path: Path) -> None:
    result = _run_deploy_script(tmp_path)

    assert result.returncode == USAGE_ERROR
    assert result.stderr == "usage: deploy.sh <tag, e.g. v1.2.3>\n"
    assert not (tmp_path / "docker.log").exists()


@pytest.mark.parametrize(
    "tag",
    ["v1.2.3-rc1", "v1.2.3/evil", "v1.2.3x", "v1.x.3"],
)
def test_deploy_script_rejects_non_exact_version_tags(
    tmp_path: Path,
    tag: str,
) -> None:
    result = _run_deploy_script(tmp_path, tag)

    assert result.returncode == USAGE_ERROR
    assert "tag must look like v<major>.<minor>.<patch>" in result.stderr
    assert not (tmp_path / "docker.log").exists()


def test_deploy_script_removes_temporary_file_when_rewrite_fails(
    tmp_path: Path,
) -> None:
    env_path = tmp_path / ".env"
    original = "APP_VERSION=v0.1.0\nSECRET=keep-me\n"
    env_path.write_text(original)

    result = _run_deploy_script(
        tmp_path,
        "v1.2.3",
        awk_exit_code=AWK_FAILURE,
    )

    assert result.returncode == AWK_FAILURE
    assert env_path.read_text() == original
    assert list(tmp_path.glob(".env.tmp.*")) == []
    assert not (tmp_path / "docker.log").exists()


{% if cookiecutter.use_traefik == "yes" -%}
def test_deploy_script_requires_docker_rollout(tmp_path: Path) -> None:
    (tmp_path / ".env").write_text("APP_VERSION=v0.1.0\n")

    result = _run_deploy_script(tmp_path, "v1.2.3", include_rollout=False)

    assert result.returncode == USAGE_ERROR
    assert result.stderr == (
        "docker-rollout is required for Traefik zero-downtime deploys\n"
    )
    assert not (tmp_path / "docker.log").exists()


{% endif -%}


def test_deploy_script_rewrites_environment_with_private_mode(
    tmp_path: Path,
) -> None:
    env_path = tmp_path / ".env"
    env_path.write_text("APP_VERSION=v0.1.0\nSECRET=keep-me\n")
    env_path.chmod(0o666)

    result = _run_deploy_script(tmp_path, "v1.2.3", permissive_umask=True)

    assert result.returncode == 0, result.stderr
    assert stat.S_IMODE(env_path.stat().st_mode) == PRIVATE_FILE_MODE


def test_deploy_script_runs_docker_phases_in_order(tmp_path: Path) -> None:
    (tmp_path / ".env").write_text(
        "DATABASE_URL=postgres://db.example.test/app\n"
        "APP_VERSION=v0.1.0\n"
        "OTHER=value\n",
    )

    result = _run_deploy_script(tmp_path, "v1.2.3")

    assert result.returncode == 0, result.stderr
    assert (tmp_path / ".env").read_text() == (
        "DATABASE_URL=postgres://db.example.test/app\nAPP_VERSION=v1.2.3\nOTHER=value\n"
    )
    assert (tmp_path / "docker.log").read_text().splitlines() == _docker_calls()


# Utils


def _docker_calls() -> list[str]:
    return [
        "compose -f .docker/compose/prod.yaml --env-file=.env pull",
{%- if cookiecutter.use_traefik == "yes" %}
        "rollout -f .docker/compose/prod.yaml --env-file=.env api",
{%- endif %}
        "compose -f .docker/compose/prod.yaml --env-file=.env up -d --wait",
        "compose -f .docker/compose/prod.yaml --env-file=.env exec -T api "
        "curl -fsS -m 3 -o /dev/null "
        "http://127.0.0.1:8000/api/ready",
    ]


def _make_executable(path: Path, content: str) -> None:
    path.write_text(content)
    path.chmod(path.stat().st_mode | stat.S_IXUSR)


def _run_deploy_script({% if cookiecutter.use_traefik == "yes" %}  # noqa: PLR0913{% endif %}
    tmp_path: Path,
    *arguments: str,
    awk_exit_code: int | None = None,
    docker_failure_phase: str = "",
{%- if cookiecutter.use_traefik == "yes" %}
    include_rollout: bool = True,
{%- endif %}
    permissive_umask: bool = False,
    readiness_exit_code: int = 0,
) -> subprocess.CompletedProcess[str]:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir(exist_ok=True)
    docker_log = tmp_path / "docker.log"

    _make_executable(
        bin_dir / "docker",
        (
            "#!/bin/sh\n"
            'printf \'%s\\n\' "$*" >> "$DOCKER_LOG"\n'
            'case "$*" in\n'
            "    *' pull') phase=pull ;;\n"
            "    'rollout '*) phase=rollout ;;\n"
            "    *' up -d --wait') phase=up ;;\n"
            "    *'/api/ready') phase=readiness ;;\n"
            '    *) echo "unexpected docker command: $*" >&2; exit 98 ;;\n'
            "esac\n"
            '[ "$DOCKER_FAILURE_PHASE" != "$phase" ] || '
            'exit "$DOCKER_FAILURE_EXIT_CODE"\n'
            'case "$*" in\n'
            "    *'/api/ready') exit \"$READINESS_EXIT_CODE\" ;;\n"
            "esac\n"
        ),
    )
{%- if cookiecutter.use_traefik == "yes" %}
    if include_rollout:
        _make_executable(bin_dir / "docker-rollout", "#!/bin/sh\nexit 0\n")

{%- endif %}

    if awk_exit_code is not None:
        _make_executable(
            bin_dir / "awk",
            f"#!/bin/sh\nexit {awk_exit_code}\n",
        )

    env = os.environ | {
        "DOCKER_FAILURE_EXIT_CODE": str(DOCKER_FAILURE),
        "DOCKER_FAILURE_PHASE": docker_failure_phase,
        "DOCKER_LOG": str(docker_log),
        "PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}",
        "READINESS_EXIT_CODE": str(readiness_exit_code),
    }
    command = [str(DEPLOY_SCRIPT), *arguments]
    if permissive_umask:
        command = ["/bin/sh", "-c", 'umask 000; exec "$@"', "sh", *command]

    return subprocess.run(  # noqa: S603
        command,
        capture_output=True,
        check=False,
        cwd=tmp_path,
        env=env,
        text=True,
    )
