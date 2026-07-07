# Plan 002: Fix the broken restore runbook and ship a `postgres-restore.sh` companion script

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving on. If
> anything in "STOP conditions" occurs, stop and report — do not improvise. When
> done, update this plan's status row in `plans/README.md` — unless a reviewer
> dispatched you and told you they maintain the index.
>
> **Drift check (run first)**:
> `git diff --stat ae42991..HEAD -- "{{cookiecutter.project_slug}}/README.md" "{{cookiecutter.project_slug}}/.docker/scripts/postgres-backup.sh" hooks/post_gen_project.py`
> If any changed since this plan was written, compare "Current state" against the
> live files before proceeding; on a mismatch, STOP. (Plan 001 rewrites the
> backup script's internals — that does not conflict with this plan, but re-read
> it if it landed first.)

## Status

- **Priority**: P1
- **Effort**: S
- **Risk**: LOW
- **Depends on**: none (coordinates with plan 001 — same script family; land in either order, re-check excerpts after the first)
- **Category**: bug (docs actively wrong) + the missing inverse script
- **Planned at**: commit `ae42991`, 2026-07-07

## Repository context (read before anything else)

This is a **Cookiecutter template**. Project source is under the literal
directory `{{cookiecutter.project_slug}}/` — **quote it in shell**. The README
is rendered (Jinja allowed); `.docker/scripts/*` is rendered too, but the
existing backup script contains no Jinja. The backup script (and the restore
script this plan adds) ship only when `postgres=compose`:
`hooks/post_gen_project.py` deletes `.docker/scripts/postgres-backup.sh` when
`POSTGRES != "compose"` (lines 44-48), and this plan extends that same rule.

- Verification means baking: `uvx cookiecutter . --no-input -o /tmp/bake`.
- There is **no shellcheck hook** in either pre-commit stack; lint shell with
  `sh -n` + `uvx --from shellcheck-py shellcheck <file>` directly.

## Why this matters

The generated README's disaster-recovery runbook is **actively wrong**. The
documented restore command passes `--dbname="$POSTGRES_DB"
--username="$POSTGRES_USER"` outside any container-side shell, so the
**operator's host shell** expands those variables — and they are defined only
in the container env (via `env_file`), not on the host. Copy-pasting the
documented command runs `pg_restore --dbname= --username=` and fails — during
a database restore, the worst possible moment to discover a broken runbook.
The paired backup script gets this right (it wraps `pg_dump` in
`sh -c '…'` so expansion happens inside the container); the two halves of the
runbook disagree.

The durable fix is the same one the backup path already uses: a script. This
plan (a) fixes the README command and (b) ships a `postgres-restore.sh` that
encapsulates the correct env handling, so recovery is one command instead of a
hand-typed multi-line incantation.

## Current state

`{{cookiecutter.project_slug}}/README.md:297-304` (the restore runbook —
**note the unquoted host-side `$POSTGRES_DB`/`$POSTGRES_USER`**):

```markdown
To restore, stop the `api` service and any worker services first, then
run:

```shell
docker compose -f .docker/compose/prod.yaml --env-file=.env exec -T postgres \
    pg_restore --clean --if-exists --dbname="$POSTGRES_DB" --username="$POSTGRES_USER" \
    < /var/backups/<project>/<stamp>.dump
```
```

`{{cookiecutter.project_slug}}/.docker/scripts/postgres-backup.sh:16-18` (the
correct pattern to mirror — single-quoted `sh -c` so the vars expand in the
container):

```sh
docker compose -f .docker/compose/prod.yaml --env-file=.env exec -T postgres \
    sh -c 'pg_dump --format=custom --username="$POSTGRES_USER" "$POSTGRES_DB"' \
    > "$BACKUP_DIR/$STAMP.dump"
```

(If plan 001 landed first, the dump redirect goes via a `.tmp` file — the
`sh -c` env pattern is unchanged.)

`hooks/post_gen_project.py:44-48` (the deletion rule to extend):

```python
    *(
        [".docker/scripts/postgres-backup.sh"]
        if POSTGRES != "compose"
        else []
    ),
```

