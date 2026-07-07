# Plan 021: Spike — make `skills-lock.json` hashes enforceable, so vendored `.agents/` skills can't drift silently

> **Executor instructions**: This is a **spike**. Deliverable is a written
> recommendation on whether/how to enforce skill-hash integrity, plus a working
> proof if the mechanism is reliable — NOT necessarily a merged CI gate. If the
> verification mechanism is unreliable (see the known caveat), the correct
> outcome is "document, don't enforce." Update this plan's status row in
> `plans/README.md` when the proposal is written.
>
> **Drift check (run first)**:
> `git diff --stat ae42991..HEAD -- "{{cookiecutter.project_slug}}/skills-lock.json" .github/workflows/ci.yaml .pre-commit-config.yaml`
> On a mismatch with "Current state", note it in the proposal.
>
> **Naming caution**: your deliverable is a NEW file,
> `plans/021-skill-verification-DESIGN.md`. Do not overwrite this plan file.

## Status

- **Priority**: P3 (spike)
- **Effort**: S
- **Risk**: LOW (no gate merged without acceptance)
- **Depends on**: none (interacts with 003/012 — any gate must be re-baselined after skills are added or pruned)
- **Category**: security
- **Planned at**: commit `ae42991`, 2026-07-07

## Repository context (read before anything else)

This is a **Cookiecutter template**. Vendored skills live under
`{{cookiecutter.project_slug}}/.agents/skills/<name>/` with a
`{{cookiecutter.project_slug}}/skills-lock.json` manifest recording, per skill:
`source` (an `owner/repo` string), `sourceType` (`"github"`), `skillPath` (a
path to the upstream `SKILL.md`), and `computedHash` (a hex content hash).

The manifest is *believed* to be produced by **`vercel-labs/skills`**
(`npx skills`) — the lock-file shape matches that tool — but **no file in the
repo names the tool** (`.agents/README.md` only says "copied from upstream
repositories"). Confirming the tool identity is part of Step 1: if
`npx skills --help` doesn't recognize this layout, that itself is a finding for
the DESIGN doc.

- `.agents/` is excluded from Ty and pre-commit; the vendored content is
  otherwise unchecked.
- The repo-root `.github/workflows/ci.yaml` is the template's own CI; the
  repo-root `.pre-commit-config.yaml` lints the template's tracked files (it
  `exclude`s `{{cookiecutter.project_slug}}/` — a `local` hook with
  `pass_filenames: false`/`always_run: true` bypasses that, as in plan 010).
- Verification means running the skills CLI against the template's vendored trees
  and (if wiring a gate) actionlint/pre-commit.

## Why this matters

`skills-lock.json` records a `computedHash` per vendored skill — a clear signal
of intent to detect drift — but **nothing recomputes or verifies those hashes**.
Because `.agents/` is excluded from every linter, a local edit or a partial
re-vendor can silently diverge the committed skill content from its recorded
hash. The "lock" is currently descriptive, not enforced. A verification step
(pre-commit and/or CI) would make the lock meaningful and catch accidental edits
to third-party skill copies.

**Known caveat (must be evaluated, not assumed away):** the `skills` CLI's
`computedHash` semantics have had reliability issues — reports that
`computedHash cannot be verified against installed files`, and guidance to treat
the hash as tool-defined rather than a portable cryptographic guarantee. So the
first job of this spike is to determine whether `npx skills verify` (or the
installed equivalent) actually works against this repo's vendored trees. If it
does not, enforcing it would produce false CI failures — the recommendation would
then be a different mechanism (self-computed content hashes) or docs-only.

## Current state

`{{cookiecutter.project_slug}}/skills-lock.json` records `computedHash` for each
of the three (soon six, if plan 012 lands) skills. No workflow or hook references
`skills`, `computedHash`, or verifies `.agents/` content:
`grep -rn "skills verify\|computedHash" .github .pre-commit-config.yaml` returns
**zero matches** (the lock file itself lives outside that grep's scope; repo-wide,
the only hits are the lock file and the `plans/` directory).

**Conventions**: extended YAML block style; pin any action/tool version exactly;
`local` pre-commit hooks use `pass_filenames: false` + `always_run: true` to read
excluded paths.

## The questions this spike must answer

1. **Does `npx skills verify` (or the installed command) reliably confirm the
   committed `.agents/skills/` trees against `skills-lock.json` on this repo?**
   Run it; record exit code and output. Try it after a deliberate one-character
   edit to a vendored `SKILL.md` — does it fail as it should? Revert the edit.
2. **If reliable:** where should the gate live — a repo-root `local` pre-commit
   hook, a CI step in `ci.yaml`, or both? (Pre-commit gives fast local feedback;
   CI guarantees it on PRs.) Does it need Node available in that context?
