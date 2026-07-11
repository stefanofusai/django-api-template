# Plan 024: Evaluate a safe update path for already-generated projects

> **Executor instructions**: Prototype in disposable repositories only. Do
> not retrofit metadata into a real generated project without approval.
>
> **Drift check (run first)**: `rtk git diff --stat b367191..HEAD -- 'cookiecutter.json' 'hooks/' 'README.md' '{{cookiecutter.project_slug}}/'`

## Status

- **Priority**: P3
- **Effort**: M
- **Risk**: MED
- **Depends on**: plan 012
- **Category**: direction
- **Planned at**: commit `b367191`, 2026-07-10

## Why this matters

The template evolves quickly, but a baked service has no supported way to
replay security and operational improvements. Cruft can track Cookiecutter
provenance and update generated projects, but post-generation deletion,
generated locks, Git initialization, and `_copy_without_render` paths make
blind adoption risky.

## Current state

- Post-gen initializes Git, prunes many option-specific paths, and generates
  `uv.lock`.
- Generated projects are expected to diverge in application code.
- No template provenance metadata or update conflict policy exists.

## Commands you will need

| Purpose | Command | Expected |
|---|---|---|
| Bake baseline | `rtk uvx cookiecutter . -o /tmp/plan-024 --no-input` | created |
| Cruft check | `cruft check "$PROJECT"` | reports expected state |
| Project tests | `rtk uv run pytest` | pass before/after clean update |

## Scope

**In scope**:
- disposable two-version template/project prototype
- `docs/decisions/generated-project-updates.md` (create)
- Cruft comparison with a documented manual alternative

**Out of scope**:
- Automatically updating real downstream repositories.
- Requiring Cruft for first-time generation before approval.
- Resolving arbitrary downstream merge conflicts automatically.

## Git workflow

Use disposable repositories and local commits only where Cruft requires
history. Do not push them or modify a real downstream project.

## Steps

### Step 1: Build a representative downstream project

Bake default and maximal projects from commit `b367191`, make realistic
downstream edits in settings, notes, workflows, and README, and record initial
template context/provenance.

**Verify**: both projects pass their original suites before updating.

### Step 2: Prototype Cruft updates

Create a disposable later template revision changing one rendered file, one
pruned file, one copy-without-render workflow, one dependency, and one hook.
Run Cruft update and record clean updates, conflicts, deleted-file behavior,
lockfile behavior, and whether hooks/Git initialization rerun unexpectedly.

**Verify**: no downstream edit is silently overwritten.

### Step 3: Define conflict and verification policy

Specify which files are template-owned, downstream-owned, or merge-managed;
how feature-knob context is persisted; how locks regenerate; and the full
post-update verification command. Compare complexity with publishing upgrade
guides only.

### Step 4: Record adopt/defer verdict

Write commands, observed diffs, limitations, security implications, and
maintenance ownership. Implement metadata/docs only if the maintainer accepts
the conflict model.

## Test plan

Exercise clean update, conflicting downstream edit, deleted conditional file,
copy-without-render workflow, dependency/lock change, and post-gen side effects
in both default and maximal bakes.

## Done criteria

- [ ] Default and maximal update prototypes exist.
- [ ] Pruning, hooks, copy-without-render, locks, and downstream edits are tested.
- [ ] No silent overwrite is accepted.
- [ ] Adopt/defer verdict and manual fallback are documented.

## STOP conditions

- Cruft reruns destructive post-generation behavior during update.
- Feature context cannot faithfully reproduce the original bake.
- Downstream source edits are overwritten without a conflict.

## Maintenance notes

Revisit when at least one real generated project requests template updates or
when update guides become a recurring maintenance burden.
