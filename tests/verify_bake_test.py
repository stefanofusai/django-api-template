import argparse
import subprocess
from pathlib import Path
from unittest.mock import call, patch

import pytest

from scripts import verify_bake


def test_option_accepts_key_value() -> None:
    assert verify_bake._option("use_celery=none") == ("use_celery", "none")


@pytest.mark.parametrize("value", ["", "missing", "=value", "key="])
def test_option_rejects_invalid_value(value: str) -> None:
    with pytest.raises(argparse.ArgumentTypeError):
        verify_bake._option(value)


def test_verifier_propagates_failure_and_tears_down(tmp_path: Path) -> None:
    project = tmp_path / "my-project"
    project.mkdir()
    (project / ".env.example").write_text("SECRET_KEY=example\n")

    with (
        patch("sys.argv", ["verify_bake.py", "--output", str(tmp_path)]),
        patch.object(verify_bake, "_run") as run,
        patch.object(verify_bake.subprocess, "run") as teardown,
    ):
        run.side_effect = [None, None, subprocess.CalledProcessError(1, ["pytest"])]

        with pytest.raises(subprocess.CalledProcessError):
            verify_bake.main()

    assert run.call_args_list[0].args[0][:5] == [
        "uv",
        "run",
        "--locked",
        "cookiecutter",
        ".",
    ]
    assert run.call_args_list[1] == call(
        [
            "docker",
            "compose",
            "-f",
            ".docker/compose/dev.yaml",
            "--env-file=.env",
            "up",
            "-d",
            "--wait",
            "postgres",
        ],
        cwd=project,
    )
    teardown.assert_called_once()
