#!/bin/sh
set -eu

# Dumps the bundled Compose Postgres with pg_dump custom format and
# prunes old dumps. Run from the project root (compose -f paths are
# relative). Schedule via host cron; copy dumps off-host — a backup on
# the same disk as the database does not survive host loss.

BACKUP_DIR=${1:?usage: postgres-backup.sh <backup-dir> [keep-count]}
KEEP_COUNT=${2:-14}

case $KEEP_COUNT in
    ''|0|*[!0-9]*) echo "keep-count must be a positive integer" >&2; exit 2 ;;
esac

mkdir -p "$BACKUP_DIR"

STAMP=$(date -u +%Y%m%dT%H%M%SZ)
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

# Keep the newest KEEP_COUNT dumps; timestamps sort lexicographically.
# Portable "all but newest N": count, then delete the oldest (total - N).
total=$(find "$BACKUP_DIR" -maxdepth 1 -name '*.dump' -type f | wc -l | tr -d ' ')
remove=$((total - KEEP_COUNT))
if [ "$remove" -gt 0 ]; then
    find "$BACKUP_DIR" -maxdepth 1 -name '*.dump' -type f | sort | head -n "$remove" | while read -r old_dump; do
        rm -f "$old_dump"
    done
fi
