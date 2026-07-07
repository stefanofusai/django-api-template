# Plan 003: Prune the `django-celery-expert` agent skill when `use_celery=none`

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving on. If
> anything in "STOP conditions" occurs, stop and report — do not improvise. When
> done, update this plan's status row in `plans/README.md` — unless a reviewer
> dispatched you and told you they maintain the index.
>
> **Drift check (run first)**:
> `git diff --stat ae42991..HEAD -- hooks/post_gen_project.py "{{cookiecutter.project_slug}}/skills-lock.json" "{{cookiecutter.project_slug}}/.agents/README.md"`
> If any of these changed since this plan was written, compare the "Current
> state" excerpts against the live files before proceeding; on a mismatch, STOP.

## Status

- **Priority**: P1
- **Effort**: S
- **Risk**: LOW
- **Depends on**: none (but coordinates with plans 005 — same hook file — and 012 — same lock file; see plans/README.md)
- **Category**: bug
- **Planned at**: commit `ae42991`, 2026-07-07

## Repository context (read before anything else)

This is a **Cookiecutter template**. Project source is under
`{{cookiecutter.project_slug}}/` — **quote it in shell**.

- `hooks/post_gen_project.py` runs **after** cookiecutter renders and copies all
  files. It already deletes knob-disabled files (`REMOVED_PATHS`) and directories
  (`REMOVED_DIRS`) from the generated project on disk. This is the right place to
  prune `.agents/` content: the hook edits the copied files, so the
  `_copy_without_render` exclusion (which only affects Jinja rendering, not
  post-gen deletion) does not block it.
- `{{cookiecutter.project_slug}}/.agents/*` and `.github/workflows/*` are copied
  **without Jinja rendering**. That means you CANNOT gate `.agents/README.md` or
  `skills-lock.json` content with `{%- if %}` — the pruning must be done
  imperatively in the post-gen hook.
- `hooks/post_gen_project.py` itself is a **rendered** file (it contains
  `{{ cookiecutter.* | tojson }}` at the top), so Jinja is valid there.
- Verification means baking: `uvx cookiecutter . --no-input -o /tmp/bake [key=value …]`.

## Why this matters

The template's knob→deletion logic is otherwise airtight: bake with
`use_celery=none` and you get no `celery.py`, no tasks module, no Celery
dependency, no worker/beat scripts. But three Celery **agent-skill** artifacts
survive that bake:

- `.agents/skills/django-celery-expert/` — 8 files (a `SKILL.md` plus 7 under
  `references/`) of authoritative Celery guidance for agents working in the
  repo.
- the `django-celery-expert` entry in `skills-lock.json`.
- the `django-celery-expert` bullet in `.agents/README.md`.

An agent opening a `use_celery=none` project reads a vendored skill instructing
it on a task queue that does not exist — the one dangling-reference case the knob
logic misses. Pruning all three when Celery is off makes the `.agents/` surface
match the actual project, consistent with how every other disabled feature is
handled.

## Current state

`hooks/post_gen_project.py` (relevant excerpts — the file reads knobs into
module constants, then deletes paths/dirs in `main()`):

```python
POSTGRES = {{ cookiecutter.postgres | tojson }}
TRAEFIK_TLS = {{ cookiecutter.traefik_tls | tojson }}
USE_CELERY = {{ cookiecutter.use_celery | tojson }}
USE_EXAMPLE_API = {{ cookiecutter.use_example_api | tojson }}
USE_SENTRY = {{ cookiecutter.use_sentry | tojson }}
USE_TRAEFIK = {{ cookiecutter.use_traefik | tojson }}
# ...
REMOVED_PATHS = [
    *(
        [
            ".docker/scripts/celery-beat.sh",
            ".docker/scripts/celery-worker.sh",
            "src/config/celery.py",
            "src/config/settings/components/celery.py",
            "tests/config/unit/celery_test.py",
        ]
        if USE_CELERY == "none"
        else []
    ),
    # ... more conditional entries ...
]
REMOVED_DIRS = [
    *(["src/apps/notes", "tests/notes"] if USE_EXAMPLE_API == "no" else []),
]
# ...

def main() -> None:
    for removed_path in REMOVED_PATHS:
        Path(removed_path).unlink()

    for removed_dir in REMOVED_DIRS:
        shutil.rmtree(removed_dir)

    for markdown_file in MARKDOWN_FILES:
        path = Path(markdown_file)
        text = path.read_text()
        path.write_text(re.sub(r"\n{3,}", "\n\n", text))
    # ... git init, uv lock, compose-version warning, next-steps print ...
```

`{{cookiecutter.project_slug}}/skills-lock.json` (full file today):

