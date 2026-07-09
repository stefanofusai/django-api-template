import os
import stat
import subprocess
from pathlib import Path

DEPLOY_SCRIPT = Path(".docker/scripts/deploy.sh").resolve()
USAGE_ERROR = 2


def test_deploy_script_rejects_non_exact_version_tags(tmp_path: Path) -> None:
    for tag in ["v1.2.3-rc1", "v1.2.3/evil", "v1.2.3x", "v1.x.3"]:
        result = _run_deploy_script(tmp_path, tag)

        assert result.returncode == USAGE_ERROR
        assert "tag must look like v<major>.<minor>.<patch>" in result.stderr


def test_deploy_script_updates_existing_app_version(tmp_path: Path) -> None:
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


def test_deploy_script_writes_app_version_when_missing(tmp_path: Path) -> None:
    (tmp_path / ".env").write_text("DATABASE_URL=postgres://db.example.test/app\n")

    result = _run_deploy_script(tmp_path, "v1.2.3")

    assert result.returncode == 0, result.stderr
    assert (tmp_path / ".env").read_text() == (
        "DATABASE_URL=postgres://db.example.test/app\nAPP_VERSION=v1.2.3\n"
    )


# Utils


def _make_executable(path: Path, content: str) -> None:
    path.write_text(content)
    path.chmod(path.stat().st_mode | stat.S_IXUSR)


def _run_deploy_script(
    tmp_path: Path,
    tag: str,
) -> subprocess.CompletedProcess[str]:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir(exist_ok=True)
    docker_log = tmp_path / "docker.log"

    _make_executable(
        bin_dir / "docker",
        '#!/bin/sh\nprintf \'%s\\n\' "$*" >> "$DOCKER_LOG"\n',
    )
    _make_executable(bin_dir / "docker-rollout", "#!/bin/sh\nexit 0\n")

    env = os.environ | {
        "DOCKER_LOG": str(docker_log),
        "PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}",
    }

    return subprocess.run(  # noqa: S603
        [str(DEPLOY_SCRIPT), tag],
        capture_output=True,
        check=False,
        cwd=tmp_path,
        env=env,
        text=True,
    )