3. **If unreliable:** is a self-computed content hash (e.g. a small script that
   hashes each skill tree and compares to a value the repo controls) a better
   fit, or is docs-only ("re-vendor via `npx skills`; do not hand-edit
   `.agents/`") the honest answer given `.agents/` is meant to be vendored, not
   authored?
4. **Scope of enforcement:** the template repo's own vendored skills only, or
   also a baked-project check (a `skills verify` step in the generated CI)? The
   generated project also carries the lock, so drift can happen downstream too.

## Deliverables

1. **`plans/021-skill-verification-DESIGN.md`** (create): the reliability finding
   (with captured command output for the clean case and the deliberate-drift
   case), the recommended mechanism (CLI `verify` / self-hash / docs-only), where
   it should run, and an explicit "open questions for the maintainer" list.
2. **A working proof** if the mechanism is reliable: the exact pre-commit hook
   and/or CI step, demonstrated to pass on the clean repo and fail on an injected
   edit — shown in a scratch/uncommitted form (do NOT merge the gate into the
   committed template until the recommendation is accepted).

## Commands you will need

| Purpose | Command | Expected |
|---------|---------|----------|
| CLI help | `npx skills --help` / `npx skills verify --help` | shows `verify` (or equivalent) |
| Verify clean | `cd "{{cookiecutter.project_slug}}" && npx skills verify` | records exit code + output |
| Verify after drift | edit one vendored `SKILL.md`, re-run verify, then `git checkout` the edit | must fail on the edit |
| actionlint (if wiring CI) | (repo root) `uvx pre-commit run actionlint check-github-workflows --all-files` | exit 0 |
| Root pre-commit | (repo root) `uvx pre-commit run --all-files` | exit 0 |

**Network + Node required** for `npx skills`. If unavailable, STOP (can't evaluate).

## Scope

**In scope**:
- `plans/021-skill-verification-DESIGN.md` (create).
- A scratch/uncommitted proof of the hook or CI step.
- Only if the recommendation is accepted AND the executor is told to proceed:
  `.pre-commit-config.yaml` and/or `.github/workflows/ci.yaml` (repo root), plus a
  helper script if a self-hash approach wins.

**Out of scope**:
- Modifying the vendored skill content or `skills-lock.json` (that is 003/012).
- Merging an enforcement gate without an accepted recommendation.
- The Ty/pre-commit `.agents/` exclusions.

## Git workflow

- Work directly on `main`. Do NOT branch/commit/push/PR unless told. If asked to
  commit an accepted mechanism: Conventional Commits, e.g.
  `ci: verify vendored skill hashes against skills-lock.json`.

## Steps

### Step 1: Evaluate the CLI's verify reliability

Run `npx skills verify` against the committed vendored trees; capture exit code +
output. Then inject a one-character change into one `SKILL.md`, re-run, capture
the result, and `git checkout` to revert. Record both outcomes verbatim in the
DESIGN doc.

**Verify**: DESIGN doc shows the clean-case and drift-case output; you can state
definitively whether the CLI verify is trustworthy on this repo.

### Step 2: Choose a mechanism and prototype it

- **If CLI verify is reliable**: prototype a repo-root `local` pre-commit hook
  (`pass_filenames: false`, `always_run: true`, `entry: npx skills verify …`) and,
  optionally, a CI step. Confirm it passes clean and fails on the injected edit.
- **If unreliable**: prototype a self-computed hash script (hash each skill tree,
  compare to a repo-controlled value) OR write the docs-only recommendation.
  Capture which and why.

**Verify**: the chosen prototype passes on the clean repo and fails on drift
(scratch/uncommitted).

### Step 3: Write the proposal and STOP

Populate `plans/021-skill-verification-DESIGN.md` with the reliability finding,
the recommended mechanism + location, the baked-project-scope decision (question
4), the exact hook/step, and open questions. Report and STOP for the maintainer's
decision; do not merge a gate unless told to proceed.

## Done criteria

ALL must hold:

- [ ] `plans/021-skill-verification-DESIGN.md` exists with captured clean-case and drift-case `verify` output and a definitive reliability finding.
- [ ] A recommended mechanism (CLI verify / self-hash / docs-only) with rationale, and where it should run.
- [ ] A working scratch prototype that passes clean and fails on injected drift (unless the recommendation is docs-only, in which case the DESIGN says why enforcement is not viable).
- [ ] An explicit "open questions for the maintainer" section (incl. baked-project scope).
- [ ] No enforcement gate merged into the committed template unless accepted and instructed (`git status` shows only `plans/` unless told otherwise).
- [ ] `plans/README.md` status row updated.

## STOP conditions

Stop and report (do not improvise) if:

- `npx`/Node or network is unavailable (can't evaluate).
- The CLI `verify` produces false failures on the clean repo (the known caveat is
  real here) — recommend self-hash or docs-only rather than a flaky gate.
- Enforcing verification would require un-excluding `.agents/` from other linters
  (it should not — the check is standalone).

## Maintenance notes

- Interacts with plans 003 and 012: any hash-verification gate must be re-run /
  re-baselined after skills are added (012) or pruned (003), or it will flag those
  intended changes. Note this dependency in the DESIGN.
- If the maintainer accepts a gate, Dependabot/Renovate support for skills.sh
  sources (discussed upstream) would complement it — mention as a future option.
- Keep the recommendation honest: if `.agents/` is meant to be freely re-vendored
  and never hand-edited, a documented "re-vendor, don't edit" rule may be enough,
  and a flaky hash gate would be worse than nothing.
