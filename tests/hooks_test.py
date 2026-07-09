import contextlib
import json
import re
import tempfile
import types
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
HOOK_PATH = ROOT / "hooks/post_gen_project.py"
JINJA_CONSTANT = re.compile(
    r"^(?P<name>[A-Z_]+) = \{\{ cookiecutter\.(?P<knob>\w+) \| tojson \}\}$",
    re.MULTILINE,
)
TEMPLATE_ROOT = ROOT / "{{cookiecutter.project_slug}}"
TEST_CONTEXT = {
    "api_auth": "session",
    "api_throttling": "none",
    "postgres": "compose",
    "traefik_tls": "letsencrypt",
    "use_celery": "worker+beat",
    "use_cors": "no",
    "use_csp": "no",
    "use_example_api": "no",
    "use_sentry": "yes",
    "use_traefik": "yes",
}


def test_every_removal_entry_exists_in_the_template_tree() -> None:
    entries = _extract_removal_entries()

    assert len(entries) >= 20

    for entry in entries:
        assert (TEMPLATE_ROOT / entry).exists(), entry


def test_missing_removal_entries_exit_with_actionable_message() -> None:
    module = _load_hook_module()
    module.REMOVED_PATHS = ["missing-file.txt"]
    module.REMOVED_DIRS = ["missing-dir"]

    with tempfile.TemporaryDirectory() as tmp_dir:
        with contextlib.chdir(tmp_dir):
            with pytest.raises(SystemExit) as raised:
                module.main()

    message = str(raised.value)
    assert "post_gen_project: removal-list entries not found" in message
    assert "missing-file.txt" in message
    assert "missing-dir" in message


def test_parse_compose_version_extracts_three_part_version() -> None:
    module = _load_hook_module()

    assert module._parse_compose_version("Docker Compose version v5.3.0") == (
        5,
        3,
        0,
    )


def test_parse_compose_version_pads_missing_patch_version() -> None:
    module = _load_hook_module()

    assert module._parse_compose_version("5.3") == (5, 3, 0)


def test_parse_compose_version_returns_none_without_digits() -> None:
    module = _load_hook_module()

    assert module._parse_compose_version("no digits here") is None


def test_prune_celery_skill_metadata_removes_only_celery_skill() -> None:
    module = _load_hook_module()
    lock = {
        "version": 1,
        "skills": {
            "django-celery-expert": {"source": "celery"},
            "postgres": {"source": "postgres"},
        },
    }
    readme = (
        "# Agents\n"
        "- `django-celery-expert`: Celery guidance.\n"
        "- `postgres`: Postgres guidance.\n"
    )

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        (tmp_path / ".agents").mkdir()
        (tmp_path / ".agents/README.md").write_text(readme)
        (tmp_path / "skills-lock.json").write_text(json.dumps(lock))

        with contextlib.chdir(tmp_path):
            module._prune_celery_skill_metadata()

        pruned_lock_text = (tmp_path / "skills-lock.json").read_text()
        pruned_lock = json.loads(pruned_lock_text)
        pruned_readme = (tmp_path / ".agents/README.md").read_text()

    assert "django-celery-expert" not in pruned_lock["skills"]
    assert "postgres" in pruned_lock["skills"]
    assert pruned_lock_text.endswith("\n")
    assert pruned_readme == "# Agents\n- `postgres`: Postgres guidance.\n"


# Utils


def _extract_removal_entries() -> list[str]:
    source = HOOK_PATH.read_text()
    lines = source.splitlines(keepends=True)
    start = _line_index(lines, "REMOVED_DIRS = [")
    paths_start = _line_index(lines, "REMOVED_PATHS = [")
    end = next(
        index
        for index, line in enumerate(lines[paths_start:], start=paths_start)
        if line.rstrip("\n") == "]"
    )
    region = "".join(lines[start : end + 1])
    literals = re.findall(r'"([^"]+)"', region)

    return [
        literal
        for literal in literals
        if "/" in literal or literal.startswith(".")
    ]


def _line_index(lines: list[str], expected: str) -> int:
    return next(
        index
        for index, line in enumerate(lines)
        if line.strip() == expected
    )


def _load_hook_module() -> types.ModuleType:
    source = JINJA_CONSTANT.sub(
        lambda match: (
            f"{match.group('name')} = "
            f"{json.dumps(TEST_CONTEXT[match.group('knob')])}"
        ),
        HOOK_PATH.read_text(),
    )
    module = types.ModuleType("post_gen_project")
    exec(compile(source, str(HOOK_PATH), "exec"), module.__dict__)  # noqa: S102
    return module
