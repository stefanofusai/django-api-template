import os
import stat
import subprocess
from pathlib import Path

DOCKER_STUB = r"""#!/usr/bin/env python3
import os
import stat
import sys

args = sys.argv[1:]
with open(os.environ["DOCKER_LOG"], "a") as log:
    log.write(" ".join(args) + "\n")

if "ps" in args:
    sys.stdout.write(os.environ["RUNNING_SERVICES"])
elif any("pg_dump" in arg for arg in args):
    mode = stat.S_IMODE(os.fstat(sys.stdout.fileno()).st_mode)
    with open(os.environ["OUTPUT_MODE_LOG"], "w") as mode_log:
        mode_log.write(f"{mode:o}\n")
    sys.stdout.write(os.environ["DUMP_CONTENT"])
"""

OWNER_ONLY_MODE = 0o600
PERMISSION_ERROR = 2
POSTGRES_BACKUP_SCRIPT = Path(".docker/scripts/postgres-backup.sh").resolve()
RETAINED_ARTIFACT_COUNT = 2


def test_postgres_backup_cleans_up_empty_temporary_dump(tmp_path: Path) -> None:
    backup_dir = tmp_path / "backups"

    result = _run_postgres_backup_script(
        tmp_path,
        "backup",
        str(backup_dir),
        dump_content="",
    )

    assert result.returncode == 1
    assert "pg_dump produced an empty file" in result.stderr
    assert list(backup_dir.iterdir()) == []


def test_postgres_backup_keeps_requested_dumps_owner_only(tmp_path: Path) -> None:
    backup_dir = tmp_path / "backups"
    backup_dir.mkdir()
    (backup_dir / "20000101T000000Z.dump").write_text("oldest")
    (backup_dir / "20010101T000000Z.dump").write_text("newer")

    result = _run_postgres_backup_script(tmp_path, "backup", str(backup_dir), "2")

    assert result.returncode == 0, result.stderr
    dumps = sorted(backup_dir.glob("*.dump"))
    assert len(dumps) == RETAINED_ARTIFACT_COUNT
    assert dumps[0].name == "20010101T000000Z.dump"
    assert stat.S_IMODE(dumps[1].stat().st_mode) == OWNER_ONLY_MODE
    assert (tmp_path / "output-mode.log").read_text() == "600\n"
    assert (tmp_path / "docker.log").read_text().splitlines() == [
        "compose -f .docker/compose/prod.yaml --env-file=.env exec -T postgres "
        'sh -c pg_dump --format=custom --username="$POSTGRES_USER" "$POSTGRES_DB"',
    ]


def test_postgres_restore_refuses_running_app_services(tmp_path: Path) -> None:
    dump_file = tmp_path / "database.dump"
    dump_file.write_text("dump")

    result = _run_postgres_backup_script(
        tmp_path,
        "restore",
        str(dump_file),
        running_services="api\n",
    )

    assert result.returncode == PERMISSION_ERROR
    assert "refusing to restore while app services are running" in result.stderr
    assert (tmp_path / "docker.log").read_text().splitlines() == [
        "compose -f .docker/compose/prod.yaml --env-file=.env ps --services --status=running",
    ]


def test_postgres_restore_runs_with_force(tmp_path: Path) -> None:
    dump_file = tmp_path / "database.dump"
    dump_file.write_text("dump")

    result = _run_postgres_backup_script(
        tmp_path,
        "restore",
        str(dump_file),
        "--force",
        running_services="api\n",
    )

    assert result.returncode == 0, result.stderr
    assert (tmp_path / "docker.log").read_text().splitlines() == [
        "compose -f .docker/compose/prod.yaml --env-file=.env exec -T postgres "
        'sh -c pg_restore --clean --dbname="$POSTGRES_DB" --if-exists '
        '--username="$POSTGRES_USER"',
    ]


# Utils


def _make_executable(path: Path, content: str) -> None:
    path.write_text(content)
    path.chmod(path.stat().st_mode | stat.S_IXUSR)


def _run_postgres_backup_script(
    tmp_path: Path,
    *arguments: str,
    dump_content: str = "dump",
    running_services: str = "",
) -> subprocess.CompletedProcess[str]:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir(exist_ok=True)
    docker_log = tmp_path / "docker.log"
    output_mode_log = tmp_path / "output-mode.log"

    _make_executable(bin_dir / "docker", DOCKER_STUB)

    env = os.environ | {
        "DOCKER_LOG": str(docker_log),
        "DUMP_CONTENT": dump_content,
        "OUTPUT_MODE_LOG": str(output_mode_log),
        "PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}",
        "RUNNING_SERVICES": running_services,
    }
    command = [
        "/bin/sh",
        "-c",
        'umask 022; exec "$@"',
        "sh",
        str(POSTGRES_BACKUP_SCRIPT),
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
