# Plan 018: Keep option coverage while removing redundant bootstrap work

> **Executor instructions**: Measure before and after. Do not reduce branch
> coverage without an explicit map and passing plan 015 invariants.
>
> **Drift check (run first)**: `rtk git diff --stat b367191..HEAD -- '.github/workflows/ci.yaml' '.pre-commit-config.yaml' 'scripts/check_generated_format.py' 'hooks/post_gen_project.py' 'tests/'`

## Status

- **Priority**: P2
- **Effort**: M
- **Risk**: MED
- **Depends on**: plans 012 and 015
- **Category**: perf, dx
- **Planned at**: commit `b367191`, 2026-07-10

## Why this matters

Every one of 21+ bake variants performs a full locked sync, pytest suite,
migration gate, and generated pre-commit. The always-run local format guard
also performs five post-generation `git init`/`uv lock` bootstraps before ten
Ruff processes. Coverage is valuable, but bootstrap work is not the same as
rendering coverage.

## Current state

- Root CI matrix steps at `ci.yaml:139-154` are unconditional.
- `check_generated_format.py` renders five combinations sequentially.
- `post_gen_project.py` initializes Git and runs uv lock on every maintenance
  bake.
- Plan 015 adds named interaction coverage and a matrix invariant test; this
  plan must preserve it.

## Commands you will need

| Purpose | Command | Expected |
|---|---|---|
| Time local gate | `time rtk uv run --locked pre-commit run generated-format --all-files` | baseline recorded |
| Root tests | `rtk uv run --locked pytest tests` | pass |
| Workflow lint | `rtk uv run --locked pre-commit run check-github-workflows --all-files` | pass |

## Scope

**In scope**:
- `hooks/post_gen_project.py`
- `scripts/check_generated_format.py`
- `.pre-commit-config.yaml`
- `.github/workflows/ci.yaml`
- root tests for maintenance mode and matrix tiering

**Out of scope**:
- Removing any supported bake case.
- Reusing mutable virtualenvs across isolated matrix jobs.
- Renaming status checks.

## Git workflow

Do not commit or push unless explicitly requested.

## Steps

### Step 1: Record a coverage and timing baseline

For every matrix case, list the Jinja branches/interactions it uniquely covers,
current wall time, and whether full Django execution is necessary. Record local
generated-format wall time over two warm-cache runs.

**Verify**: every case has a coverage reason or is identified as redundant.

### Step 2: Add a side-effect-free maintenance render mode

Have `check_generated_format.py` set a narrowly named environment flag when
running Cookiecutter. In `post_gen_project.py`, that flag may skip only Git
initialization, `uv lock`, Compose warning probes, and next-step output; pruning
and Markdown normalization must still run exactly. Add hook tests proving
normal generation is unchanged and maintenance mode skips only side effects.

**Verify**: five render/Ruff cases pass without creating `.git` or `uv.lock`.

### Step 3: Tier the CI matrix

Add an explicit matrix field such as `full-checks`. All cases must still bake
and pass fast rendered syntax/format checks. A pairwise representative subset
covering every dependency and settings branch runs locked sync, full pytest,
migrations, and pre-commit. Keep default, maximal security/auth, minimal,
email-provider, and backing-topology representatives in the full tier.

**Verify**: the matrix invariant test proves each branch has at least one full
representative and every case has a render gate.

### Step 4: Compare results

Run the local guard and a CI test branch. Report before/after local duration,
aggregate runner minutes, and slowest critical-path duration. Require a
material improvement (target at least 30%) without lost checks.

**Verify**: all jobs green and timing target met.

## Test plan

Test maintenance-mode side effects, normal post-gen behavior, full/render-only
case classification, and branch-to-full-case coverage.

## Done criteria

- [ ] Every option case still renders and receives a fast correctness gate.
- [ ] Every material branch runs fully in at least one representative case.
- [ ] Normal Cookiecutter post-generation behavior is unchanged.
- [ ] Measured local/CI bootstrap cost materially decreases.

## STOP conditions

- A branch cannot be validated without the full generated suite and has no
  remaining full representative.
- Maintenance mode changes files compared with normal generation after
  excluding `.git`, `uv.lock`, and console output.
- Measured savings are below 30%; report rather than add complexity.

## Maintenance notes

Update the coverage map and matrix invariant whenever a new knob or conditional
dependency is added.
