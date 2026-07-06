# Plan 006: Ship a backup-and-restore story for bundled Postgres

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving to the
> next step. If anything in the "STOP conditions" section occurs, stop and
> report — do not improvise. When done, update the status row for this plan
> in `plans/README.md` — unless a reviewer dispatched you and told you they
> maintain the index.
>
> **Drift check (run first)**:
> `git diff --stat d333a73..HEAD -- '{{cookiecutter.project_slug}}/.docker' '{{cookiecutter.project_slug}}/README.md' hooks/post_gen_project.py`
> If any in-scope file changed since this plan was written, compare the
> "Current state" excerpts against the live code before proceeding; on a
> mismatch, treat it as a STOP condition. (Plans 004/007 legitimately edit
> `prod.yaml`/README — integrate, don't overwrite.)

## Status

- **Priority**: P2
- **Effort**: M
- **Risk**: LOW — additive script + docs; no app-path changes
- **Depends on**: none (serialize with 004/007 on `prod.yaml`/README)
- **Category**: security (data durability)
- **Planned at**: commit `d333a73`, 2026-07-05

## Why this matters

When `postgres == "compose"` (the default), production data lives in a
single named Docker volume with no backup mechanism, no docs, and no
restore procedure — an accidental `down -v`, volume corruption, or host
loss is unrecoverable. The README documents backups only for the
`external` knob ("Your provider owns backups, high availability, and
upgrades"); the bundled case says nothing. This is the template's
largest silent production gap. Ship an operator-runnable backup script
plus a documented restore path, gated to the compose topology.

Design decision (matches the maintainer's taste: no new always-on
services, keep operational constants fixed): a host-cron-driven
`pg_dump` script inside the project, NOT a backup sidecar container.

## Current state

Cookiecutter template; generated project under the literal
`{{cookiecutter.project_slug}}/` directory. Knob: `postgres` ∈
`compose` | `external`.

- `{{cookiecutter.project_slug}}/.docker/compose/prod.yaml:124-141` —
  the gated Postgres service:

  ```yaml
  {%- if cookiecutter.postgres == "compose" %}
    postgres:
      env_file:
        - ../../.env
      healthcheck:
        test:
          - CMD-SHELL
          - pg_isready --dbname="$${POSTGRES_DB}" --username="$${POSTGRES_USER}"
        ...
      image: postgres:18.4
      restart: unless-stopped
      volumes:
        - postgres_data:/var/lib/postgresql
  {%- endif %}
  ```

- `{{cookiecutter.project_slug}}/.docker/scripts/` — existing scripts
  (`gunicorn.sh`, `migrations.sh`, `dev.sh`, `celery-*.sh`): all
  `#!/bin/sh` + `set -eu`, executable.

- `hooks/post_gen_project.py:25-53` — `REMOVED_PATHS` deletes
  knob-irrelevant files after generation. Knob constants are defined at
  the top via `{{ cookiecutter.x | tojson }}`; there is currently no
  `POSTGRES` constant. New knob-gated files must be added here.

- `{{cookiecutter.project_slug}}/README.md`:
  - Production section: the `postgres == "compose"` branch (lines
    260-264) mentions only `POSTGRES_PASSWORD`; the `external` branch
    (265-274) carries the "provider owns backups" sentence.
  - The compose commands convention: run from the project root with
    `-f .docker/compose/prod.yaml --env-file=.env`.

- Conventions: AGENTS.md (root) — "Format complex shell commands over
  multiple lines with backslashes"; alphabetize where order is
  arbitrary; README inventory style.

## Commands you will need

| Purpose | Command | Expected on success |
|---------|---------|---------------------|
| Bake (default) | `uvx cookiecutter . --no-input -o /tmp/plan006` | baked; script present |
| Bake (external) | `uvx cookiecutter . --no-input -o /tmp/plan006ext postgres=external` | baked; script ABSENT |
| Boot prod stack | env prep per `.github/workflows/ci.yaml:165-170`, then `docker compose -f .docker/compose/prod.yaml --env-file=.env up -d --build --wait` | healthy |
| Run backup | `./.docker/scripts/postgres-backup.sh /tmp/plan006-backups` | dump file created |
| Verify dump | `docker compose -f .docker/compose/prod.yaml --env-file=.env exec -T postgres pg_restore --list < <dump>` | TOC listing |
| Root pre-commit | `pre-commit run --all-files` | exit 0 |

## Scope

**In scope**:

- `{{cookiecutter.project_slug}}/.docker/scripts/postgres-backup.sh`
  (create)
- `hooks/post_gen_project.py` (add `POSTGRES` constant + one
  `REMOVED_PATHS` entry)
- `{{cookiecutter.project_slug}}/README.md` (Production section: new
  "Backups" prose in the compose branch)
- Root `README.md` (one "What You Get" bullet)

**Out of scope** (do NOT touch):

- `prod.yaml` — no new services, volumes, or labels.
- WAL archiving / PITR / off-host replication — documented as the
  operator's next step, not implemented.
- The `external` knob's docs (already correct).

## Git workflow

- Work directly on `main`; do not create or switch to a plan branch unless the
  operator explicitly asks.
- Do NOT commit, push, or open a PR unless the operator explicitly instructs it.
- If asked to commit, use a conventional commit such as
  `feat: add pg_dump backup script and restore docs`.

## Steps

### Step 1: Create the backup script

`{{cookiecutter.project_slug}}/.docker/scripts/postgres-backup.sh`,
executable, matching the house shell style:

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

Notes for the executor: `head -n -N` is GNU coreutils (fine: the deploy
target is Linux). `exec -T` disables TTY so stdout is the dump stream.
Credentials come from the container's own env (`env_file: .env`), so the
script needs no secret handling.

**Verify**: `shellcheck '{{cookiecutter.project_slug}}/.docker/scripts/postgres-backup.sh'`
if shellcheck is available (else skip); file mode is executable in git
(`git ls-files -s` shows `100755`).

### Step 2: Gate the file to the compose knob

In `hooks/post_gen_project.py`, add at the top with the other knob
constants (alphabetical):

```python
POSTGRES = {{ cookiecutter.postgres | tojson }}
```

and in `REMOVED_PATHS` (keep the list's existing grouping style):

```python
*(
    [".docker/scripts/postgres-backup.sh"]
    if POSTGRES != "compose"
    else []
),
```

**Verify**: bake `postgres=external` → the script is absent; default
bake → present and executable.

### Step 3: Document backup + restore in the baked README

In the Production section's `postgres == "compose"` branch (after the
SECRET_KEY/POSTGRES_PASSWORD paragraph), add prose covering:

- Schedule: a host-cron example, e.g.
  `0 3 * * * cd /path/to/{{ cookiecutter.project_slug }} && ./.docker/scripts/postgres-backup.sh /var/backups/{{ cookiecutter.project_slug }}`
- Off-host responsibility: dumps must be copied off the host (rclone,
  object storage, whatever the operator uses); a dump on the same disk
  does not survive host loss.
- Restore procedure (fenced block):

  ```shell
  docker compose -f .docker/compose/prod.yaml --env-file=.env exec -T postgres \
      pg_restore --clean --if-exists --dbname="$POSTGRES_DB" --username="$POSTGRES_USER" \
      < /var/backups/<project>/<stamp>.dump
  ```

  with a warning to stop `api`/workers first and to rehearse restores
  periodically.
- Scope honesty: this is snapshot-based; anything written after the last
  dump is lost. Point-in-time recovery (WAL archiving) is out of scope —
  move to managed Postgres (`postgres=external`) when RPO minutes
  matter.

Keep the section OUT of the `external` branch.

**Verify**: bake default + external; the prose renders only in the
default; markdownlint via the baked pre-commit passes.

### Step 4: Root README bullet

Add to "What You Get" (alphabetical position): a bullet like
"`pg_dump` backup script and restore runbook for the bundled Postgres".

**Verify**: root `pre-commit run --all-files` → exit 0.

### Step 5: Live verification

Boot the baked default prod stack, create a marker row (e.g.
`docker compose ... exec api python manage.py createsuperuser --noinput`
with `DJANGO_SUPERUSER_USERNAME=plan006 DJANGO_SUPERUSER_PASSWORD=...
DJANGO_SUPERUSER_EMAIL=plan006@example.com` env vars), then:

```shell
./.docker/scripts/postgres-backup.sh /tmp/plan006-backups
ls -l /tmp/plan006-backups   # one .dump, non-empty
docker compose -f .docker/compose/prod.yaml --env-file=.env exec -T postgres \
    pg_restore --list < /tmp/plan006-backups/*.dump | grep -i "core_user"
```

Then rehearse the documented restore command and confirm the marker user
still exists (`manage.py shell -c "from apps.core.models import User;
print(User.objects.filter(username='plan006').exists())"` → `True`).
Finally run the script twice more with `KEEP_COUNT=1`
(`postgres-backup.sh /tmp/plan006-backups 1`) and confirm pruning leaves
exactly one dump. Tear down with `down -v`.

**Verify**: all expected outputs above.

## Test plan

No pytest changes (host-operational script). The live verification in
Step 5 — dump created, TOC lists `core_user`, restore rehearsal passes,
prune keeps N — is the test, and its outputs go in the completion
report.

## Done criteria

- [ ] Default bake ships an executable `postgres-backup.sh`; external
      bake does not
- [ ] Step 5 evidence: dump non-empty, `pg_restore --list` shows
      `core_user`, restore rehearsal preserves the marker user, pruning
      honors keep-count
- [ ] README backup/restore prose renders in compose bakes only
- [ ] Root + baked pre-commit exit 0; `git status` clean outside scope
- [ ] `plans/README.md` status row updated

## STOP conditions

- Docker unavailable — the live verification is mandatory for a plan
  whose whole value is a working restore path.
- `pg_restore --clean` errors on the rehearsal in a way that suggests
  the dump format/flags are wrong for `postgres:18.4` — report the exact
  error; do not swap dump formats ad hoc.
- You are tempted to add a sidecar/cron container — that is an explicit
  design rejection here; report instead if the script approach proves
  insufficient.

## Maintenance notes

- The script's compose file path and `--env-file` convention are
  duplicated from the README deploy commands; if the compose layout
  moves, update both.
- If the maintainer later wants scheduled off-host backups as a feature,
  that's a new knob (backup sidecar + object-storage target) — recorded
  as deferred direction in `plans/README.md`.
- Reviewer: check the prune pipeline against filenames with spaces (none
  are produced by the stamp format) and confirm `--if-exists` semantics
  in the restore doc.