```json
{
  "version": 1,
  "skills": {
    "django-celery-expert": {
      "source": "vintasoftware/django-ai-plugins",
      "sourceType": "github",
      "skillPath": "plugins/django-celery-expert/skills/SKILL.md",
      "computedHash": "31eb59e33c4251087afc81387abf26502814885921b93c9c9afa06090c3495ca"
    },
    "django-expert": { "...": "..." },
    "postgres": { "...": "..." }
  }
}
```

`{{cookiecutter.project_slug}}/.agents/README.md` (full file today):

```markdown
# Vendored Agent Skills

The generated project vendors agent-skill instructions for local development.
They are copied from upstream repositories under redistributable licenses:

- `django-celery-expert`: `vintasoftware/django-ai-plugins`, MIT.
- `django-expert`: `vintasoftware/django-ai-plugins`, MIT.
- `postgres`: `planetscale/database-skills`, MIT.
```

**Conventions (from `AGENTS.md`)**:
- `hooks/post_gen_project.py` is plain Python once rendered — follow Ruff
  formatting/linting. Prefer clear explicit code.
- `.agents/` stays excluded from Ty and pre-commit — do not change those
  exclusions.

## Commands you will need

| Purpose | Command | Expected |
|---------|---------|----------|
| Bake celery-off | `uvx cookiecutter . --no-input -o /tmp/bake-nc use_celery=none` | project with no celery |
| Bake default | `uvx cookiecutter . --no-input -o /tmp/bake` | project with celery |
| Check skill dir gone | `test ! -d /tmp/bake-nc/my-project/.agents/skills/django-celery-expert && echo OK` | `OK` |
| Check skill dir present (default) | `test -d /tmp/bake/my-project/.agents/skills/django-celery-expert && echo OK` | `OK` |
| Baked pre-commit | `cd /tmp/bake-nc/my-project && git add -A && uv run pre-commit run --all-files` | exit 0 |
| Root pre-commit | (repo root) `uvx pre-commit run --all-files` | exit 0 |

## Scope

**In scope**:
- `hooks/post_gen_project.py` — add the imperative pruning when `USE_CELERY == "none"`.

**Out of scope**:
- `{{cookiecutter.project_slug}}/skills-lock.json` and `.agents/README.md` — do
  NOT add Jinja to these (they are copied unrendered). They are edited *at bake
  time by the hook*, not in the template source.
- The `.agents/` Ty/pre-commit exclusions.
- Adding a skill (that is plan 012). This plan only removes the Celery skill when
  Celery is off.

## Git workflow

- Work directly on `main`. Do NOT branch/commit/push/PR unless told. If asked to
  commit: Conventional Commits, e.g.
  `fix: prune django-celery-expert skill when use_celery=none`.

## Steps

### Step 1: Remove the skill directory when Celery is off

Add `.agents/skills/django-celery-expert` to `REMOVED_DIRS` conditionally on
`USE_CELERY == "none"`:

```python
REMOVED_DIRS = [
    *(["src/apps/notes", "tests/notes"] if USE_EXAMPLE_API == "no" else []),
    *(
        [".agents/skills/django-celery-expert"]
        if USE_CELERY == "none"
        else []
    ),
]
```

`main()` already `shutil.rmtree`s each entry in `REMOVED_DIRS`, so no change to
`main()` is needed for the directory removal.

### Step 2: Drop the lock entry and the README bullet when Celery is off

`skills-lock.json` is JSON and `.agents/README.md` is Markdown; neither can hold
Jinja, so edit them on disk in the hook. Add a helper and call it from `main()`
under the `USE_CELERY == "none"` condition. Target shape:

```python
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

Add `import json` to the existing import block. Note: nothing lints this file
(the root pre-commit `exclude`s `hooks/`, and pre-render it is not valid Python
anyway because of the Jinja constants), so the goal is only to match the
existing layout — the current block is `from pathlib import Path` / `import re`
/ `import shutil` / `import subprocess`; put `import json` immediately before
`import re`. Call the helper in `main()` right after the `REMOVED_DIRS` loop,
guarded:

```python
    if USE_CELERY == "none":
        _prune_celery_skill_metadata()
