# Plan 005: Fast local bake-and-lint gate for template source

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving to the
> next step. If anything in the "STOP conditions" section occurs, stop and
> report — do not improvise. When done, update the status row for this plan
> in `plans/README.md` — unless a reviewer dispatched you and told you they
> maintain the index.
>
> **Drift check (run first)**:
> `git diff --stat eee3978..HEAD -- .pre-commit-config.yaml scripts/`
> If any in-scope file changed since this plan was written, compare the
> "Current state" excerpts against the live code before proceeding; on a
> mismatch, treat it as a STOP condition.

## Status

- **Priority**: P2
- **Effort**: M
- **Risk**: LOW
- **Depends on**: plans/001-fix-bake-matrix-regressions.md (**hard** — until
  001 lands, this gate fails on main's known defects and cannot be committed
  green)
- **Category**: dx
- **Planned at**: commit `eee3978`, 2026-07-08

## Why this matters

Root pre-commit necessarily excludes `{{cookiecutter.project_slug}}/`
(Jinja-templated Python isn't parseable), so formatting/lint drift in template
source is invisible locally and only surfaces in the ~19-case CI bake matrix —
which the maintainer may not run for weeks (work happens on local `main`).
That gap shipped three of the four defects plan 001 fixes. A root-level check
that bakes a handful of render-diverse combos into a temp dir and runs the
pinned ruff over them takes well under a couple of minutes and catches this
whole defect class at commit time.

## Current state

This repo is a **cookiecutter template**; the root repo's own hooks live in
`.pre-commit-config.yaml`, whose `exclude` line is:

```yaml
exclude: ^(\{\{cookiecutter\.project_slug\}\}/|hooks/|plans/)
```

The root config already has a "Repo invariants" section of local hooks — the
exemplar to match exactly (`.pre-commit-config.yaml:88-102`):

```yaml
  # Repo invariants
  - repo: local
    hooks:
      - id: dockerfile-prod-env
        name: dockerfile production collectstatic env matches prod settings
        entry: python scripts/check_dockerfile_prod_env.py
        language: system
        pass_filenames: false
        always_run: true
      - id: postgres-image-pin
        name: postgres image pins agree across compose and workflows
        entry: python scripts/check_postgres_image.py
        language: system
        pass_filenames: false
        always_run: true
```

Existing root scripts live in `scripts/` (`check_dockerfile_prod_env.py`,
`check_postgres_image.py`, `__init__.py`) — read one before writing yours and
match its structure/style (constants top, `main()`, helpers under `# Utils`,
alphabetized; root `AGENTS.md` style rules apply: no
`from __future__ import annotations`, blank lines around control flow).
Note plan 022 recently edited `scripts/check_dockerfile_prod_env.py` (mock
env literals) — read the current version, not a cached memory of it.

The generated project pins ruff in
`{{cookiecutter.project_slug}}/.pre-commit-config.yaml` (ruff-pre-commit
`rev: v0.15.16` at the time of writing) — the gate must use THAT pin (the
generated project's, not the root's, though they currently match), read at
runtime so version bumps can't drift.

Render-diverse combos that cover the known failure surfaces (conditional
test files, import lattices, minimal renders):

1. default (no knobs)
2. `use_example_api=yes api_auth=token api_throttling=basic use_cors=yes use_csp=yes` (maximal)
3. `use_example_api=no use_celery=none email_provider=none use_sentry=no use_s3_media=no use_traefik=no` (minimal render)
4. `api_throttling=basic` (throttling without example API)
5. `email_provider=smtp` (smtp branches)

Baking uses `uvx cookiecutter . -o <tmpdir> --no-input <knobs>`. NOTE: baking
runs `hooks/post_gen_project.py`, which runs `git init` and `uv lock` in the
output dir — `uv lock` costs a few seconds per bake with a warm uv cache.
Total budget: aim under ~60s for all five combos; if `uv lock` dominates,
measure and, if needed, drop to 3 combos (1–3) and note it in the hook name.

## Commands you will need

| Purpose | Command | Expected on success |
|---------|---------|---------------------|
| Run the new gate directly | `python scripts/check_generated_format.py` | exit 0, per-combo PASS lines |
| Root hooks | `uvx pre-commit run --all-files` | all pass incl. new hook |
| Time it | `time python scripts/check_generated_format.py` | wall time noted |

## Scope

**In scope** (the only files you should modify/create):
- `scripts/check_generated_format.py` (create)
- `.pre-commit-config.yaml` (root — add the hook to the local repo block)
- Root `AGENTS.md` Verification section (one line mentioning the gate, only
  if the section enumerates root checks — check first; if it only says
  `pre-commit run --all-files`, no edit needed)

**Out of scope** (do NOT touch):
- `{{cookiecutter.project_slug}}/**` — the gate reads bakes; it never edits
  template source.
- `.github/workflows/ci.yaml` — CI already runs the full matrix; this gate is
  local-speed only. Do not add a CI job.
- `hooks/` — no changes to bake behavior.

## Git workflow

- Branch: `advisor/005-fast-local-format-gate`
- One commit, e.g. `ci: gate template source formatting on rendered bakes`.
- Do NOT push or open a PR unless the operator instructed it.

## Steps

### Step 1: Write `scripts/check_generated_format.py`

Behavior:
1. Read the ruff pin from
   `{{cookiecutter.project_slug}}/.pre-commit-config.yaml`: find the
   `astral-sh/ruff-pre-commit` repo block and take its `rev:` (strip the `v`).
   Fail with a clear message if not found.
2. For each combo (constant list `COMBOS`, the five above), bake into a
   `tempfile.mkdtemp()` dir via
   `uvx cookiecutter <repo-root> -o <tmp> --no-input <knobs>` (use
   `subprocess.run(..., check=...)`, capture output, print it on failure).
3. In each baked project dir, run `uvx ruff@<pin> format --check .` and
   `uvx ruff@<pin> check --no-fix .`; treat nonzero exit as failure and print
   the combo name plus ruff's output.
4. Clean up temp dirs (`finally`); exit 0 only if every combo passes; print
   one `PASS <combo>` line per success.

Style: match `scripts/check_postgres_image.py`'s shape. Alphabetize
constants. No third-party imports (stdlib only — the script runs under
`language: system`).

**Verify**: `python scripts/check_generated_format.py` → exit 0 with 5 PASS
lines (requires plan 001 landed; see STOP conditions).
`time` it — record wall seconds in the commit message body.

### Step 2: Wire the pre-commit hook

Add to the root `.pre-commit-config.yaml` local-hooks block, alphabetized by
id among the local hooks (`dockerfile-prod-env`, `generated-format`,
`postgres-image-pin`):

```yaml
      - id: generated-format
        name: generated projects pass ruff format and check
        entry: python scripts/check_generated_format.py
        language: system
        pass_filenames: false
        always_run: true
```

`always_run: true` (matching the neighbor hooks) is required, not laziness: a
`files:` filter on `{{cookiecutter.project_slug}}/` or `hooks/` paths can
never match because the config's global `exclude` strips those paths before
per-hook `files` matching, and narrowing the global exclude would expose
every other hook to unparseable Jinja. Accept the cost on every commit; it is
bounded by the timing budget above.

**Verify**: `uvx pre-commit run generated-format --all-files` → pass.
`uvx pre-commit run --all-files` → all hooks pass.

### Step 3: Prove the gate catches the defect class

Temporarily introduce plan-001's defect shape (add one extra blank line
between two module-level defs in
`'{{cookiecutter.project_slug}}/tests/core/unit/models_test.py'`), run
`python scripts/check_generated_format.py`, confirm it FAILS naming the
combo, then `git checkout` the file.

