import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts/check_skills_lock.py"
SPEC = importlib.util.spec_from_file_location(
    "check_skills_lock",
    SCRIPT_PATH,
)

if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"could not load {SCRIPT_PATH}")

check_skills_lock = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(check_skills_lock)


def _lock(**hashes: str) -> str:
    return json.dumps(
        {
            "version": 2,
            "skills": {
                name: {
                    "source": "x/y",
                    "sourceType": "github",
                    "skillPath": f"skills/{name}/SKILL.md",
                    "computedHash": value,
                }
                for name, value in hashes.items()
            },
        },
    )


def test_all_match_returns_no_problems() -> None:
    lock = _lock(alpha="aaa", beta="bbb")

    assert check_skills_lock.check(lock, {"alpha": "aaa", "beta": "bbb"}) == []


def test_empty_lock_fails_closed() -> None:
    assert check_skills_lock.check(json.dumps({"version": 2, "skills": {}}), {})


def test_hash_mismatch_names_the_skill() -> None:
    problems = check_skills_lock.check(_lock(alpha="aaa"), {"alpha": "tampered"})

    assert len(problems) == 1
    assert "alpha" in problems[0]


def test_missing_lock_fails_closed() -> None:
    assert check_skills_lock.check(None, {})


def test_missing_vendored_file_is_reported() -> None:
    problems = check_skills_lock.check(_lock(alpha="aaa", beta="bbb"), {"alpha": "aaa"})

    assert len(problems) == 1
    assert "beta" in problems[0]
    assert "missing" in problems[0]


def test_unparseable_lock_fails_closed() -> None:
    assert check_skills_lock.check("{ not json", {})
