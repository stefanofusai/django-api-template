import os
import stat
import subprocess
from pathlib import Path

DEPLOY_SCRIPT = Path(".docker/scripts/deploy.sh").resolve()
READINESS_FAILURE = 22
USAGE_ERROR = 2


def test_deploy_script_exits_nonzero_when_readiness_fails(tmp_path: Path) -> None:
    (tmp_path / ".env").write_text(
        "DATABASE_URL=postgres://db.example.test/app\nAPP_VERSION=v0.1.0\n"
    )

    result = _run_deploy_script(
        readiness_exit_code=READINESS_FAILURE,
        tag="v1.2.3",
        tmp_path=tmp_path,
    )

    assert result.returncode == READINESS_FAILURE
    assert (tmp_path / "docker.log").read_text().splitlines() == _docker_calls()


def test_deploy_script_rejects_non_exact_version_tags(tmp_path: Path) -> None:
    for tag in ["v1.2.3-rc1", "v1.2.3/evil", "v1.2.3x", "v1.x.3"]:
        result = _run_deploy_script(tag=tag, tmp_path=tmp_path)

        assert result.returncode == USAGE_ERROR
        assert "tag must look like v<major>.<minor>.<patch>" in result.stderr


def test_deploy_script_updates_existing_app_version(tmp_path: Path) -> None:
    (tmp_path / ".env").write_text(
        "DATABASE_URL=postgres://db.example.test/app\n"
        "APP_VERSION=v0.1.0\n"
        "OTHER=value\n",
    )

    result = _run_deploy_script(tag="v1.2.3", tmp_path=tmp_path)

    assert result.returncode == 0, result.stderr
    assert (tmp_path / ".env").read_text() == (
        "DATABASE_URL=postgres://db.example.test/app\nAPP_VERSION=v1.2.3\nOTHER=value\n"
    )
    assert (tmp_path / "docker.log").read_text().splitlines() == _docker_calls()


def test_deploy_script_writes_app_version_when_missing(tmp_path: Path) -> None:
    (tmp_path / ".env").write_text("DATABASE_URL=postgres://db.example.test/app\n")

    result = _run_deploy_script(tag="v1.2.3", tmp_path=tmp_path)

    assert result.returncode == 0, result.stderr
    assert (tmp_path / ".env").read_text() == (
        "DATABASE_URL=postgres://db.example.test/app\nAPP_VERSION=v1.2.3\n"
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


def _run_deploy_script(
    *,
    readiness_exit_code: int = 0,
    tag: str,
    tmp_path: Path,
) -> subprocess.CompletedProcess[str]:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir(exist_ok=True)
    docker_log = tmp_path / "docker.log"

    _make_executable(
        bin_dir / "docker",
        (
            '#!/bin/sh\nprintf \'%s\\n\' "$*" >> "$DOCKER_LOG"\n'
            'case "$*" in\n'
            "*'/api/ready') exit \"$READINESS_EXIT_CODE\" ;;\n"
            "esac\n"
        ),
    )
    _make_executable(bin_dir / "docker-rollout", "#!/bin/sh\nexit 0\n")

    env = os.environ | {
        "DOCKER_LOG": str(docker_log),
        "PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}",
        "READINESS_EXIT_CODE": str(readiness_exit_code),
    }

    return subprocess.run(  # noqa: S603
        [str(DEPLOY_SCRIPT), tag],
        capture_output=True,
        check=False,
        cwd=tmp_path,
        env=env,
        text=True,
    )
