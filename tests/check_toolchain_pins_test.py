import shutil
from pathlib import Path

from scripts import check_toolchain_pins


ROOT = Path(__file__).resolve().parents[1]


def test_drifted_toolchain_path_is_reported(tmp_path: Path) -> None:
    fixture_root = tmp_path / "template"

    for relative_path in check_toolchain_pins.CONTRACT_PATHS:
        source = ROOT / relative_path
        destination = fixture_root / relative_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(source, destination)

    dockerfile = fixture_root / "{{cookiecutter.project_slug}}/.docker/Dockerfile"
    dockerfile.write_text(dockerfile.read_text().replace("uv:0.11.19", "uv:0.11.18"))

    failures = check_toolchain_pins.check_contract(fixture_root, check_lock=False)

    assert failures == [
        "{{cookiecutter.project_slug}}/.docker/Dockerfile: expected uv 0.11.19, "
        "found 0.11.18"
    ]


def test_floating_cookiecutter_command_is_reported(tmp_path: Path) -> None:
    fixture_root = tmp_path / "template"

    for relative_path in check_toolchain_pins.CONTRACT_PATHS:
        source = ROOT / relative_path
        destination = fixture_root / relative_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(source, destination)

    readme = fixture_root / "README.md"
    readme.write_text(
        readme.read_text().replace(
            "uvx --from=cookiecutter==2.7.1 cookiecutter",
            "uvx cookiecutter",
        )
    )

    failures = check_toolchain_pins.check_contract(fixture_root, check_lock=False)

    assert failures == ["README.md: contains an unversioned uvx cookiecutter command"]


def test_post_gen_uv_drift_is_reported(tmp_path: Path) -> None:
    fixture_root = tmp_path / "template"

    for relative_path in check_toolchain_pins.CONTRACT_PATHS:
        source = ROOT / relative_path
        destination = fixture_root / relative_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(source, destination)

    hook = fixture_root / "hooks/post_gen_project.py"
    hook.write_text(
        hook.read_text().replace('UV_VERSION = "0.11.19"', 'UV_VERSION = "0.11.18"')
    )

    failures = check_toolchain_pins.check_contract(fixture_root, check_lock=False)

    assert failures == ["hooks/post_gen_project.py: expected uv 0.11.19, found 0.11.18"]


def test_stale_root_lock_is_reported(tmp_path: Path) -> None:
    fixture_root = tmp_path / "template"

    for relative_path in check_toolchain_pins.CONTRACT_PATHS:
        source = ROOT / relative_path
        destination = fixture_root / relative_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(source, destination)

    pyproject = fixture_root / "pyproject.toml"
    pyproject.write_text(
        pyproject.read_text().replace("pytest==9.1.1", "pytest==9.0.3")
    )

    failures = check_toolchain_pins.check_contract(fixture_root)

    assert "uv.lock: does not match pyproject.toml" in failures


def test_toolchain_contract_is_synchronized() -> None:
    assert check_toolchain_pins.check_contract(ROOT) == []