**Verify**: gate fails while the defect is present; `git status --short`
clean of that file afterwards; gate passes again.

## Test plan

Step 3 is the test (a deliberate red/green run). No pytest coverage — root
`scripts/` has no test harness (the two existing invariant scripts don't
either; consistent).

## Done criteria

Machine-checkable. ALL must hold:

- [ ] `python scripts/check_generated_format.py` exits 0 with one PASS line per combo
- [ ] `uvx pre-commit run --all-files` passes including `generated-format`
- [ ] Step 3 red/green demonstrated (describe in your report)
- [ ] Gate wall time recorded; if > 120s, report it as a concern
- [ ] `git status --short` shows only the in-scope files changed/created
- [ ] `plans/README.md` status row updated

## STOP conditions

Stop and report back (do not improvise) if:

- Plan 001 has not landed (the gate will fail on main's known defects —
  verify by running the gate; if it fails on
`admin_test.py`/`throttling_test.py`/`conftest.py`, 001 is missing: stop).
- `uv lock` inside the post-gen hook pushes total gate time past ~120s on
  your machine — report timings and the 3-combo fallback option instead of
  silently shipping a slow hook.
- The pinned-ruff parse of the generated `.pre-commit-config.yaml` is
  ambiguous (multiple ruff repo blocks).

## Maintenance notes

- When a knob is added, extend `COMBOS` if the knob introduces new
  conditional Python (settings components, tests); the constant is the
  single place to update.
- This gate makes formatting drift visible locally; it does NOT replace the
  CI matrix (which also runs pytest/migrations per combo).
- Future speedup option (deferred): a `COOKIECUTTER_SKIP_UV_LOCK`-style env
  toggle in the post-gen hook so the gate can skip `uv lock` — rejected for
  now to keep bake behavior identical everywhere.
