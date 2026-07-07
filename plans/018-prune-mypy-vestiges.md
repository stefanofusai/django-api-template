# Plan 018: Remove the dead mypy/django-stubs configuration — and verify whether `ty` still needs the stubs package

> **Executor instructions**: Part A (delete inert config) is mechanical. Part B
> (the `django-stubs` dependency itself) is an **evidence-gated decision**: you
> remove the dependency ONLY if the experiment in Step B1 shows `ty` output is
> unchanged without it; otherwise you keep it and document why. Run every
> verification command. When done, update this plan's status row in
> `plans/README.md` — unless a reviewer dispatched you and told you they
> maintain the index.
>
> **Drift check (run first)**:
> `git diff --stat ae42991..HEAD -- "{{cookiecutter.project_slug}}/pyproject.toml" "{{cookiecutter.project_slug}}/.gitignore" "{{cookiecutter.project_slug}}/.docker/Dockerfile.dockerignore"`
> On a mismatch with "Current state", STOP. (Plan 016 adds lines to
> `Dockerfile.dockerignore` — different lines; reconcile if landed.)

## Status

- **Priority**: P3
- **Effort**: S
- **Risk**: LOW (Part A) / MED (Part B — only if the experiment justifies removal)
- **Depends on**: none
- **Category**: tech-debt
- **Planned at**: commit `ae42991`, 2026-07-07

## Repository context (read before anything else)

This is a **Cookiecutter template**; source under
`{{cookiecutter.project_slug}}/` (**quote in shell**). The generated project's
only type checker is **`ty`** (pre-commit hook `astral-sh/ty-pre-commit`,
config under `[tool.ty.*]` in `pyproject.toml`). There is no mypy anywhere:
no `[tool.mypy]`, no mypy hook, no mypy dependency. Verification means baking
and running the baked pre-commit (which includes the `ty --locked` hook).

## Why this matters

The generated project carries configuration for a type checker it does not
have:

- `[tool.django-stubs] django_settings_module = "config.settings"` — read
  ONLY by mypy's `mypy_django_plugin`. Nothing installs or configures that
  plugin, so the section is inert. A maintainer editing it (e.g. during a
  settings rename) is tuning a knob wired to nothing, and may wrongly assume
  django-stubs' settings-aware typing is active.
- `.gitignore` entries for `.mypy_cache/`, `.dmypy.json`, `dmypy.json` and a
  `.mypy_cache/` line in `Dockerfile.dockerignore` — caches of a tool that
  never runs.

Separately, `django-stubs==6.0.5` sits in the `ci` dependency group. Its
headline feature (the mypy plugin) is unreachable here — but its *static* PEP
561 stub files MAY be what `ty` resolves Django types from. Whether the
dependency earns its place is an empirical question this plan answers with an
experiment, not an assumption. (`django-stubs-ext==6.0.5` is a RUNTIME
dependency used by `src/config/settings/__init__.py` — it stays regardless.)

## Current state

