# Plan 001: Make `postgres-backup.sh` fail safe — never leave a corrupt "newest" dump, and prune portably

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving on. If
> anything in "STOP conditions" occurs, stop and report — do not improvise. When
> done, update this plan's status row in `plans/README.md` — unless a reviewer
> dispatched you and told you they maintain the index.
>
> **Drift check (run first)**:
> `git diff --stat ae42991..HEAD -- "{{cookiecutter.project_slug}}/.docker/scripts/postgres-backup.sh"`
> If the file changed since this plan was written, compare the "Current state"
> excerpt against the live file before proceeding; on a mismatch, STOP.

## Status

- **Priority**: P1
- **Effort**: S
- **Risk**: LOW
- **Depends on**: none
- **Category**: bug
- **Planned at**: commit `ae42991`, 2026-07-07

## Repository context (read before anything else)

This is a **Cookiecutter template**. Project source is under the literal
directory `{{cookiecutter.project_slug}}/` — **quote it in shell**
(`cd "{{cookiecutter.project_slug}}"`). This particular file contains **no
Jinja** and is plain `/bin/sh`, but it is only present when `postgres=compose`
(the post-gen hook deletes it otherwise — see `hooks/post_gen_project.py:44-48`).

- Verification means baking a project: `uvx cookiecutter . --no-input -o /tmp/bake`
  produces `/tmp/bake/my-project/`. The script ships only in `postgres=compose`
  bakes (the default), so a default bake contains it.
- The script is not exercised by pytest (it is an operational shell script),
  and **neither the baked nor the root pre-commit stack has a shellcheck (or
  any shell-lint) hook** — do not go looking for one. The gates for this plan
  are: `sh -n` (parse check), a direct `shellcheck` run via
  `uvx --from shellcheck-py shellcheck` (needs network the first time; if
  `uvx` is unavailable, note it in your report and rely on the other gates),
  and the behavioral smoke in Step 4.

## Why this matters

`postgres-backup.sh` is the template's disaster-recovery story — it is what an
operator schedules via host cron to survive data loss. Two defects make it
unsafe in exactly the situation it exists for:

1. **Truncate-before-dump.** The shell opens and truncates the redirect target
   *before* `pg_dump` runs. If `pg_dump` (or the `docker compose exec`) fails,
   a 0-byte or partial `.dump` file is left behind with the newest timestamp.
   Because the prune keeps the newest N by timestamp, this corrupt file is
   retained while a genuine older dump is deleted — silent backup-retention
   corruption discovered only at restore time.
2. **Non-portable prune.** `head -n "-N"` (negative line count) is a GNU
   coreutils extension. On a BSD/macOS host `head` rejects it, the prune errors
   out, and dumps accumulate without bound. The `ls */*.dump` glob also errors
   on an empty backup dir, and without `pipefail` these failures are partly
   masked mid-pipeline.

Fixing both keeps the recovery path trustworthy on any host and guarantees a
failed backup never masquerades as a good one.

## Current state

`{{cookiecutter.project_slug}}/.docker/scripts/postgres-backup.sh` (full file
today):

```sh
#!/bin/sh
set -eu

# Dumps the bundled Compose Postgres with pg_dump custom format and
# prunes old dumps. Run from the project root (compose -f paths are
# relative). Schedule via host cron; copy dumps off-host — a backup on
# the same disk as the database does not survive host loss.

BACKUP_DIR=${1:?usage: postgres-backup.sh <backup-dir> [keep-count]}
KEEP_COUNT=${2:-14}

mkdir -p "$BACKUP_DIR"

STAMP=$(date -u +%Y%m%dT%H%M%SZ)

docker compose -f .docker/compose/prod.yaml --env-file=.env exec -T postgres \
    sh -c 'pg_dump --format=custom --username="$POSTGRES_USER" "$POSTGRES_DB"' \
    > "$BACKUP_DIR/$STAMP.dump"

# Keep the newest KEEP_COUNT dumps; timestamps sort lexicographically.
ls -1 "$BACKUP_DIR"/*.dump | sort | head -n "-$KEEP_COUNT" | while read -r old_dump; do
    rm "$old_dump"
done
```

