# Plan 015: Add media backup/restore parity for local-volume media

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving to the
> next step. If anything in the "STOP conditions" section occurs, stop and
> report — do not improvise. When done, update the status row for this plan
> in `plans/README.md` — unless a reviewer dispatched you and told you they
> maintain the index.
>
> **Drift check (run first)**:
> `git diff --stat 75c4dce..HEAD -- '{{cookiecutter.project_slug}}/.docker/scripts/' '{{cookiecutter.project_slug}}/.docker/compose/prod.yaml' hooks/post_gen_project.py '{{cookiecutter.project_slug}}/README.md'`
> If any in-scope file changed since this plan was written, compare the
> "Current state" excerpts against the live code before proceeding; on a
> mismatch, treat it as a STOP condition.

## Status

- **Priority**: P3
- **Effort**: M
- **Risk**: LOW-MED (new operational scripts; no runtime code changes)
- **Depends on**: plans/013-hooks-testability-and-removal-list-guard.md
  (soft — 013 adds a root test asserting every removal-list entry exists;
  this plan ADDS removal-list entries, so land 013 first and this plan's new
  entries are automatically covered. Also soft on 003/004, which edit the
  generated README's Production area — coordinate to avoid conflicts.)
- **Category**: direction / ops
- **Planned at**: commit `75c4dce`, 2026-07-08

## Why this matters

A production topology of bundled Postgres + local media (`use_s3_media=no`)
gets database backups via `postgres-backup.sh` but has NO backup path for
the `media_data` volume — a silent data-loss asymmetry for exactly the
self-hosted operator the backup scripts target. User uploads survive a
container restart but not host loss. This plan adds a
`media-backup.sh`/`media-restore.sh` pair mirroring the Postgres scripts'
conventions, shipped only when media actually lives on the local volume.

## Current state

This repo is a **cookiecutter template**; single-quote
`{{cookiecutter.project_slug}}` paths in shell commands. Bake to verify.

- Media wiring, `{{cookiecutter.project_slug}}/.docker/compose/prod.yaml`
  (grep-verified at 75c4dce):
  - line 77-79: `{%- if cookiecutter.use_s3_media == "no" %}` →
    `- media_data:/app/media` (api service volumes; a second mount around
    line 136-138 for another service — check whether that is the celery
    worker and keep both in mind for restore-time consistency)
  - line 231-234: the `media_data:` named-volume declaration, gated on
    `use_s3_media == "no"` (shared gate with letsencrypt).
- `{{cookiecutter.project_slug}}/src/config/settings/components/storage.py:3-4`
  — `MEDIA_ROOT = BASE_DIR / "media"`, mounted at `/app/media` in the
  container.
- The exemplar scripts to mirror —
  `{{cookiecutter.project_slug}}/.docker/scripts/postgres-backup.sh` (dump →
  temp file → non-empty check → promote → prune to keep-count; `verify`
  subcommand restores into a throwaway container) and `postgres-restore.sh`
  (stop-services warning in header comment; restore via
  `docker compose ... exec -T`). Both are `#!/bin/sh`, `set -eu`, POSIXLY
  portable, usage-string driven, run from the project root. Read both fully
  before writing — your scripts must be stylistic siblings.
- Knob-gated removal, `hooks/post_gen_project.py:60-67`:

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

There is no `USE_S3_MEDIA` constant in the hook today — you will add one
(the Jinja constants block at `:7-29` shows the pattern:
`USE_S3_MEDIA = {{ cookiecutter.use_s3_media | tojson }}`, inserted
alphabetically).

- The generated README has a Production section documenting the Postgres
  backup runbook — grep `postgres-backup` in
  `{{cookiecutter.project_slug}}/README.md` to find it; the media runbook
  paragraph goes alongside it, inside a
  `{% if cookiecutter.use_s3_media == "no" %}` gate.

## Commands you will need

| Purpose | Command | Expected on success |
|---------|---------|---------------------|
| Bake local-media | `uvx cookiecutter . -o /tmp/verify-015 --no-input use_s3_media=no` | scripts present |
| Bake s3-media (default) | `uvx cookiecutter . -o /tmp/verify-015b --no-input` | scripts ABSENT |
| Shellcheck | `uvx pre-commit run shellcheck --all-files` (root; also runs in the bake's pre-commit) | exit 0 |
| Bake lint | in bake: `git init -q && git add -A && uv run pre-commit run --all-files` | exit 0 |
| Root tests (013's guard) | `python -m unittest discover -s tests -t .` | `OK` |

## Scope

**In scope**:

- `{{cookiecutter.project_slug}}/.docker/scripts/media-backup.sh` (create)
- `{{cookiecutter.project_slug}}/.docker/scripts/media-restore.sh` (create)
- `hooks/post_gen_project.py` (add `USE_S3_MEDIA` constant + one removal
  splat)
- `{{cookiecutter.project_slug}}/README.md` (one gated runbook paragraph)

**Out of scope** (do NOT touch):

- S3-media backup (provider-managed; out of the template's contract).
- `prod.yaml` — no compose changes are needed; the scripts read the volume
  through a throwaway container.
- Scheduling/cron wiring — the Postgres scripts leave scheduling to the
  operator; match that.

## Git workflow

- Conventional commit, e.g. `feat: add media backup and restore scripts for
  local-volume media`.
- Do NOT push unless instructed.

## Steps

### Step 1: Write `media-backup.sh`

Mirror `postgres-backup.sh`'s structure exactly (usage string, `backup
<backup-dir> [keep-count]` and `verify <archive>` subcommands, `set -eu`,
temp-then-promote, non-empty check, keep-count prune). Core backup
mechanism — tar the volume through a throwaway container so the script
works regardless of which services are running:

```sh
docker run --rm \
    -v "$(docker compose -f .docker/compose/prod.yaml --env-file=.env config --format json | python3 -c 'import json,sys; print(json.load(sys.stdin)["volumes"]["media_data"]["name"])')":/media:ro \
    -v "$BACKUP_DIR":/backup \
    alpine tar -czf "/backup/$STAMP.tar.gz.tmp" -C /media .
```

SIMPLER ALTERNATIVE (prefer if it verifies): `docker compose ... exec -T api
tar -czf - -C /app/media . > "$TMP_ARCHIVE"` — matches how
`postgres-backup.sh` streams `pg_dump` through `exec -T`, requires the api
service to be running (acceptable: so does the Postgres script), and avoids
volume-name resolution entirely. Choose ONE mechanism, implement it fully,
and note the choice in the script's header comment. `verify` should list
the archive (`tar -tzf`) and assert it is non-empty.

**Verify**: `shellcheck` clean on the new file
(`uvx shellcheck '{{cookiecutter.project_slug}}/.docker/scripts/media-backup.sh'`
works pre-bake since the script must contain NO Jinja).

### Step 2: Write `media-restore.sh`

Mirror `postgres-restore.sh`: single archive argument, header comment
telling the operator to stop api/worker services first, restore via the
same mechanism family as step 1 (e.g. `exec -T api sh -c 'rm -rf
/app/media/* && tar -xzf - -C /app/media' < "$ARCHIVE"` — BUT: if you use
`rm -rf` inside the container, guard the path literally and double-check
the tar extraction target; a typo here destroys user data. Prefer extracting
over the top without the rm, and document that deleted-since-backup files
survive a restore — matching `pg_restore --clean` semantics is NOT required
for a first version, but say what the semantics are in the header).

**Verify**: shellcheck clean.

### Step 3: Gate the scripts at bake time

In `hooks/post_gen_project.py`: add
`USE_S3_MEDIA = {{ cookiecutter.use_s3_media | tojson }}` to the constants
block (alphabetical position), and add to `REMOVED_PATHS` (matching the
existing splat style, placed near the other `.docker/scripts` splat):

```python
    *(
        [
            ".docker/scripts/media-backup.sh",
            ".docker/scripts/media-restore.sh",
        ]
        if USE_S3_MEDIA == "yes"
        else []
    ),
```

**Verify**: both bakes —
`/tmp/verify-015` (`use_s3_media=no`): `ls '/tmp/verify-015/my-project/.docker/scripts/'`
shows both media scripts; `/tmp/verify-015b` (default, s3=yes): shows
neither. If plan 013 landed, `python -m unittest discover -s tests -t .` →
`OK` (the existence guard sees the new entries).

### Step 4: Document the runbook

In `{{cookiecutter.project_slug}}/README.md`, next to the Postgres backup
runbook, add a `{% if cookiecutter.use_s3_media == "no" %}`-gated paragraph:
what the scripts do, the backup command, the restore command, the
stop-services-first warning, and the same off-host-copies caveat the
Postgres runbook carries. Match the surrounding section's voice and heading
level.

**Verify**: in the `/tmp/verify-015` bake:
`git init -q && git add -A && uv run pre-commit run --all-files` → exit 0
(markdownlint + shellcheck across the baked files).

### Step 5: Functional smoke of backup + restore

In `/tmp/verify-015/my-project` with Docker available: boot the dev stack
or a minimal prod stack, drop a file into the media volume
(`docker compose ... exec api sh -c 'echo test > /app/media/smoke.txt'`),
run `./.docker/scripts/media-backup.sh backup /tmp/verify-015-backups`,
assert a non-empty archive exists, delete the file, run
`./.docker/scripts/media-restore.sh /tmp/verify-015-backups/<archive>`,
assert the file is back. Tear down with `down -v`.

**Verify**: the round-trip succeeds. If Docker is unavailable, STOP and
report — these are operational scripts; shipping them without one real
round-trip is not acceptable.

## Test plan

Step 5 is the test (manual round-trip; these are operator shell scripts —
the repo has no shell-test harness and none of the existing `.docker/scripts`
have unit tests; parity means matching that bar plus the mandatory smoke).
Static gates: shellcheck, both bake variants, 013's existence guard.

## Done criteria

- [ ] Both scripts exist, shellcheck-clean, no Jinja inside
- [ ] `use_s3_media=no` bake ships them; default bake does not
- [ ] README runbook paragraph present only in the `use_s3_media=no` bake
- [ ] Backup→delete→restore round-trip demonstrated (step 5)
- [ ] Baked pre-commit passes; root tests pass
- [ ] `plans/README.md` status row updated

## STOP conditions

Stop and report back if:

- `media_data` is no longer a named volume gated on `use_s3_media == "no"`
  in prod.yaml (the mechanism assumption breaks).
- The restore mechanism requires `rm -rf` with any variable-derived path —
  redesign so the destructive path is a literal, or stop and ask.
- Docker is unavailable for step 5.
- You find an existing media-backup mechanism anywhere in the template
  (search first: `grep -rn "media" '{{cookiecutter.project_slug}}/.docker/'`)
  — the audit found none at 75c4dce, but if one appeared, reconcile instead
  of duplicating.

## Maintenance notes

- If a future knob moves media to another storage class, the removal splat
  and README gate must follow `use_s3_media`'s semantics.
- Reviewer scrutiny: the restore script's deletion semantics (see step 2)
  and that neither script embeds the volume name statically (slug-dependent).
- Deferred: scheduling/retention documentation beyond keep-count, and any
  S3-side backup guidance.
