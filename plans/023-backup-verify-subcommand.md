# Plan 023: Extend `postgres-backup.sh` with `backup` / `verify` subcommands — prove dumps are restorable, not just present

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving on. If
> anything in "STOP conditions" occurs, stop and report — do not improvise.
> When done, update this plan's status row in `plans/README.md` — unless a
> reviewer dispatched you and told you they maintain the index.
>
> **Drift check (run first)**:
> `git diff --stat ae42991..HEAD -- "{{cookiecutter.project_slug}}/.docker/scripts/postgres-backup.sh" "{{cookiecutter.project_slug}}/README.md" "{{cookiecutter.project_slug}}/.docker/compose/prod.yaml"`
> **Plan 001 rewrites this script's internals and MUST land before this plan**
> (its done criteria assert the old single-command CLI; this plan supersedes
> that CLI). If plan 001 has not landed, STOP and do it first. After it lands,
> re-read the live script — this plan's "Current state" describes the
> POST-001 shape.

## Status

- **Priority**: P3
- **Effort**: S–M
- **Risk**: LOW (verify only ever touches a throwaway container; the backup
  path is restructured, not changed)
- **Depends on**: plan 001 (hard — same file, this plan changes the CLI that
  001's done criteria assert). Coordinates with 002 (restore script + same
  README section) and 022 (`deploy.sh` sibling conventions).
- **Category**: dx / operations
- **Planned at**: commit `ae42991`, 2026-07-07

## Repository context (read before anything else)

This is a **Cookiecutter template**; source under
`{{cookiecutter.project_slug}}/` (**quote it in shell**).
`postgres-backup.sh` contains no Jinja, is POSIX `/bin/sh`, and ships only
when `postgres=compose` (deleted by `hooks/post_gen_project.py` otherwise).
There is **no shellcheck pre-commit hook** until plan 006 lands — lint with
`sh -n` + `uvx --from shellcheck-py shellcheck <file>` directly.
Verification means baking (`uvx cookiecutter . --no-input -o /tmp/bake`) and,
for the verify subcommand, a live Docker daemon.

## Why this matters

The generated README instructs operators to *"Rehearse restores periodically
so the procedure is proven before it is needed under pressure"* — but ships
no tooling for it, and the only database available for a rehearsal is the
live one, which is exactly the wrong place to practice `pg_restore --clean`.
So in practice nobody rehearses, and the first real restore attempt is during
an incident.

A `verify` subcommand closes the gap: it restores a dump into a **throwaway
Postgres container** (same image the stack runs), asserts the restore
actually produced a Django database, and destroys the container. It turns
"backups exist" into "backups are restorable" — the only property that
matters, and the one a silently-corrupt dump (the failure mode plan 001
fixed) would otherwise hide until disaster day. Per the maintainer's
direction, this lives as a second subcommand of the existing script — one
operational entrypoint for the backup lifecycle, not a second script.

**This is a deliberate CLI break**: `postgres-backup.sh <backup-dir>` becomes
`postgres-backup.sh backup <backup-dir>`. Fine for a template (every bake is
a fresh project; there are no external callers to keep compatible) — but the
README cron example must move in the same commit.

## Current state

`{{cookiecutter.project_slug}}/.docker/scripts/postgres-backup.sh` — as left
by plan 001: `#!/bin/sh` + `set -eu`; positional CLI
`<backup-dir> [keep-count]` with `KEEP_COUNT` defaulting to 14 and a guard
rejecting non-positive values; dump via
`docker compose -f .docker/compose/prod.yaml --env-file=.env exec -T postgres
sh -c 'pg_dump --format=custom --username="$POSTGRES_USER" "$POSTGRES_DB"'`
into a `.dump.tmp` promoted to `$STAMP.dump` on success; portable
count-based prune. **Re-read the live file before editing — the excerpt
above is a post-001 summary, and your restructuring must preserve its
semantics exactly.**

`{{cookiecutter.project_slug}}/README.md:286-292` — backup docs + cron
example (`0 3 * * * cd /path/to/… && ./.docker/scripts/postgres-backup.sh
/var/backups/…`), and the "Rehearse restores periodically" instruction at
lines 306-307. (Plan 002 rewrites the *restore* passage nearby — reconcile if
it landed.)