**Conventions that apply (from `AGENTS.md`)**:
- Short flags before long flags; alphabetized within each group; long flags
  written `--flag=value`. Keep the existing `docker compose` invocation style.
- Prefer clear explicit code over clever compression.
- The file targets POSIX `/bin/sh` (shebang is `#!/bin/sh`, not bash) — do not
  introduce bashisms (no arrays, no `[[ ]]`, no `mapfile`).

## Commands you will need

| Purpose | Command | Expected |
|---------|---------|----------|
| Bake default | `uvx cookiecutter . --no-input -o /tmp/bake` | `/tmp/bake/my-project/` exists, contains `.docker/scripts/postgres-backup.sh` |
| POSIX parse check | `sh -n "{{cookiecutter.project_slug}}/.docker/scripts/postgres-backup.sh"` | exit 0 (the template file has no Jinja, so this works pre-bake) |
| Shellcheck (direct) | `uvx --from shellcheck-py shellcheck "{{cookiecutter.project_slug}}/.docker/scripts/postgres-backup.sh"` | exit 0, no findings (there is NO shellcheck pre-commit hook in this repo) |
| Full baked pre-commit (regression) | `cd /tmp/bake/my-project && git add -A && uv run pre-commit run --all-files` | exit 0 |
| Root pre-commit (regression) | (repo root) `uvx pre-commit run --all-files` | exit 0 |

## Scope

**In scope** (the only file you should modify):
- `{{cookiecutter.project_slug}}/.docker/scripts/postgres-backup.sh`

**Out of scope** (do NOT touch):
- The restore runbook / README backup docs — the CLI contract
  (`postgres-backup.sh <backup-dir> [keep-count]`) does not change, so docs stay
  valid. Only touch README if the drift check shows the docs describe internals
  you changed (they should not).
- `hooks/post_gen_project.py` — the file's deletion rule is unchanged.
- `.docker/compose/prod.yaml` — the Postgres service and its env are unchanged.

## Git workflow

- Work directly on `main`. Do NOT branch, commit, push, or open a PR unless the
  operator explicitly says so. If asked to commit: Conventional Commits, e.g.
  `fix: make postgres-backup.sh fail safe and prune portably`.

## Steps

### Step 1: Dump to a temp file and promote only on success

Replace the dump command so the redirect target is a temp file that is renamed
into place only after `pg_dump` exits 0. (No `pipefail` is needed or wanted:
the dump command is a plain redirect, not a pipeline — `set -e` already aborts
on a non-zero `docker compose exec` — and `pipefail` is not POSIX `sh`.)
Target shape:

```sh
STAMP=$(date -u +%Y%m%dT%H%M%SZ)
TMP_DUMP="$BACKUP_DIR/$STAMP.dump.tmp"

docker compose -f .docker/compose/prod.yaml --env-file=.env exec -T postgres \
    sh -c 'pg_dump --format=custom --username="$POSTGRES_USER" "$POSTGRES_DB"' \
    > "$TMP_DUMP"

mv "$TMP_DUMP" "$BACKUP_DIR/$STAMP.dump"
```

Because `set -e` is in force, a non-zero `pg_dump`/`exec` aborts the script
before the `mv`, leaving only a `.tmp` file (which the prune glob `*.dump` does
NOT match, so it will not masquerade as a valid backup). Do not add cleanup of
stale `.tmp` files in this plan unless you also add a test for it — keep the
change minimal; note the follow-up in Maintenance notes.

Optionally reject an empty dump before promoting (a successful `pg_dump` of a
real DB is never empty):

```sh
if [ ! -s "$TMP_DUMP" ]; then
    echo "pg_dump produced an empty file; refusing to promote" >&2
    rm -f "$TMP_DUMP"
    exit 1
fi
```

