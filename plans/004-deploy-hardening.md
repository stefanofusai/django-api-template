# Plan 004: Harden deployment state updates and prove orchestration

> **Executor instructions**: Run every verification and stop on the conditions
> below. Update the plan index when complete.
>
> **Drift check (run first)**: `rtk git diff --stat 20ec7c5..HEAD -- '{{cookiecutter.project_slug}}/.docker/scripts/deploy.sh' '{{cookiecutter.project_slug}}/tests/config/unit/deploy_script_test.py' '{{cookiecutter.project_slug}}/README.md'`

## Status

- **Priority**: P1
- **Effort**: M
- **Risk**: LOW
- **Depends on**: plan 003
- **Category**: bug, security, tests
- **Planned at**: commit `20ec7c5`, 2026-07-10

## Why this matters

`deploy.sh` replaces only the first `APP_VERSION`, so a stale later duplicate
can remain authoritative. Its temporary `.env` inherits the caller's umask and
can weaken a private credential file to mode 0644. Existing tests record every
Docker invocation but never assert the log, so dropping rollout, `--wait`, or
pull would remain green. The README also installs `docker-rollout` from a
mutable tag without integrity verification.

## Current state

- `deploy.sh:39-57` uses a predictable `.env.tmp.$$` and replaces only the
  first matching assignment.
- `deploy.sh:59-63` requires pull, optional rollout, and `up -d --wait`.
  Plan 003 adds the final in-container readiness probe; include it in the
  orchestration assertions rather than removing or duplicating it.
- `deploy_script_test.py:58-75` writes `docker.log` but never reads it.
- `README.md:538-545` downloads and executes the plugin without a digest.
- Plan 003 is complete but intentionally uncommitted. Before changing these
  files, import the current `deploy.sh`, `deploy_script_test.py`, and `README.md`
  from its preserved worktree as this plan's dependency baseline. Review plan
  004's incremental diff against that imported baseline as well as the combined
  diff against `20ec7c5`.

## Commands you will need

| Purpose | Command | Expected |
|---|---|---|
| Focused test | `rtk uv run pytest tests/config/unit/deploy_script_test.py -q` | pass |
| Shell lint | `rtk uv run pre-commit run shellcheck --all-files` | exit 0 |
| Root checks | `rtk uvx pre-commit run --all-files` | exit 0 |

## Scope

**In scope**:
- `{{cookiecutter.project_slug}}/.docker/scripts/deploy.sh`
- `{{cookiecutter.project_slug}}/tests/config/unit/deploy_script_test.py`
- `{{cookiecutter.project_slug}}/README.md`

**Out of scope**:
- Changing the release tag format.
- Replacing docker-rollout with another orchestrator.
- Database rollback automation.

## Git workflow

Do not commit or push unless explicitly requested.

## Steps

### Step 1: Expand failing deploy tests

Assert exact ordered Docker log entries for pull, rollout when enabled,
`compose up -d --wait`, and plan 003's final readiness probe. Add cases for
duplicate `APP_VERSION`, missing `.env`,
help, absent docker-rollout, invalid tags, and failure propagation from each
Docker phase. Under a permissive umask, assert the rewritten `.env` is 0600.

**Verify**: duplicate, mode, and orchestration assertions fail on current code.

### Step 2: Rewrite `.env` atomically and canonically

Set `umask 077`; create the temporary file with portable `mktemp` in the same
directory; have `awk` emit exactly one requested `APP_VERSION` and discard all
later duplicates; rename atomically. Keep the trap for every failure/signal.

**Verify**: focused tests pass and no `.env.tmp.*` remains after forced failure.

### Step 3: Pin and verify docker-rollout installation

Replace the tag-based raw URL with an immutable upstream commit URL. Compute
and document the SHA-256 for exactly those bytes, download to a temporary file,
verify with `sha256sum -c -`, then install and mark executable. Add a short
maintenance note explaining that commit and digest must change together.

Do not invent a digest. Resolve the current `v0.13` commit and compute it from
the downloaded file during implementation; record both in the README diff.

**Verify**: a copied command block succeeds for correct bytes and fails before
`chmod` after one byte is altered.

### Step 4: Run rendered verification

Bake Traefik and no-Traefik projects; run the focused tests in both, then full
pytest and pre-commit in one representative bake.

**Verify**: all pass at 100% coverage; root pre-commit passes.

## Test plan

The Docker stub must fail if commands are omitted or reordered. Include
duplicate version lines both before and after unrelated values and inspect
final file mode with `stat.S_IMODE`.

## Done criteria

- [ ] `.env` contains exactly one requested `APP_VERSION` at mode 0600.
- [ ] Pull, rollout, readiness/wait, and failure propagation are asserted.
- [ ] docker-rollout installation is commit-pinned and checksum-verified.
- [ ] Traefik and no-Traefik focused tests pass.

## STOP conditions

- The upstream tag cannot be resolved to immutable content.
- Portable same-directory `mktemp` semantics differ on supported Linux/macOS
  shells; report rather than falling back to predictable names.
- A test requires ignoring a failed Docker command.

## Maintenance notes

Treat `.env` as a credential file. Reviewers should compare the documented
plugin commit, URL, and digest as one atomic update.