`{{cookiecutter.project_slug}}/.docker/compose/prod.yaml:150` — the postgres
service pins `image: postgres:18.4`. The verify subcommand must run **the
same image**; read it from this file at runtime rather than hardcoding a
second pin (plan 010's drift-checker enumerates pin sites — do not add one).

**Conventions**: POSIX sh only (no bashisms); short-before-long flags,
`--flag=value`; `${1:?usage}` argument style as in the existing script;
comments only for constraints the code can't show.

## Commands you will need

| Purpose | Command | Expected |
|---------|---------|----------|
| Bake default | `uvx cookiecutter . --no-input -o /tmp/bake` | contains the script |
| Parse check | `sh -n "{{cookiecutter.project_slug}}/.docker/scripts/postgres-backup.sh"` | exit 0 |
| Shellcheck | `uvx --from shellcheck-py shellcheck "{{cookiecutter.project_slug}}/.docker/scripts/postgres-backup.sh"` | exit 0 |
| End-to-end verify test | see Step 4 (needs Docker) | `verify` exits 0 on a good dump, ≠0 on a corrupt one |
| Baked + root pre-commit | as in other plans | exit 0 |

## Scope

**In scope**:
- `{{cookiecutter.project_slug}}/.docker/scripts/postgres-backup.sh` —
  restructure into `backup` / `verify` subcommands.
- `{{cookiecutter.project_slug}}/README.md` — update the cron example to the
  new CLI; add a short "rehearse with `verify`" sentence next to the existing
  rehearsal instruction.

**Out of scope**:
- `postgres-restore.sh` (plan 002 — restore targets the LIVE database; verify
  targets a throwaway. Different operations, both needed).
- `hooks/post_gen_project.py` (deletion rule unchanged — same file path).
- Any change to dump format, retention defaults, or the compose postgres
  service.

## Git workflow

- Work directly on `main`. Do NOT branch/commit/push/PR unless told. If asked
  to commit: Conventional Commits, e.g.
  `feat: add verify subcommand to postgres-backup.sh`.

## Steps

### Step 1: Restructure into subcommands

Add a dispatcher at the top; move the existing (post-001) backup logic into
the `backup` arm **unchanged in behavior**. Target shape:

```sh
#!/bin/sh
set -eu

USAGE="usage: postgres-backup.sh backup <backup-dir> [keep-count]
       postgres-backup.sh verify <dump-file>"

COMMAND=${1:?$USAGE}
shift

case $COMMAND in
    backup)
        # ... existing post-001 logic verbatim: arg parsing, KEEP_COUNT
        # guard, mkdir, tmp-file dump + promote, portable prune ...
        ;;
    verify)
        # ... Step 2 ...
        ;;
    *)
        echo "$USAGE" >&2
        exit 2
        ;;
esac
```

(POSIX sh functions are also fine if the arms get long — match whichever
reads clearer; no bashisms.)

**Verify**: `sh -n` exit 0; `./postgres-backup.sh` with no args prints usage
and exits ≠0; `./postgres-backup.sh nonsense` exits 2.

### Step 2: Implement `verify`

Semantics: restore `<dump-file>` into a throwaway Postgres and assert it
produced a Django database. Nothing it does may touch the live stack. Target
shape for the `verify` arm:

```sh
        DUMP_FILE=${1:?$USAGE}
        [ -f "$DUMP_FILE" ] || { echo "no such dump file: $DUMP_FILE" >&2; exit 2; }

        # Same image the stack runs; prod.yaml is the single pin site.
        POSTGRES_IMAGE=$(grep -E '^ *image: postgres:' .docker/compose/prod.yaml | awk '{print $2}')
        [ -n "$POSTGRES_IMAGE" ] || { echo "could not read postgres image from prod.yaml" >&2; exit 2; }

        CONTAINER="backup-verify-$$"
        trap 'docker rm -f "$CONTAINER" >/dev/null 2>&1 || true' EXIT

        docker run -d --name "$CONTAINER" \
            -e POSTGRES_PASSWORD=backup-verify \
            "$POSTGRES_IMAGE" >/dev/null

        tries=0
        until docker exec "$CONTAINER" pg_isready --username=postgres >/dev/null 2>&1; do
            tries=$((tries + 1))
            [ "$tries" -lt 30 ] || { echo "throwaway postgres never became ready" >&2; exit 1; }
            sleep 1
        done

        docker exec -i "$CONTAINER" \
            pg_restore --clean --if-exists --no-owner --username=postgres --dbname=postgres \
            < "$DUMP_FILE"

        MIGRATIONS=$(docker exec "$CONTAINER" \
            psql --username=postgres --dbname=postgres -tAc \
            "SELECT count(*) FROM django_migrations")
        [ "$MIGRATIONS" -gt 0 ] || { echo "restore produced no django_migrations rows" >&2; exit 1; }

        echo "verify OK: $DUMP_FILE restored cleanly ($MIGRATIONS migrations)"
```

Load-bearing details:
- `--no-owner`: the dump's role (the app's slug user) does not exist in the
  throwaway container; without it `pg_restore` errors on ownership. Confirm
  during Step 4 whether `--no-owner` suffices or `--no-privileges` is also
  needed for a clean exit — add exactly what the real dump requires, no more.