`{{cookiecutter.project_slug}}/pyproject.toml`:
- line 33: `"django-stubs-ext==6.0.5",` (runtime deps — KEEP)
- line 49: `"django-stubs==6.0.5",` (ci group — Part B's subject)
- lines 90-91: `[tool.django-stubs]` / `django_settings_module = "config.settings"` (Part A: delete)
- lines 148-152: `[tool.ty.environment]` / `[tool.ty.src]` with `exclude = [".agents"]` (KEEP — the real type-checker config)

`{{cookiecutter.project_slug}}/.gitignore:178-181`:

```
# mypy
.mypy_cache/
.dmypy.json
dmypy.json
```

`{{cookiecutter.project_slug}}/.docker/Dockerfile.dockerignore:8`:
`.mypy_cache/` (file is kept sorted by the `file-contents-sorter` hook).

Baked ty hook: `.pre-commit-config.yaml` lines 53-59 —
`astral-sh/ty-pre-commit`, `id: ty`, `args: [--locked, --no-python-downloads]`.

## Commands you will need

| Purpose | Command | Expected |
|---------|---------|----------|
| Bake default | `uvx cookiecutter . --no-input -o /tmp/bake` | project |
| Run just ty | `cd /tmp/bake/my-project && git add -A && uv run pre-commit run ty --all-files` | `Passed` |
| Full baked pre-commit | `cd /tmp/bake/my-project && git add -A && uv run pre-commit run --all-files` | exit 0 |
| Baked tests | `cd /tmp/bake/my-project && DATABASE_URL=postgres://postgres:postgres@localhost:5432/postgres uv run pytest` | 100%, pass |
| Root pre-commit | (repo root) `uvx pre-commit run --all-files` | exit 0 |

## Scope

**In scope**:
- `{{cookiecutter.project_slug}}/pyproject.toml` — delete `[tool.django-stubs]`
  (Part A); possibly remove the `django-stubs` ci-group pin (Part B, evidence-gated).
- `{{cookiecutter.project_slug}}/.gitignore` — delete the 4 mypy lines (Part A).
- `{{cookiecutter.project_slug}}/.docker/Dockerfile.dockerignore` — delete
  `.mypy_cache/` (Part A).

**Out of scope**:
- `django-stubs-ext` (runtime, actively used — must stay).
- Any `[tool.ty.*]` change; any `# ty: ignore` marker in `src/`.
- Introducing mypy (the toolchain decision is ty; this plan removes the
  contradiction, not relitigates it).

## Git workflow

- Work directly on `main`. Do NOT branch/commit/push/PR unless told. If asked
  to commit: Conventional Commits, e.g. `chore: remove dead mypy configuration`.

## Steps

### Part A: delete the inert config

Remove `[tool.django-stubs]` + its one key from `pyproject.toml`; remove the
`# mypy` block (4 lines) from `.gitignore`; remove `.mypy_cache/` from
`Dockerfile.dockerignore`.

**Verify**:
```
uvx cookiecutter . --no-input -o /tmp/bake
grep -c "django-stubs\]" /tmp/bake/my-project/pyproject.toml      # 0 (the [tool.django-stubs] header)
grep -c "mypy" /tmp/bake/my-project/.gitignore                     # 0
grep -c "mypy" /tmp/bake/my-project/.docker/Dockerfile.dockerignore # 0
cd /tmp/bake/my-project && git add -A && uv run pre-commit run --all-files   # exit 0
```
(Note the pyproject grep targets the TABLE HEADER — the `django-stubs==` and
`django-stubs-ext==` dependency pins still match a plain `django-stubs` grep;
that is expected at this stage.)

### Part B: the dependency experiment

#### Step B1: measure ty with and without `django-stubs`

In the bake (NOT the template), capture a baseline then remove the package
and diff:

```
cd /tmp/bake/my-project
git add -A && uv run pre-commit run ty --all-files    # baseline: Passed
uv remove --group=ci django-stubs
git add -A && uv run pre-commit run ty --all-files    # experiment
```

Interpret:
- **Identical result (Passed, same diagnostics)** → `ty` does not consume the
  stubs; the dependency is dead weight. Proceed to B2.
- **New diagnostics appear** (unresolved Django attributes, changed inferred
  types) → `ty` WAS using the stubs. Do NOT remove it. Restore the bake,
  and instead add a one-line comment in the template's `pyproject.toml` next
  to the `django-stubs` pin stating the constraint the code can't show:
  it exists for its static stubs, consumed by ty (not for the mypy plugin).
  Record the observed diff in your report. Plan complete after Part A.

#### Step B2: (only on identical-result evidence) remove the pin from the template

Remove `"django-stubs==6.0.5",` from the ci group in the TEMPLATE's
`pyproject.toml` (keep `django-stubs-ext`). Re-bake fresh and run the FULL
gate set: baked pre-commit (ty included), baked pytest, root pre-commit.

**Verify**: all exit 0/pass on the fresh bake;
`grep -c '"django-stubs==' "{{cookiecutter.project_slug}}/pyproject.toml"` → 0
while `grep -c '"django-stubs-ext==' …` → 1.

## Test plan

- No new pytest (config-only; `AGENTS.md` forbids config-assertion tests).
  The gates are the baked ty hook (the tool whose behavior could change), the
  full baked suite, and the B1 experiment's captured before/after output —
  paste both runs' summaries into your report.

## Done criteria

ALL must hold:

- [ ] `[tool.django-stubs]` gone; mypy lines gone from `.gitignore` and `Dockerfile.dockerignore`.
- [ ] B1 experiment ran with captured before/after ty output in the report.
- [ ] EITHER `django-stubs` removed from the ci group (identical-output evidence) OR retained with an explanatory comment (diagnostic-diff evidence) — matching the experiment.
- [ ] Fresh default bake: `uv run pre-commit run --all-files` exit 0 (ty passes), `uv run pytest` 100%.
- [ ] `django-stubs-ext` pin untouched.
- [ ] Root pre-commit exit 0; no out-of-scope files modified; `plans/README.md` status row updated.

## STOP conditions

Stop and report (do not improvise) if:

- ty's behavior without the stubs is AMBIGUOUS (e.g. same exit code but
  subtly different diagnostics you can't classify) — paste both outputs and
  stop; do not remove on unclear evidence.
- Removing the pin breaks `uv lock`/`uv sync` resolution in some unexpected
  way (another package pins it — report which).
- You find an actual mypy invocation somewhere this plan's recon missed —
  the premise is wrong; stop.

## Maintenance notes

- If the outcome is "keep the dep for ty", revisit when ty's release notes
  announce first-party Django stub bundling or a stubs-resolution change —
  the comment in `pyproject.toml` is the breadcrumb.
- If the outcome is "removed", nothing further: `django-stubs-ext` remains the
  only stubs-family package, and it is runtime-justified.
- A reviewer should confirm the experiment ran against the ci group's locked
  env (`--locked` is in the ty hook args — a stale lock invalidates the
  comparison; `uv remove` updates the lock in the bake).