**Verify**: `sh -n` on the file parses (exit 0), and shellcheck (Step 3) passes.

### Step 2: Replace the GNU-only prune with a portable all-but-newest-N

`head -n "-$KEEP_COUNT"` is a GNU extension. Replace the prune so it works on
POSIX `head`/`sort`. A portable approach counts the dumps and drops the oldest
`total - KEEP_COUNT` — no temp file needed:

```sh
# Keep the newest KEEP_COUNT dumps; timestamps sort lexicographically.
# Portable "all but newest N": count, then delete the oldest (total - N).
total=$(find "$BACKUP_DIR" -maxdepth 1 -name '*.dump' -type f | wc -l | tr -d ' ')
remove=$((total - KEEP_COUNT))
if [ "$remove" -gt 0 ]; then
    find "$BACKUP_DIR" -maxdepth 1 -name '*.dump' -type f | sort | head -n "$remove" | while read -r old_dump; do
        rm -f "$old_dump"
    done
fi
```

`head -n "$remove"` with a **positive** count is POSIX and works everywhere;
`find` (not the `ls` glob) tolerates an empty directory without error. Note the
prune stays inside `if [ ... ]; then ... fi` — do NOT compress it to
`[ "$remove" -gt 0 ] && ...`, which returns exit 1 (killing the script under
`set -e`) whenever there is nothing to prune. Also guard `KEEP_COUNT`,
**rejecting 0** — a keep-count of 0 would delete every dump including the one
this run just created, which can never be what a backup operator wants (the old
GNU `head -n -0` behavior had exactly that footgun):

```sh
case $KEEP_COUNT in
    ''|0|*[!0-9]*) echo "keep-count must be a positive integer" >&2; exit 2 ;;
esac
```

Place the `KEEP_COUNT` guard right after it is assigned (near the top).

**Verify**: `sh -n` parses; the direct shellcheck run (Step 3) is clean; the
Step 4 smoke proves the boundary behavior.

### Step 3: Lint

Run shellcheck directly on the template file (there is no shellcheck hook in
either pre-commit stack), then the baked pre-commit as a regression check:

```
sh -n "{{cookiecutter.project_slug}}/.docker/scripts/postgres-backup.sh"
uvx --from shellcheck-py shellcheck "{{cookiecutter.project_slug}}/.docker/scripts/postgres-backup.sh"
uvx cookiecutter . --no-input -o /tmp/bake
cd /tmp/bake/my-project
git add -A
uv run pre-commit run --all-files
```

**Verify**: all exit 0. If shellcheck flags a warning on your new code, fix it
precisely — do not add any `# shellcheck disable` (no sibling script under
`.docker/scripts/` has one, so there is no precedent). If `uvx` cannot fetch
shellcheck-py (no network), note that in your report and rely on `sh -n` +
the Step 4 smoke.

### Step 4: Behavioral smoke (no live Postgres needed)

You cannot easily run a real `pg_dump` here, but you can prove the prune and the
promote-on-success logic with a fake `docker` and hand-made files. Do this in a
scratch dir, NOT in the template:

```sh
tmp=$(mktemp -d)
cd "$tmp"
# 20 fake dumps, oldest first by name
for i in $(seq -w 1 20); do : > "20260101T0000${i}Z.dump"; done
# Simulate the prune with KEEP_COUNT=14 (same if-form as the real script):
KEEP_COUNT=14
total=$(find "$tmp" -maxdepth 1 -name '*.dump' -type f | wc -l | tr -d ' ')
remove=$((total - KEEP_COUNT))
if [ "$remove" -gt 0 ]; then
    find "$tmp" -maxdepth 1 -name '*.dump' -type f | sort | head -n "$remove" | while read -r old_dump; do
        rm -f "$old_dump"
    done
fi
ls ./*.dump | wc -l                          # expect 14
test ! -f "20260101T000006Z.dump" && echo OLDEST_GONE   # expect OLDEST_GONE
test -f "20260101T000007Z.dump" && echo BOUNDARY_KEPT   # expect BOUNDARY_KEPT
test -f "20260101T000020Z.dump" && echo NEWEST_KEPT     # expect NEWEST_KEPT
```

