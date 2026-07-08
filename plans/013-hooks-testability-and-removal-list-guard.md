# Plan 013: Unit-test the cookiecutter hooks and guard the post-gen removal lists

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving to the
> next step. If anything in the "STOP conditions" section occurs, stop and
> report — do not improvise. When done, update the status row for this plan
> in `plans/README.md` — unless a reviewer dispatched you and told you they
> maintain the index.
>
> **Drift check (run first)**:
> `git diff --stat 75c4dce..HEAD -- hooks/ tests/ .pre-commit-config.yaml`
> If any in-scope file changed since this plan was written, compare the
> "Current state" excerpts against the live code before proceeding; on a
> mismatch, treat it as a STOP condition. (A `tests/` directory existing is
> EXPECTED if plan 011 landed — that is this plan's prerequisite, not drift.)

## Status

- **Priority**: P2
- **Effort**: M
- **Risk**: MED (touches the generation critical path; mitigated by the bake
  matrix and by keeping behavior changes minimal)
- **Depends on**: plans/011-root-guard-script-tests-and-reject-matrix.md
  (**hard** — it creates the root `tests/` directory and the `root-tests`
  pre-commit hook this plan extends)
- **Category**: tests / tech-debt
- **Planned at**: commit `75c4dce`, 2026-07-08

## Why this matters

The cookiecutter hooks are the template's core generation logic, and they
are Jinja-templated Python — which is exactly why they have zero tests
today. Two concrete hazards: (a) `hooks/post_gen_project.py` hand-maintains
`REMOVED_DIRS`/`REMOVED_PATHS` lists mirroring every knob-gated file; a
renamed template file leaves a stale entry that crashes generation with a
bare `FileNotFoundError` for combos the CI matrix doesn't bake, and nothing
catches the mistake before a user hits it. (b) The pure helpers —
`_parse_compose_version`, `_prune_celery_skill_metadata` — and every warning
branch run in zero tests; CI always has git+uv+docker available, so those
paths never execute anywhere. This plan adds a static existence guard for
the removal lists, a clear pre-flight error in the hook itself, and real
unit tests for the pure helpers.

## Current state

This repo is a **cookiecutter template**. `hooks/*.py` are rendered by Jinja
BEFORE execution (constants like `API_AUTH = {{ cookiecutter.api_auth |
tojson }}` become `API_AUTH = "session"`), then run with the generated
project as the working directory. They cannot be imported directly — root
tests must render them first (step 3 shows how). Root pre-commit EXCLUDES
`hooks/` from lint hooks (`.pre-commit-config.yaml:4`), so hook edits are
only checked by the bake matrix.

- `hooks/post_gen_project.py:35-120` — the removal lists. Shape (abridged;
  every entry is a plain string literal, no Jinja inside the lists):

```python
REMOVED_DIRS = [
    *(
        [".agents/skills/django-celery-expert"]
        if USE_CELERY == "none"
        else []
    ),
    *(["src/apps/notes", "tests/notes"] if USE_EXAMPLE_API == "no" else []),
]
REMOVED_PATHS = [
    *(["tests/utils.py"] if USE_EXAMPLE_API == "no" else []),
    # ... ~15 more knob-gated splats of string literals ...
]
```

- `hooks/post_gen_project.py:122-127` — the unguarded deletion:

```python
def main() -> None:
    for removed_path in REMOVED_PATHS:
        Path(removed_path).unlink()

    for removed_dir in REMOVED_DIRS:
        shutil.rmtree(removed_dir)
```

- `hooks/post_gen_project.py:172-193` — the pure helpers to test:

```python
def _parse_compose_version(output: str) -> tuple[int, int, int] | None:
    parts = re.findall(r"\d+", output)
    if not parts:
        return None

    version = [int(part) for part in parts[:3]]
    while len(version) < 3:
        version.append(0)

    return tuple(version)


def _prune_celery_skill_metadata() -> None:
    lock_path = Path("skills-lock.json")
    lock = json.loads(lock_path.read_text())
    lock["skills"].pop("django-celery-expert", None)
    lock_path.write_text(json.dumps(lock, indent=2) + "\n")

    readme_path = Path(".agents/README.md")
    lines = readme_path.read_text().splitlines(keepends=True)
    kept = [line for line in lines if "`django-celery-expert`:" not in line]
    readme_path.write_text("".join(kept))
```

- Jinja constants block at the top of the hook (`:7-33`): every templated
  line matches the exact pattern `NAME = {{ cookiecutter.name | tojson }}`.
  The knob names and defaults live in root `cookiecutter.json` (defaults:
  first list element for choice knobs, e.g. `api_auth` → `"session"`,
  `use_celery` → `"worker+beat"`).

- Root test infrastructure (from plan 011): stdlib `unittest` modules under
  `tests/`, discovered by the `root-tests` local pre-commit hook
  (`python -m unittest discover -s tests -t .`). Follow
  `tests/check_dockerfile_prod_env_test.py` as the structural pattern.

## Commands you will need

| Purpose | Command | Expected on success |
|---------|---------|---------------------|
| Root tests | `python -m unittest discover -s tests -t .` | `OK` |
| Root pre-commit | `uvx pre-commit run --all-files` | exit 0 |
| Bake (hook exercised end-to-end) | `uvx cookiecutter . -o /tmp/verify-013 --no-input use_celery=none use_example_api=no` | exit 0; project generated |
| Bake default | `uvx cookiecutter . -o /tmp/verify-013b --no-input` | exit 0 |

## Scope

**In scope**:

- `hooks/post_gen_project.py` — ONLY: add the pre-flight existence check in
  `main()` (step 1). No other behavior changes.
- `tests/hooks_test.py` (create)

**Out of scope** (do NOT touch):

- `hooks/pre_gen_project.py` — its validators are CI-covered after plan 011.
- Inverting the removal model (gated files self-declaring their knob) —
  attractive but a redesign; explicitly deferred (see Maintenance notes).
- `Path.unlink(missing_ok=True)` — REJECTED option: it would silently hide
  stale entries, which is worse than crashing.
- Anything under `{{cookiecutter.project_slug}}/`.

## Git workflow

- Conventional commits, e.g. `test: unit-test the post-gen hook and guard
  its removal lists`.
- Do NOT push unless instructed.

## Steps

### Step 1: Add a pre-flight existence check to `main()`

In `hooks/post_gen_project.py`, at the top of `main()` (before any
deletion), add:

```python
    missing = [
        entry
        for entry in [*REMOVED_PATHS, *REMOVED_DIRS]
        if not Path(entry).exists()
    ]
    if missing:
        sys.exit(
            "post_gen_project: removal-list entries not found in the "
            f"generated project (stale after a rename?): {missing}"
        )
```

Add `import sys` to the imports (alphabetical order within the import
block, matching the file's existing style). Generation still fails on a
stale entry — that is intended — but now with an actionable message instead
of a bare traceback, and all stale entries are reported at once.

**Verify**: `uvx cookiecutter . -o /tmp/verify-013 --no-input use_celery=none use_example_api=no`
→ exit 0 (all current entries exist, so the guard is silent);
`uvx cookiecutter . -o /tmp/verify-013b --no-input` → exit 0.

### Step 2: Add the static removal-list existence test

In new `tests/hooks_test.py`, add a test that catches stale entries WITHOUT
baking: read `hooks/post_gen_project.py` as text, slice out the region
between `REMOVED_DIRS = [` and the line `]` that closes `REMOVED_PATHS`
(the region ends at the first line that is exactly `]` following the
`REMOVED_PATHS = [` marker), extract every single-quoted or double-quoted
string literal with `re.findall(r'"([^"]+)"', region)`, and assert each
extracted path exists under `{{cookiecutter.project_slug}}/`:

```python
TEMPLATE_ROOT = Path("{{cookiecutter.project_slug}}")

class RemovalListsTest(unittest.TestCase):
    def test_every_removal_entry_exists_in_the_template_tree(self) -> None:
        ...
        for entry in entries:
            with self.subTest(entry=entry):
                self.assertTrue((TEMPLATE_ROOT / entry).exists())
```

Guard the extraction itself: assert `len(entries) >= 20` (today the two
lists contain 20+ literals) so a slicing regression fails loudly instead of
vacuously passing on an empty list.

**Verify**: `python -m unittest discover -s tests -t .` → `OK`. Then
temporarily check the test's teeth: it must FAIL if you add a bogus entry
string to the extraction fixture in a scratch copy — do this reasoning
check mentally or in `/tmp`, do NOT modify the real hook to test it.

### Step 3: Add a render-and-import helper and unit-test the pure helpers

In `tests/hooks_test.py`, add a helper that makes the templated hook
importable:

```python
HOOK_PATH = Path("hooks/post_gen_project.py")
JINJA_CONSTANT = re.compile(
    r"^(?P<name>[A-Z_]+) = \{\{ cookiecutter\.(?P<knob>\w+) \| tojson \}\}$",
    re.MULTILINE,
)
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


def _load_hook_module():
    source = JINJA_CONSTANT.sub(
        lambda m: f"{m.group('name')} = {json.dumps(TEST_CONTEXT[m.group('knob')])}",
        HOOK_PATH.read_text(),
    )
    module = types.ModuleType("post_gen_project")
    exec(compile(source, str(HOOK_PATH), "exec"), module.__dict__)  # noqa: S102
    return module
```

(If root ruff flags `exec`, keep the suppression comment style consistent
with how the repo suppresses elsewhere — grep for `noqa` in `scripts/`.)

Then add tests:

1. `_parse_compose_version("Docker Compose version v5.3.0")` →
   `(5, 3, 0)`
2. `_parse_compose_version("5.3")` → `(5, 3, 0)` (padding branch)
3. `_parse_compose_version("no digits here")` → `None`
4. `_prune_celery_skill_metadata`: in a `tempfile.TemporaryDirectory`, write
   a minimal `skills-lock.json` (copy the real shape:
   `{"version": 1, "skills": {"django-celery-expert": {...}, "postgres":
   {...}}}`) and a minimal `.agents/README.md` containing one
   `- \`django-celery-expert\`: ...` line and one other line; chdir into it
   (`contextlib.chdir`), call the function, assert the celery key is gone
   from the lock, the other skill remains, the README lost exactly the
   celery line, and the lock file ends with a trailing newline.

**Verify**: `python -m unittest discover -s tests -t .` → `OK`, with the
new tests counted (≥5 new).

### Step 4: Full check

```shell
uvx pre-commit run --all-files
uvx cookiecutter . -o /tmp/verify-013c --no-input use_celery=none
```

**Verify**: pre-commit exit 0 (root-tests hook includes the new module);
the `use_celery=none` bake succeeds and
`grep -c django-celery-expert /tmp/verify-013c/my-project/skills-lock.json`
→ `0`.

## Test plan

Steps 2–3 ARE the tests: one static invariant test (removal lists ↔
template tree), three `_parse_compose_version` branch tests, one
`_prune_celery_skill_metadata` behavior test. Pattern: plan 011's root
unittest modules.

## Done criteria

- [ ] `main()` pre-flights the removal lists with a clear `sys.exit` message
- [ ] `tests/hooks_test.py` exists; unittest discovery passes with ≥5 new
  tests including the ≥20-entries extraction guard
- [ ] Both bakes in step 1 and the bake in step 4 succeed
- [ ] `uvx pre-commit run --all-files` exits 0
- [ ] `git status` clean apart from `hooks/post_gen_project.py` and
  `tests/hooks_test.py`
- [ ] `plans/README.md` status row updated

## STOP conditions

Stop and report back if:

- Plan 011 has not landed (no root `tests/` or `root-tests` hook) — this
  plan cannot proceed without it.
- The Jinja-constant regex fails to render ALL templated lines in the hook
  (i.e. `exec` raises a `SyntaxError` mentioning `{{`) — the constants block
  has drifted from the `NAME = {{ cookiecutter.x | tojson }}` shape; report
  rather than loosening the regex blindly.
- The step-2 extraction finds fewer than 20 entries against the CURRENT
  hook — the list region slicing missed content; report.
- Any bake that succeeded before step 1 fails after it.

## Maintenance notes

- The static test catches STALE entries (listed but missing from the
  template). The inverse failure — a new knob-gated file FORGOTTEN from the
  lists, silently shipping into wrong combos — is NOT covered; catching it
  needs the removal model inverted (gated files self-declare their knob) or
  a Jinja-aware sweep of the template tree. Deferred: revisit if a
  forgotten-entry bug actually ships.
- When adding a knob-gated file, register it in `REMOVED_*` AND nothing
  else — the existence test will fail if you typo the path, which is the
  new safety net working.
- If a new Jinja constant is added to the hook, add its knob to
  `TEST_CONTEXT` or the render helper raises `KeyError` (loud, intended).
