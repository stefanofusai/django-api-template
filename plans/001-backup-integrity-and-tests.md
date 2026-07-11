# Plan 001: Make backup verification and file handling fail safely

> **Executor instructions**: Follow every step and verification gate. Stop on
> any STOP condition; do not improvise. Update this plan's row in
> `plans/README.md` when complete unless a reviewer owns the index.
>
> **Drift check (run first)**: `rtk git diff --stat b367191..HEAD -- 'hooks/post_gen_project.py' '{{cookiecutter.project_slug}}/.docker/scripts/media-backup.sh' '{{cookiecutter.project_slug}}/.docker/scripts/postgres-backup.sh' '{{cookiecutter.project_slug}}/tests/config/unit/'`

## Status

- **Priority**: P1
- **Effort**: M
- **Risk**: LOW
- **Depends on**: none
- **Category**: bug, security, tests
- **Planned at**: commit `b367191`, 2026-07-10

## Why this matters

The generated media `verify` command pipes `tar -tzf` into `sed`; POSIX shell
therefore returns `sed`'s status and can report success after `tar` has emitted
one entry and failed. Database dumps, media archives, and their temporary files
also inherit the caller's umask, commonly making production data world-readable.
These are destructive recovery tools and currently have no automated tests.

## Current state

- `media-backup.sh:92-103` already checks archive readability and traversal
  before restore; preserve those checks.
- `media-backup.sh:140-146` derives `FIRST_ENTRY` from a pipeline and never
  separately checks `tar`'s exit status.
- `postgres-backup.sh:43` and `media-backup.sh:45` create temporary artifacts
  with shell redirection; neither script establishes `umask 077`.
- Tests for shell orchestration use executable stubs in
  `tests/config/unit/deploy_script_test.py`; match that pattern.
- The post-generation hook must remove each new test whenever it removes the
  corresponding script.

## Commands you will need

| Purpose | Command | Expected |
|---|---|---|
| Root tests | `rtk uvx pytest tests` | 21+ tests pass |
| Bake default | `rtk uvx cookiecutter . -o /tmp/plan-001-default --no-input` | project created |
| Bake local media | `rtk uvx cookiecutter . -o /tmp/plan-001-media --no-input use_s3_media=no` | project created |
| Baked suite | `rtk uv run pytest` | exit 0, coverage 100% |
| Broad checks | `rtk uv run pre-commit run --all-files` | exit 0 |

## Scope

**In scope**:
- `{{cookiecutter.project_slug}}/.docker/scripts/media-backup.sh`
- `{{cookiecutter.project_slug}}/.docker/scripts/postgres-backup.sh`
- `{{cookiecutter.project_slug}}/tests/config/unit/media_backup_script_test.py` (create)
- `{{cookiecutter.project_slug}}/tests/config/unit/postgres_backup_script_test.py` (create)
- `hooks/post_gen_project.py`

**Out of scope**:
- S3-provider backup implementation.
- Changing dump/archive formats or retention defaults.
- Real production restores in CI.

## Git workflow

Do not commit, push, or open a PR unless the operator explicitly asks. Preserve
unrelated work and use conventional commit wording if later asked to commit.

## Steps

### Step 1: Write failing shell-harness tests

Create both test modules using temporary directories and executable `docker`
and `tar` stubs. Cover at least:

- media verify: a fake `tar` prints one member and exits nonzero; command must
  fail and must not print `verify OK`;
- valid and empty media archives;
- unsafe absolute and parent-traversal archive members;
- refusal to restore while `api` or worker services run, plus `--force`;
- empty PostgreSQL dump refusal and temporary-file cleanup;
- retention keeps exactly the newest requested artifacts;
- final backup/archive mode is `0o600` even when the test process uses umask
  `0o022`.

Model helpers after `deploy_script_test.py`; never invoke a real Docker daemon.

**Verify**: focused tests fail specifically on masked `tar` status and file
mode assertions, not on harness setup.

### Step 2: Fix verification and sensitive file creation

Add `umask 077` near the top of both scripts before any sensitive file is
created. In `media-backup.sh verify`, first run and check
`tar -tzf "$ARCHIVE" >/dev/null`; only after it succeeds inspect the first
member to distinguish an empty but readable archive. Preserve exit codes and
existing messages where tests or README text depend on them.

**Verify**: both focused test modules pass.

### Step 3: Keep option pruning consistent

Add the PostgreSQL test path to the `POSTGRES != "compose"` removal block and
the media test path to the `USE_S3_MEDIA == "yes"` block. Keep paths ordered
with the corresponding script before its test.

**Verify**: root hook tests pass; default bake contains only the PostgreSQL
backup test, `use_s3_media=no` contains both, and `postgres=external` contains
neither the PostgreSQL script nor its test.

### Step 4: Run full rendered verification

In both exercised bakes copy `.env.example` to `.env`, start only Postgres,
run the full pytest suite and pre-commit, then tear Compose down with `-v`.

**Verify**: all commands exit 0 and both suites retain 100% coverage.

## Test plan

Use deterministic stubs for Docker responses and archive bytes. The regression
test for the pipeline must simulate partial output followed by nonzero exit;
a simply unreadable archive is insufficient because the old code already
rejects an empty listing.

## Done criteria

- [ ] Partial-output `tar` failure makes `verify` nonzero.
- [ ] Backups and temporary artifacts are owner-only.
- [ ] Restore refusal, force, traversal, retention, and cleanup paths are tested.
- [ ] Removal lists cover both new test files.
- [ ] Root tests, both baked suites, and both pre-commit runs pass.
- [ ] No source file outside Scope changed.

## STOP conditions

- A test requires weakening an existing restore safety check.
- BSD and GNU tar disagree on a real archive fixture; report both behaviors.
- The fix appears to require a new archive or dump format.

## Maintenance notes

Review future backup changes against both data integrity and local file modes.
The Docker stubs should assert complete argument lists so safety flags cannot
silently disappear.