**Verify**: `14`, then `OLDEST_GONE`, `BOUNDARY_KEPT`, `NEWEST_KEPT` — i.e.
dumps 01-06 were deleted and 07-20 (the newest 14) survive. These boundary
checks are the machine-checkable version of "the newest 14 remain".

## Test plan

- No pytest test — this is an operational shell script with no Python surface;
  `AGENTS.md` forbids tests that only assert configuration. The gates are
  `sh -n` + direct shellcheck (Step 3) and the prune smoke with boundary
  assertions (Step 4).
- Confirm on a **default** bake (has the script) and confirm a **`postgres=external`**
  bake does NOT contain it (proving you did not change the deletion rule):
  `uvx cookiecutter . --no-input -o /tmp/bake-ext postgres=external` then
  `test ! -f /tmp/bake-ext/my-project/.docker/scripts/postgres-backup.sh`.

## Done criteria

ALL must hold:

- [ ] `grep -c '\.dump\.tmp' "{{cookiecutter.project_slug}}/.docker/scripts/postgres-backup.sh"` ≥ 1 (dump goes to a temp path first).
- [ ] `grep -c 'head -n "-' "{{cookiecutter.project_slug}}/.docker/scripts/postgres-backup.sh"` == 0 (no GNU negative-count `head`).
- [ ] The script still accepts `postgres-backup.sh <backup-dir> [keep-count]` with the same default (`KEEP_COUNT` 14); keep-count `0` is now rejected with exit 2 (documented contract tightening).
- [ ] `sh -n` exits 0 and `uvx --from shellcheck-py shellcheck` reports no findings on the script (or the report notes shellcheck was unavailable).
- [ ] Baked `git add -A && uv run pre-commit run --all-files` exits 0; root `uvx pre-commit run --all-files` exits 0 (regression only — neither stack lints shell).
- [ ] Step 4 smoke leaves exactly 14 of 20 fake dumps AND the three boundary assertions print (`OLDEST_GONE`, `BOUNDARY_KEPT`, `NEWEST_KEPT`).
- [ ] `postgres=external` bake does not contain the script.
- [ ] No files outside the in-scope list modified (`git status`).
- [ ] `plans/README.md` status row updated.

## STOP conditions

Stop and report (do not improvise) if:

- The live script no longer matches the "Current state" excerpt (drift).
- shellcheck demands a change that would alter the CLI contract or require a
  bashism (the shebang is `/bin/sh`).
- Rejecting keep-count `0` turns out to conflict with a documented use of the
  script (check README's backup section first — it should not).
- You find the prune must delete `.tmp` files too — that expands scope; report
  it as a follow-up rather than adding untested cleanup logic.

## Maintenance notes

- **Deferred follow-up**: cleaning up stale `*.dump.tmp` files left by a crash
  mid-dump. Left out to keep this change minimal and testable; a future pass
  could `rm -f "$BACKUP_DIR"/*.dump.tmp` at start (guarded for the empty case).
- **Deferred follow-up**: the template ships six `/bin/sh` scripts and neither
  pre-commit stack lints shell at all — adding a shellcheck hook is tracked as
  plan 006 (see `plans/README.md`).
- A reviewer should confirm: dump promotion is atomic (temp → `mv`), the prune
  count is correct at the boundary (`total == KEEP_COUNT` removes nothing;
  `total == KEEP_COUNT + 1` removes exactly the oldest one), and no bashism crept
  in.
- If the dump format or filename stamp ever changes, the prune glob (`*.dump`)
  and lexicographic-sort assumption must be revisited.
- **Plan 023 lands AFTER this one** and restructures the script into
  `backup`/`verify` subcommands, superseding this plan's "CLI unchanged" done
  criterion at that point — do not treat 023's change as drift.
