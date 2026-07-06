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