**Conventions (from the generated `AGENTS.md`)**: POSIX `/bin/sh` (match the
sibling scripts' `#!/bin/sh` + `set -eu`); short flags before long, long flags
as `--flag=value`; alphabetize where lists exist; prefer clear explicit code.

## Commands you will need

| Purpose | Command | Expected |
|---------|---------|----------|
| Bake default | `uvx cookiecutter . --no-input -o /tmp/bake` | contains both scripts |
| Bake external-pg | `uvx cookiecutter . --no-input -o /tmp/bake-ext postgres=external` | contains NEITHER script |
| Parse check | `sh -n "{{cookiecutter.project_slug}}/.docker/scripts/postgres-restore.sh"` | exit 0 |
| Shellcheck | `uvx --from shellcheck-py shellcheck "{{cookiecutter.project_slug}}/.docker/scripts/postgres-restore.sh"` | exit 0 |
| Baked pre-commit | `cd /tmp/bake/my-project && git add -A && uv run pre-commit run --all-files` | exit 0 |
| Root pre-commit | (repo root) `uvx pre-commit run --all-files` | exit 0 |

## Scope

**In scope**:
- `{{cookiecutter.project_slug}}/.docker/scripts/postgres-restore.sh` (create).
- `{{cookiecutter.project_slug}}/README.md` — replace the hand-typed restore
  command with the script invocation (lines 297-304 region).
- `hooks/post_gen_project.py` — add the restore script to the
  `POSTGRES != "compose"` removal list.

**Out of scope**:
- `postgres-backup.sh` internals (plan 001's territory).
- Any Compose service change; any point-in-time-recovery ambition (the README
  already documents the snapshot-only limitation — keep that text).

## Git workflow

- Work directly on `main`. Do NOT branch/commit/push/PR unless told. If asked
  to commit: Conventional Commits, e.g.
  `fix: correct restore runbook and add postgres-restore.sh`.

## Steps

### Step 1: Create `postgres-restore.sh`

Create `{{cookiecutter.project_slug}}/.docker/scripts/postgres-restore.sh`,
mode 0755 (match the sibling scripts — the baked
`check-shebang-scripts-are-executable` hook enforces the bit). Shape:

```sh
#!/bin/sh
set -eu

# Restores a pg_dump custom-format dump into the bundled Compose Postgres.
# Run from the project root (compose -f paths are relative). Stop the api
# and worker services first; --clean drops and recreates objects, so a
# restore into a live app corrupts in-flight requests.

DUMP_FILE=${1:?usage: postgres-restore.sh <dump-file>}

[ -f "$DUMP_FILE" ] || { echo "no such dump file: $DUMP_FILE" >&2; exit 2; }

docker compose -f .docker/compose/prod.yaml --env-file=.env exec -T postgres \
    sh -c 'pg_restore --clean --if-exists --dbname="$POSTGRES_DB" --username="$POSTGRES_USER"' \
    < "$DUMP_FILE"
```

The `sh -c '…'` single quotes are load-bearing: they defer
`$POSTGRES_DB`/`$POSTGRES_USER` expansion to the container shell, where the
`env_file` vars exist. Mirror the backup script's flag style exactly.

**Verify**: `sh -n` exits 0; shellcheck exits 0;
`ls -l "{{cookiecutter.project_slug}}/.docker/scripts/postgres-restore.sh"`
shows `-rwxr-xr-x`.

### Step 2: Fix the README runbook

Replace the hand-typed `docker compose … pg_restore …` block (lines 300-304)
with the script invocation, keeping the surrounding prose (stop services
first, rehearse restores, snapshot-only caveat):

```shell
./.docker/scripts/postgres-restore.sh /var/backups/<project>/<stamp>.dump
```

Do NOT leave the old command as an alternative — it is the bug.

**Verify**:
`grep -c 'pg_restore' "{{cookiecutter.project_slug}}/README.md"` → 0 (the
README no longer inlines pg_restore; the script owns it), and
`grep -c 'postgres-restore.sh' "{{cookiecutter.project_slug}}/README.md"` ≥ 1.

### Step 3: Extend the deletion rule

In `hooks/post_gen_project.py`, extend the existing `POSTGRES != "compose"`
entry to remove both scripts (keep the list alphabetized):

```python
    *(
        [
            ".docker/scripts/postgres-backup.sh",
            ".docker/scripts/postgres-restore.sh",
        ]
        if POSTGRES != "compose"
        else []
    ),
```

**Verify**:
```
uvx cookiecutter . --no-input -o /tmp/bake-ext postgres=external
test ! -f /tmp/bake-ext/my-project/.docker/scripts/postgres-restore.sh && echo GONE
test ! -f /tmp/bake-ext/my-project/.docker/scripts/postgres-backup.sh && echo GONE2
```
→ `GONE`, `GONE2`, and the bake itself succeeds (no `FileNotFoundError`).

### Step 4: Full regression

```
uvx cookiecutter . --no-input -o /tmp/bake
test -x /tmp/bake/my-project/.docker/scripts/postgres-restore.sh && echo OK
cd /tmp/bake/my-project && git add -A && uv run pre-commit run --all-files
```
→ `OK`; exit 0. Then repo-root `uvx pre-commit run --all-files` → exit 0.

(Optional, only if you have Docker + Compose ≥ 5.3.0 and a booted default
bake: take a backup with `postgres-backup.sh /tmp/dumps`, then restore it with
the new script and confirm exit 0. Not required — the env-expansion fix is
verifiable by inspection against the working backup script.)

## Test plan

- No pytest (operational shell + docs; `AGENTS.md` forbids config-only tests).
  Gates: `sh -n`, direct shellcheck, the `postgres=external` deletion bake, the
  README greps, and both pre-commit runs.

## Done criteria

ALL must hold:

- [ ] `postgres-restore.sh` exists, mode 0755, wraps `pg_restore` in single-quoted `sh -c` (container-side expansion), and passes `sh -n` + shellcheck.
- [ ] The generated README's restore section invokes the script; `grep -c pg_restore README.md` == 0 in the template's README source.
- [ ] `postgres=external` bake contains neither script and bakes cleanly.
- [ ] Default bake contains both scripts; baked + root pre-commit exit 0.
- [ ] No out-of-scope files modified (`git status`); `plans/README.md` status row updated.

## STOP conditions

Stop and report (do not improvise) if:

- The live README restore block or the backup script no longer matches
  "Current state" (drift — plan 001 may have landed; re-read and reconcile).
- shellcheck demands a bashism (shebang must stay `/bin/sh`).
- You find other host-side `$POSTGRES_*` expansions in docs or scripts beyond
  the one fixed here — report them; do not silently expand scope.

## Maintenance notes

- If plan 001's `.tmp`-promotion lands, the restore script is unaffected (it
  reads only `*.dump` files the operator names explicitly).
- A reviewer should confirm the single quotes around the `sh -c` payload
  survived any editor auto-formatting — double quotes reintroduce the bug.
- If the compose file name or `--env-file` convention ever changes, both
  backup and restore scripts must change together.
