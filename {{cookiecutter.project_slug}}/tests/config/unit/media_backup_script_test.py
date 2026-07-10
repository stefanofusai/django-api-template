import os
import stat
import subprocess
from pathlib import Path

import pytest

DOCKER_STUB = r"""#!/usr/bin/env python3
import json
import os
import stat
import sys

args = sys.argv[1:]
with open(os.environ["DOCKER_LOG"], "a") as log:
    log.write(" ".join(args) + "\n")

if "config" in args:
    print(json.dumps({"volumes": {"media_data": {"name": "test-media"}}}))
elif "ps" in args:
    sys.stdout.write(os.environ["RUNNING_SERVICES"])
elif "-czf" in args:
    mode = stat.S_IMODE(os.fstat(sys.stdout.fileno()).st_mode)
    with open(os.environ["OUTPUT_MODE_LOG"], "w") as mode_log:
        mode_log.write(f"{mode:o}\n")
    sys.stdout.write(os.environ["BACKUP_CONTENT"])
"""

MEDIA_BACKUP_SCRIPT = Path(".docker/scripts/media-backup.sh").resolve()
OWNER_ONLY_MODE = 0o600
PERMISSION_ERROR = 2
RETAINED_ARTIFACT_COUNT = 2

TAR_STUB = """#!/bin/sh
printf '%s' "$TAR_OUTPUT"
exit "$TAR_STATUS"
"""


def test_media_backup_keeps_requested_archives_owner_only(tmp_path: Path) -> None:
    backup_dir = tmp_path / "backups"
    backup_dir.mkdir()
    (backup_dir / "20000101T000000Z.tar.gz").write_text("oldest")
    (backup_dir / "20010101T000000Z.tar.gz").write_text("newer")

    result = _run_media_backup_script(tmp_path, "backup", str(backup_dir), "2")

    assert result.returncode == 0, result.stderr
    archives = sorted(backup_dir.glob("*.tar.gz"))
    assert len(archives) == RETAINED_ARTIFACT_COUNT
    assert archives[0].name == "20010101T000000Z.tar.gz"
    assert stat.S_IMODE(archives[1].stat().st_mode) == OWNER_ONLY_MODE
    assert (tmp_path / "output-mode.log").read_text() == "600\n"
    assert (tmp_path / "docker.log").read_text().splitlines() == [
        "compose -f .docker/compose/prod.yaml --env-file=.env config --format json",
        "run --rm -v test-media:/media:ro alpine:3.22.2 tar -czf - -C /media .",
    ]


@pytest.mark.parametrize("running_service", ["api", "celery-worker"])
def test_media_restore_refuses_running_app_services(
    tmp_path: Path,
    running_service: str,
) -> None:
    archive = tmp_path / "media.tar.gz"
    archive.write_text("archive")

    result = _run_media_backup_script(
        tmp_path,
        "restore",
        str(archive),
        running_services=f"{running_service}\n",
    )

    assert result.returncode == PERMISSION_ERROR
    assert "refusing to restore while app services are running" in result.stderr
    assert (tmp_path / "docker.log").read_text().splitlines() == [
        "compose -f .docker/compose/prod.yaml --env-file=.env ps --services --status=running",
    ]


@pytest.mark.parametrize("member", ["/etc/passwd\n", "./media/../secret\n"])
def test_media_restore_rejects_unsafe_members(
    tmp_path: Path,
    member: str,
) -> None:
    archive = tmp_path / "media.tar.gz"
    archive.write_text("archive")

    result = _run_media_backup_script(
        tmp_path,
        "restore",
        str(archive),
        tar_output=member,
    )

    assert result.returncode == PERMISSION_ERROR
    assert "archive contains unsafe media paths" in result.stderr


def test_media_restore_runs_with_force(tmp_path: Path) -> None:
    archive = tmp_path / "media.tar.gz"
    archive.write_text("archive")

    result = _run_media_backup_script(
        tmp_path,
        "restore",
        str(archive),
        "--force",
        running_services="api\n",
    )

    assert result.returncode == 0, result.stderr
    assert (tmp_path / "docker.log").read_text().splitlines() == [
        "compose -f .docker/compose/prod.yaml --env-file=.env config --format json",
        "run --rm -i -v test-media:/media alpine:3.22.2 tar -xzf - -C /media",
    ]


def test_media_verify_accepts_archive_with_entries(tmp_path: Path) -> None:
    archive = tmp_path / "media.tar.gz"
    archive.write_text("archive")

    result = _run_media_backup_script(tmp_path, "verify", str(archive))

    assert result.returncode == 0, result.stderr
    assert "verify OK" in result.stdout


def test_media_verify_rejects_empty_archive(tmp_path: Path) -> None:
    archive = tmp_path / "media.tar.gz"
    archive.write_text("archive")

    result = _run_media_backup_script(
        tmp_path,
        "verify",
        str(archive),
        tar_output="",
    )

    assert result.returncode == 1
    assert "archive contains no media entries" in result.stderr
    assert "verify OK" not in result.stdout


def test_media_verify_rejects_partial_listing_failure(tmp_path: Path) -> None:
    archive = tmp_path / "media.tar.gz"
    archive.write_text("archive")

    result = _run_media_backup_script(
        tmp_path,
        "verify",
        str(archive),
        tar_status=1,
    )

    assert result.returncode != 0
    assert "verify OK" not in result.stdout


# Utils


def _make_executable(path: Path, content: str) -> None:
    path.write_text(content)
    path.chmod(path.stat().st_mode | stat.S_IXUSR)


def _run_media_backup_script(
    tmp_path: Path,
    *arguments: str,
    backup_content: str = "archive",
    running_services: str = "",
    tar_output: str = "./media/file.txt\n",
    tar_status: int = 0,
) -> subprocess.CompletedProcess[str]:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir(exist_ok=True)
    docker_log = tmp_path / "docker.log"
    output_mode_log = tmp_path / "output-mode.log"

    _make_executable(bin_dir / "docker", DOCKER_STUB)
    _make_executable(bin_dir / "tar", TAR_STUB)

    env = os.environ | {
        "BACKUP_CONTENT": backup_content,
        "DOCKER_LOG": str(docker_log),
        "OUTPUT_MODE_LOG": str(output_mode_log),
        "PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}",
        "RUNNING_SERVICES": running_services,
        "TAR_OUTPUT": tar_output,
        "TAR_STATUS": str(tar_status),
    }
    command = [
        "/bin/sh",
        "-c",
        'umask 022; exec "$@"',
        "sh",
        str(MEDIA_BACKUP_SCRIPT),
        *arguments,
    ]

    return subprocess.run(  # noqa: S603
        command,
        capture_output=True,
        check=False,
        cwd=tmp_path,
        env=env,
        text=True,
    )
