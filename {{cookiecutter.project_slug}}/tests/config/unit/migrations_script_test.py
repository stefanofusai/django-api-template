import os
import stat
import subprocess
from pathlib import Path

MIGRATIONS_SCRIPT = Path(".docker/scripts/migrations.sh").resolve()
PYTHON_STUB = """#!/bin/sh
printf '%s\n' "$DATABASE_LOCK_TIMEOUT" > "$LOCK_TIMEOUT_LOG"
printf '%s\n' "$DATABASE_STATEMENT_TIMEOUT" > "$STATEMENT_TIMEOUT_LOG"
printf '%s\n' "$*" > "$PYTHON_ARGUMENTS_LOG"
"""


def test_migrations_script_preserves_database_lock_timeout_default(
    tmp_path: Path,
) -> None:
    result = _run_migrations_script(
        database_lock_timeout="5000",
        tmp_path=tmp_path,
    )

    assert result.returncode == 0, result.stderr
    assert (tmp_path / "lock-timeout.log").read_text() == "5000\n"
    assert (tmp_path / "statement-timeout.log").read_text() == "0\n"
    assert (tmp_path / "python-arguments.log").read_text() == (
        "manage.py migrate --no-input\n"
    )


def test_migrations_script_preserves_database_lock_timeout_override(
    tmp_path: Path,
) -> None:
    result = _run_migrations_script(
        database_lock_timeout="12000",
        tmp_path=tmp_path,
    )

    assert result.returncode == 0, result.stderr
    assert (tmp_path / "lock-timeout.log").read_text() == "12000\n"
    assert (tmp_path / "statement-timeout.log").read_text() == "0\n"


# Utils


def _make_executable(path: Path, content: str) -> None:
    path.write_text(content)
    path.chmod(path.stat().st_mode | stat.S_IXUSR)


def _run_migrations_script(
    *,
    database_lock_timeout: str,
    tmp_path: Path,
) -> subprocess.CompletedProcess[str]:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()

    _make_executable(bin_dir / "python", PYTHON_STUB)

    env = os.environ | {
        "DATABASE_LOCK_TIMEOUT": database_lock_timeout,
        "LOCK_TIMEOUT_LOG": str(tmp_path / "lock-timeout.log"),
        "PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}",
        "PYTHON_ARGUMENTS_LOG": str(tmp_path / "python-arguments.log"),
        "STATEMENT_TIMEOUT_LOG": str(tmp_path / "statement-timeout.log"),
    }

    return subprocess.run(  # noqa: S603
        [str(MIGRATIONS_SCRIPT)],
        capture_output=True,
        check=False,
        cwd=tmp_path,
        env=env,
        text=True,
    )
