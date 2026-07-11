import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts/check_redis_image.py"
SPEC = importlib.util.spec_from_file_location("check_redis_image", SCRIPT_PATH)

if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"could not load {SCRIPT_PATH}")

check_redis_image = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(check_redis_image)


def test_all_files_agree_on_one_tag() -> None:
    assert check_redis_image.check(
        canonical_tags={"8.8.0"},
        file_tags={
            Path("compose/ci-services.yaml"): {"8.8.0"},
            Path("compose/dev.yaml"): {"8.8.0"},
        },
    ) == []


def test_canonical_file_with_no_tags_reports_problem() -> None:
    problems = check_redis_image.check(
        canonical_tags=set(),
        file_tags={Path("compose/dev.yaml"): {"8.8.0"}},
    )

    assert len(problems) == 1
    assert "expected exactly one redis tag" in problems[0]
    assert "set()" in problems[0]


def test_drifted_file_reports_problem() -> None:
    problems = check_redis_image.check(
        canonical_tags={"8.8.0"},
        file_tags={
            Path("compose/ci-services.yaml"): {"8.8.0"},
            Path("compose/dev.yaml"): {"8.7.0"},
        },
    )

    assert len(problems) == 2
    assert "canonical {'8.8.0'}" in problems[0]
    assert problems[1] == "  compose/dev.yaml: {'8.7.0'}"


def test_files_list_covers_generated_compose_files() -> None:
    assert check_redis_image.FILES == [
        Path("{{cookiecutter.project_slug}}/.docker/compose/ci-services.yaml"),
        Path("{{cookiecutter.project_slug}}/.docker/compose/dev.yaml"),
    ]
