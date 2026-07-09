# Plan 003: Backup scripts — guard destructive restores behind a running-services check and stop orphaning `.tmp` files

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving to the
> next step. If anything in the "STOP conditions" section occurs, stop and
> report — do not improvise. When done, update the status row for this plan
> in `plans/README.md` — unless a reviewer dispatched you and told you they
> maintain the index.
>
> **Drift check (run first)**:
> `git diff --stat e0ec725..HEAD -- '{{cookiecutter.project_slug}}/.docker/scripts/postgres-backup.sh' '{{cookiecutter.project_slug}}/.docker/scripts/media-backup.sh' '{{cookiecutter.project_slug}}/README.md'`
> If any in-scope file changed since this plan was written, compare the
> "Current state" excerpts against the live code before proceeding; on a
> mismatch, treat it as a STOP condition.

## Status

- **Priority**: P2
- **Effort**: S
- **Risk**: LOW
- **Depends on**: none
- **Category**: bug
- **Planned at**: commit `e0ec725`, 2026-07-09

## Why this matters

This repository is a cookiecutter template; the two scripts below ship into
generated projects as the operator's backup/restore tooling for the bundled
Compose stack. Two defects:

1. **Unguarded destructive restore.** `postgres-backup.sh restore` runs
   `pg_restore --clean --if-exists` against the live production database, and
   `media-backup.sh restore` extracts a tar over the live media volume, with
   only a file-existence check. The header comments say "stop the api service
   ... before restore", but nothing enforces it — a mistyped subcommand or a
   restore run while the app serves traffic irreversibly drops and recreates
   every DB object (or overwrites media) mid-flight.
2. **Orphaned temp files.** The `backup` subcommands write to
   `$STAMP.dump.tmp` / `$STAMP.tar.gz.tmp` and promote via `mv` on success.
   Both scripts use `set -eu`, so a mid-dump failure exits before the `mv`
   and before any cleanup; retention prunes only `*.dump` / `*.tar.gz`. Each
   transient cron failure leaks a `.tmp` that accumulates forever on the disk
   the backup is meant to protect.

## Current state

- `{{cookiecutter.project_slug}}/.docker/scripts/postgres-backup.sh` — POSIX
  `sh`, `set -eu`, `case $COMMAND in backup|restore|verify)`. This file is
  Jinja-rendered (only `.github/workflows/*` and `.agents/*` are
  copy-without-render) but currently contains no Jinja; it is removed by the
  post-gen hook when `postgres != "compose"`. Key excerpts:

  ```sh
  # backup branch, ~lines 36-46
  TMP_DUMP="$BACKUP_DIR/$STAMP.dump.tmp"

  docker compose -f .docker/compose/prod.yaml --env-file=.env exec -T postgres \
      sh -c 'pg_dump --format=custom --username="$POSTGRES_USER" "$POSTGRES_DB"' \
      > "$TMP_DUMP"

  if [ ! -s "$TMP_DUMP" ]; then
      echo "pg_dump produced an empty file; refusing to promote" >&2
      rm -f "$TMP_DUMP"
      exit 1
  fi

  mv "$TMP_DUMP" "$BACKUP_DIR/$STAMP.dump"
  ```

  ```sh
  # restore branch, ~lines 61-70
  restore)
      DUMP_FILE=${1:?$USAGE}
      if [ ! -f "$DUMP_FILE" ]; then
          echo "no such dump file: $DUMP_FILE" >&2
          exit 2
      fi

      docker compose -f .docker/compose/prod.yaml --env-file=.env exec -T postgres \
          sh -c 'pg_restore --clean --dbname="$POSTGRES_DB" --if-exists --username="$POSTGRES_USER"' \
          < "$DUMP_FILE"
      ;;
  ```

  The `verify` branch already uses `trap 'docker rm -f "$CONTAINER" ...' EXIT`
  — use it as the in-file exemplar for trap style.

- `{{cookiecutter.project_slug}}/.docker/scripts/media-backup.sh` — same
  structure; removed when `use_s3_media == "yes"`. Backup branch writes
  `TMP_ARCHIVE="$BACKUP_DIR/$STAMP.tar.gz.tmp"` via a throwaway
  `docker run ... tar -czf - ... > "$TMP_ARCHIVE"` (~lines 38-57); restore
  branch (~lines 90-98) validates the archive (readable, no absolute/`..`
  paths) then extracts into the live volume via
  `docker run --rm -i -v "$MEDIA_VOLUME":/media ... tar -xzf - -C /media`.

- Generated README restore runbooks —
  `{{cookiecutter.project_slug}}/README.md` Production section. Postgres
  block (~lines 426-431):

  ```
  To restore, stop the `api` service and any worker services first, then
  run:

      ./.docker/scripts/postgres-backup.sh restore /var/backups/<project>/<stamp>.dump
  ```

  A parallel media-restore block exists later in the same section (search for
  `media-backup.sh restore`).

