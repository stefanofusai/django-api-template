#!/bin/sh
set -eu

# Dumps the bundled Compose Postgres with pg_dump custom format and
# prunes old dumps, or verifies an existing dump in a throwaway container.
# Run from the project root (compose -f paths are relative). Schedule via
# host cron; copy dumps off-host — a backup on the same disk as the database
# does not survive host loss.

USAGE="usage: postgres-backup.sh backup <backup-dir> [keep-count]
       postgres-backup.sh verify <dump-file>"

if [ "$#" -lt 1 ]; then
    echo "$USAGE" >&2
    exit 2
fi

COMMAND=$1
shift

case $COMMAND in
    backup)
        BACKUP_DIR=${1:?$USAGE}
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
        ;;
    verify)
        DUMP_FILE=${1:?$USAGE}
        if [ ! -f "$DUMP_FILE" ]; then
            echo "no such dump file: $DUMP_FILE" >&2
            exit 2
        fi

        POSTGRES_IMAGE=$(grep -E '^ *image: postgres:' .docker/compose/prod.yaml | awk '{print $2}')
        if [ -z "$POSTGRES_IMAGE" ]; then
            echo "could not read postgres image from prod.yaml" >&2
            exit 2
        fi

        CONTAINER="backup-verify-$$"
        trap 'docker rm -f "$CONTAINER" >/dev/null 2>&1 || true' EXIT

        docker run -d -e POSTGRES_PASSWORD=backup-verify --name "$CONTAINER" \
            "$POSTGRES_IMAGE" >/dev/null

        tries=0
        until docker exec "$CONTAINER" pg_isready --username=postgres >/dev/null 2>&1; do
            tries=$((tries + 1))
            if [ "$tries" -ge 30 ]; then
                echo "throwaway postgres never became ready" >&2
                exit 1
            fi
            sleep 1
        done

        docker exec -i "$CONTAINER" \
            pg_restore --clean --dbname=postgres --if-exists --no-owner \
                --username=postgres \
            < "$DUMP_FILE"

        MIGRATIONS=$(docker exec "$CONTAINER" \
            psql --dbname=postgres --username=postgres -tAc \
                "SELECT count(*) FROM django_migrations")
        if [ "$MIGRATIONS" -le 0 ]; then
            echo "restore produced no django_migrations rows" >&2
            exit 1
        fi

        echo "verify OK: $DUMP_FILE restored cleanly ($MIGRATIONS migrations)"
        ;;
    *)
        echo "$USAGE" >&2
        exit 2
        ;;
esac