```

**Important — match the existing JSON formatting exactly.** The current
`skills-lock.json` uses 2-space indentation and a trailing newline. Confirm your
`json.dumps(..., indent=2) + "\n"` reproduces byte-identical formatting for the
*surviving* keys by diffing a default bake against the committed file (Step 4).
If `json.dumps` reorders or reformats anything, adjust (e.g. preserve key order —
`json.loads` preserves insertion order in Python 3.7+, so `django-expert` and
`postgres` stay in order after popping `django-celery-expert`).

**Verify**: see Steps 3–4.

### Step 3: Bake celery-off and confirm all three artifacts are gone

```
uvx cookiecutter . --no-input -o /tmp/bake-nc use_celery=none
test ! -d /tmp/bake-nc/my-project/.agents/skills/django-celery-expert && echo DIR_OK
grep -c "django-celery-expert" /tmp/bake-nc/my-project/skills-lock.json      # expect 0
grep -c "django-celery-expert" /tmp/bake-nc/my-project/.agents/README.md     # expect 0
cd /tmp/bake-nc/my-project && git add -A && uv run pre-commit run --all-files
```

**Verify**: `DIR_OK` printed; both greps return `0`; baked pre-commit exits 0.
**The baked pre-commit does NOT validate `skills-lock.json`** (its only JSON
hooks are `check-dependabot`/`check-github-workflows`, which are file-specific,
and `.agents/` is excluded anyway) — so validate the JSON explicitly:

```
python -c "import json; json.load(open('/tmp/bake-nc/my-project/skills-lock.json'))"
```

→ exits 0.

### Step 4: Bake default and confirm the Celery skill is UNTOUCHED

The default bake (`use_celery=worker+beat`) must keep all three artifacts and
`skills-lock.json` must be byte-identical to the committed template file (the
hook only rewrites it when Celery is off — confirm it does not rewrite it
otherwise, OR that rewriting it produces identical bytes):

```
uvx cookiecutter . --no-input -o /tmp/bake
test -d /tmp/bake/my-project/.agents/skills/django-celery-expert && echo DIR_OK
diff /tmp/bake/my-project/skills-lock.json "{{cookiecutter.project_slug}}/skills-lock.json"
grep -c "django-celery-expert" /tmp/bake/my-project/.agents/README.md   # expect 1
```

**Verify**: `DIR_OK`; `diff` shows no differences; README grep returns `1`.

### Step 5: Regression — root pre-commit and worker-only bake

```
# worker-only still has celery, so the skill must remain:
uvx cookiecutter . --no-input -o /tmp/bake-wo use_celery=worker
test -d /tmp/bake-wo/my-project/.agents/skills/django-celery-expert && echo OK
# repo-root regression (note: this does NOT lint hooks/ — the root pre-commit
# excludes it; style-check your hook edit by eye against the existing code):
cd <repo root> && uvx pre-commit run --all-files
```

**Verify**: `OK`; root pre-commit exits 0. Since no linter covers
`hooks/post_gen_project.py`, the real gate for your edit is the bake matrix in
Steps 3-5 (a syntax error in the hook fails every bake loudly).

## Test plan

- No pytest test (the hook is not importable as normal Python — it contains
  Jinja pre-render). Verification is the bake matrix in Steps 3–5.
- Cover all three `use_celery` values: `none` (skill pruned), `worker` and
  `worker+beat` (skill retained).

## Done criteria

ALL must hold:

- [ ] `use_celery=none` bake: no `.agents/skills/django-celery-expert/` dir, no `django-celery-expert` in `skills-lock.json` or `.agents/README.md`, and `skills-lock.json` is valid JSON.
- [ ] `use_celery=worker` and default bakes: all three artifacts present; default-bake `skills-lock.json` byte-identical to the committed template file.
- [ ] Baked pre-commit exits 0 on both a celery-off and a default bake.
- [ ] Root `uvx pre-commit run --all-files` exits 0.
- [ ] No files outside `hooks/post_gen_project.py` modified (`git status`).
- [ ] `plans/README.md` status row updated.

## STOP conditions

Stop and report (do not improvise) if:

- Any of the three "Current state" excerpts no longer matches the live file.
- `json.dumps(indent=2)` cannot reproduce the committed `skills-lock.json`
  formatting byte-for-byte for surviving keys (report the diff; the maintainer
  may prefer a text-surgical edit over parse-and-redump).
- Removing the README bullet would leave a malformed list (e.g. the bullet
  format differs from the excerpt) — report it.

## Maintenance notes

- If more optional, feature-specific skills are vendored later (e.g. a storage
  or email skill gated on a knob), extend the same pattern: dir removal in
  `REMOVED_DIRS`, plus a lock/README prune in the hook.
- A reviewer should confirm the JSON rewrite is deterministic and the surviving
  entries keep insertion order, and that the default bake is provably unchanged.
- Interacts with plan 012 (vendor three more skills): if 015 lands first, this
  plan's celery-off assertions are unaffected (012 adds unconditional skills),
  but re-confirm the `skills-lock.json` byte-identity check against the
  post-012 committed file.