- Compose facts you need: the prod stack is
  `.docker/compose/prod.yaml`; app services are `api` plus (knob-dependent)
  `celery-worker`/`celery-beat`; backing services are `postgres`, `redis`,
  `traefik` (all knob-dependent except `api`).
  `docker compose -f .docker/compose/prod.yaml --env-file=.env ps --services --status=running`
  lists running service names one per line without needing to know which
  services exist — this is the Jinja-free way to detect "app still running".

- Conventions (root `AGENTS.md`): POSIX sh (`#!/bin/sh`, `set -eu`); short
  flags before long flags, alphabetized within groups; long flags with values
  as `--flag=value`; blank lines around control-flow blocks; alphabetize list
  items when order doesn't matter.

## Commands you will need

| Purpose | Command | Expected on success |
|---------|---------|---------------------|
| Syntax check | `sh -n '{{cookiecutter.project_slug}}/.docker/scripts/postgres-backup.sh'` (fails on Jinja if you add any — bake first in that case) | exit 0 |
| Bake (scripts present) | `uvx cookiecutter . -o /tmp/verify-003 --no-input` | exit 0; both scripts under `/tmp/verify-003/my-project/.docker/scripts/` |
| Baked lint | `cd /tmp/verify-003/my-project && uv sync --locked && uv run pre-commit run --all-files` | exit 0 (includes shell checks) |
| Root checks | `uvx pre-commit run --all-files` | exit 0 |

Always quote paths containing `{{cookiecutter.project_slug}}`.

## Scope

**In scope** (the only files you should modify):

- `{{cookiecutter.project_slug}}/.docker/scripts/postgres-backup.sh`
- `{{cookiecutter.project_slug}}/.docker/scripts/media-backup.sh`
- `{{cookiecutter.project_slug}}/README.md` (the two restore runbook blocks
  only)

**Out of scope** (do NOT touch, even though they look related):

- The `verify` branches of both scripts — already safe (throwaway container).
- `.docker/scripts/deploy.sh`, compose files, `hooks/post_gen_project.py`
  (removal lists already handle both scripts correctly).
- Interactive TTY confirmation prompts — the maintainer's scripts are
  cron/agent-driven; use the flag-based guard below, not `read`.

## Git workflow

- Branch: `advisor/003-backup-script-hardening`
- Commit style: conventional commits (e.g.
  `fix: guard backup restores and clean up orphaned temp files`).
- Do NOT push or open a PR unless the operator instructed it.

## Steps

### Step 1: Clean up temp files on failed backups (both scripts)

In `postgres-backup.sh`'s `backup` branch, immediately after
`TMP_DUMP="$BACKUP_DIR/$STAMP.dump.tmp"` add:

```sh
        trap 'rm -f "$TMP_DUMP"' EXIT
```

and immediately after the successful `mv "$TMP_DUMP" "$BACKUP_DIR/$STAMP.dump"`
add:

```sh
        trap - EXIT
```

(Then the existing explicit `rm -f "$TMP_DUMP"` in the empty-file branch
becomes redundant but harmless — leave it, it documents intent.) Mirror the
same two lines in `media-backup.sh` with `$TMP_ARCHIVE`. Note each script has
at most one `trap ... EXIT` active at a time per invocation: the `backup` and
`verify` branches are mutually exclusive arms of the same `case`, so this
does not clobber `postgres-backup.sh`'s verify trap.

**Verify**: `sh -n` on both template files → exit 0. Then simulate a failure:
in a scratch dir, run
`sh -c 'set -eu; TMP=/tmp/claude-scratch-003.tmp; trap "rm -f \"$TMP\"" EXIT; touch "$TMP"; false'`
→ exits 1 and `/tmp/claude-scratch-003.tmp` does not exist afterwards
(confirms the trap pattern you used behaves as intended in `sh`).

### Step 2: Refuse restores while app services are running (both scripts)

In both scripts' `restore` branches, after the existing dump/archive
validation and **before** the destructive `docker` command, insert a guard.
Support a `--force` bypass as an optional trailing argument
(`restore <file> [--force]`). Target shape for `postgres-backup.sh` (adapt
variable names for `media-backup.sh`):

```sh
    restore)
        DUMP_FILE=${1:?$USAGE}
        FORCE=${2:-}

        if [ -n "$FORCE" ] && [ "$FORCE" != "--force" ]; then
            echo "$USAGE" >&2
            exit 2
        fi

        if [ ! -f "$DUMP_FILE" ]; then
            echo "no such dump file: $DUMP_FILE" >&2
            exit 2
        fi

        if [ "$FORCE" != "--force" ]; then
            RUNNING_APP_SERVICES=$(
                docker compose -f .docker/compose/prod.yaml --env-file=.env ps --services --status=running \
                    | grep -v -x -e postgres -e redis -e traefik || true
            )

            if [ -n "$RUNNING_APP_SERVICES" ]; then
                echo "refusing to restore while app services are running:" >&2
                echo "$RUNNING_APP_SERVICES" >&2
                echo "stop them first (docker compose ... stop api ...) or pass --force" >&2
                exit 2
            fi
        fi
        ...existing docker restore command...
```