- The `trap … EXIT` guarantees cleanup on every failure path (`set -e`
  aborts still run EXIT traps in POSIX sh).
- `django_migrations` is a sound invariant: every generated project migrates
  on boot, so any real dump has rows there.
- No `.env` access needed — the throwaway has its own one-shot password.

**Verify**: `sh -n` + shellcheck exit 0.

### Step 3: Update the README

- Cron example (line ~291): add the `backup` subcommand to the invocation.
- Next to the "Rehearse restores periodically" sentence: state that
  `./.docker/scripts/postgres-backup.sh verify <dump>` performs the rehearsal
  against a throwaway container (never the live database), and suggest
  running it on a schedule (e.g. monthly, or after each backup for paranoid
  setups — note it briefly, don't prescribe).

**Verify**: `grep -c "postgres-backup.sh backup" "{{cookiecutter.project_slug}}/README.md"` ≥ 1;
`grep -c "postgres-backup.sh /var" "{{cookiecutter.project_slug}}/README.md"` == 0
(no stale old-CLI example); root markdownlint passes.

### Step 4: End-to-end test with a real dump (needs Docker)

In a booted default bake (or any environment with the compose stack up):

1. `./.docker/scripts/postgres-backup.sh backup /tmp/dumps` → produces a
   `.dump`; confirm the backup arm's behavior is unchanged from plan 001
   (temp-file promote, prune).
2. `./.docker/scripts/postgres-backup.sh verify /tmp/dumps/<stamp>.dump` →
   exits 0, prints `verify OK`, and `docker ps -a` shows NO leftover
   `backup-verify-*` container.
3. Corrupt-dump case: `head -c 100 /tmp/dumps/<stamp>.dump > /tmp/bad.dump`
   then `verify /tmp/bad.dump` → exits ≠0 AND still leaves no container
   (trap cleanup fired).

If you cannot boot the stack, the corrupt-dump and cleanup halves can still
be exercised with any `pg_dump --format=custom` file; if Docker itself is
unavailable, that is a STOP (verify cannot be verified).

### Step 5: Regression

Default bake: baked pre-commit exit 0; `postgres=external` bake still
contains no script (deletion rule untouched); root pre-commit exit 0.

## Test plan

- No pytest (operational shell). Gates: `sh -n` + shellcheck, the usage/
  dispatch checks (Step 1), the end-to-end good-dump / corrupt-dump /
  no-leftover-container checks (Step 4), and the README greps (Step 3).

## Done criteria

ALL must hold:

- [ ] `postgres-backup.sh` dispatches `backup` / `verify`; unknown or missing subcommand prints usage and exits 2.
- [ ] The `backup` arm's behavior is byte-equivalent to the post-001 logic (temp-file promote, portable prune, KEEP_COUNT guard).
- [ ] `verify` restores into a throwaway container using the image read from `prod.yaml` (no second hardcoded pin), asserts `django_migrations` non-empty, exits 0 on a good dump, ≠0 on a corrupt one, and never leaves a container behind (trap-tested).
- [ ] README cron example uses `backup`; the rehearsal instruction points at `verify`; no stale old-CLI example remains.
- [ ] `sh -n` + shellcheck clean; baked + root pre-commit exit 0; `postgres=external` bake unaffected.
- [ ] No out-of-scope files modified (`git status`); `plans/README.md` status row updated.

## STOP conditions

Stop and report (do not improvise) if:

- Plan 001 has not landed (hard prerequisite — see the drift-check note).
- The live script does not match the post-001 shape this plan assumes.
- A clean `pg_restore` into the throwaway requires flags beyond
  `--no-owner`/`--no-privileges` (something structural about the dumps —
  report what the real dump needed).
- Docker is unavailable — Step 4 cannot run and grep-level verification is
  insufficient for the verify arm.
- shellcheck demands a bashism (shebang stays `/bin/sh`).

## Maintenance notes

- Once plan 006 lands, shellcheck covers this script on every commit.
- The verify arm reads the postgres image from `prod.yaml`, so Dependabot
  image bumps flow through automatically — if plan 010's
  `scripts/check_postgres_image.py` exists, this file needs NO entry in its
  `FILES` list (there is no literal pin here); leave it out.
- If a future dump grows past what a default throwaway container handles
  (memory/disk), the verify arm may need `--shm-size` or a tmpfs tweak —
  revisit only if observed.
- A reviewer should scrutinize: the trap fires on ALL failure paths; the
  backup arm diff is pure restructuring (no behavior change); the README has
  exactly one CLI style.
