import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts/check_postgres_image.py"
SPEC = importlib.util.spec_from_file_location(
    "check_postgres_image",
    SCRIPT_PATH,
)

if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"could not load {SCRIPT_PATH}")

check_postgres_image = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(check_postgres_image)


def test_all_files_agree_on_one_tag() -> None:
    assert (
        check_postgres_image.check(
            canonical_tags={"17.6"},
            file_tags={
                Path("compose/dev.yaml"): {"17.6"},
                Path("workflows/ci.yaml"): {"17.6"},
            },
        )
        == []
    )


def test_canonical_file_with_no_tags_reports_problem() -> None:
    problems = check_postgres_image.check(
        canonical_tags=set(),
        file_tags={Path("compose/dev.yaml"): {"17.6"}},
    )

    assert len(problems) == 1
    assert "expected exactly one postgres tag" in problems[0]
    assert "set()" in problems[0]


def test_drifted_file_reports_problem() -> None:
    problems = check_postgres_image.check(
        canonical_tags={"17.6"},
        file_tags={
            Path("compose/dev.yaml"): {"17.5"},
            Path("workflows/ci.yaml"): {"17.6"},
        },
    )

    assert len(problems) == 2
    assert "canonical {'17.6'}" in problems[0]
    assert problems[1] == "  compose/dev.yaml: {'17.5'}"