Notes:
- `grep -v -x` excludes exact service names; `postgres`/`redis` must be
  allowed to run (postgres restore needs postgres up), and `traefik` is
  harmless. Everything else (api, celery-worker, celery-beat, and any future
  app service) blocks the restore. The `|| true` keeps `set -e` happy when
  grep filters everything out.
- For `media-backup.sh` use the identical exclusion list — media restore has
  the same "no app writers" requirement.
- Update the `USAGE` string in both scripts:
  `restore <dump-file> [--force]` / `restore <archive> [--force]`.

**Verify**: `sh -n` on both template files → exit 0. Then bake
(`uvx cookiecutter . -o /tmp/verify-003 --no-input`) and confirm the baked
copies contain the guard:
`grep -c 'refusing to restore' /tmp/verify-003/my-project/.docker/scripts/postgres-backup.sh /tmp/verify-003/my-project/.docker/scripts/media-backup.sh`
→ `1` for each file.

### Step 3: Update the two README restore runbooks

In `{{cookiecutter.project_slug}}/README.md`, amend both restore blocks
(postgres ~line 426, media — search `media-backup.sh restore`) to state that
the script refuses to run while `api`/worker services are running and that
`--force` bypasses the guard for non-Compose or emergency contexts. Keep the
existing "stop the api service and any worker services first" sentence — the
guard enforces it now. Anchor your edit on the surrounding sentences, not
line numbers.

**Verify**: `grep -n -- '--force' '{{cookiecutter.project_slug}}/README.md'`
→ at least 2 matches (one per runbook).

### Step 4: Full verification sweep

Bake fresh, run the baked project's `uv run pre-commit run --all-files`
(shell hooks included), and the root `uvx pre-commit run --all-files`.

**Verify**: both exit 0.

## Test plan

There is no shell-unit-test harness in this repo (root `tests/` covers Python
guard scripts and hooks only) — do not invent one. Coverage comes from:

- `sh -n` syntax gates per step.
- The baked project's pre-commit shell hooks (step 4).
- The behavioral trap simulation in step 1's verify.
- Optional (only if Docker is available and you have time): in the baked
  project, `cp .env.example .env`, boot
  `docker compose -f .docker/compose/prod.yaml -f .docker/compose/ci-services.yaml --env-file=.env up -d --build --wait`
  is the CI smoke path — too heavy for this plan; skip unless a reviewer
  requests a live demonstration of the guard.

## Done criteria

Machine-checkable. ALL must hold:

- [ ] `grep -c "trap 'rm -f" '{{cookiecutter.project_slug}}/.docker/scripts/postgres-backup.sh'` → 1 (plus the pre-existing verify-branch trap: total `grep -c "trap "` is 3 including `trap - EXIT`)
- [ ] `grep -c "trap " '{{cookiecutter.project_slug}}/.docker/scripts/media-backup.sh'` → 2 (`trap 'rm -f ...'` + `trap - EXIT`)
- [ ] `grep -c 'refusing to restore' '{{cookiecutter.project_slug}}/.docker/scripts/postgres-backup.sh'` → 1; same for `media-backup.sh`
- [ ] Both scripts pass `sh -n`
- [ ] `grep -n -- '--force' '{{cookiecutter.project_slug}}/README.md'` → ≥ 2 matches
- [ ] Fresh default bake + `uv run pre-commit run --all-files` in it → exit 0
- [ ] Root `uvx pre-commit run --all-files` → exit 0
- [ ] `git status` shows no modified files outside the in-scope list
- [ ] `plans/README.md` status row updated

## STOP conditions

Stop and report back (do not improvise) if:

- Either script's `restore` branch no longer matches the "Current state"
  excerpts.
- `docker compose ps --services --status=running` is unavailable in the
  Compose version the template targets (the README pins Compose ≥ v5.x with
  `pre_start` support; `--services --status` has existed far longer — but if
  a baked `docker compose ps --services --status=running` errors, report it).
- You find yourself adding Jinja conditionals to enumerate service names —
  that's the wrong direction; the exclusion-list approach exists precisely to
  avoid it.

## Maintenance notes

- If a new app service is added to `prod.yaml`, the exclusion list
  (`postgres`, `redis`, `traefik`) still blocks it by default — the safe
  failure mode. Only additions of new *backing* services need a new exclusion
  entry in both scripts.
- Reviewer should scrutinize: trap placement relative to `set -eu` exit
  paths, and that `--force` is position-checked (second arg) rather than
  parsed loosely.
- Deferred: interactive confirmation prompts (rejected — cron/agent-driven
  scripts) and off-host backup shipping (documented as operator
  responsibility in the README).
