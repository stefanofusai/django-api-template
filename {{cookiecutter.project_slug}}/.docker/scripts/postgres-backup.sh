#!/bin/sh
set -eu

# Dumps the bundled Compose Postgres with pg_dump custom format, restores a
# dump into the live bundled Compose Postgres, or verifies an existing dump in a
# throwaway container. Run from the project root (compose -f paths are relative).
# Schedule backups via host cron; copy dumps off-host — a backup on the same
# disk as the database does not survive host loss. Stop the api and worker
# services before restore; --clean drops and recreates objects, so a restore
# into a live app corrupts in-flight requests.

USAGE="usage: postgres-backup.sh backup <backup-dir> [keep-count]
       postgres-backup.sh restore <dump-file> [--force]
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
        trap 'rm -f "$TMP_DUMP"' EXIT

        docker compose -f .docker/compose/prod.yaml --env-file=.env exec -T postgres \
            sh -c 'pg_dump --format=custom --username="$POSTGRES_USER" "$POSTGRES_DB"' \
            > "$TMP_DUMP"

        if [ ! -s "$TMP_DUMP" ]; then
            echo "pg_dump produced an empty file; refusing to promote" >&2
            rm -f "$TMP_DUMP"
            exit 1
        fi

        mv "$TMP_DUMP" "$BACKUP_DIR/$STAMP.dump"
        trap - EXIT

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
            RUNNING_SERVICES=$(
                docker compose -f .docker/compose/prod.yaml --env-file=.env ps --services --status=running
            )
            RUNNING_APP_SERVICES=$(
                printf '%s\n' "$RUNNING_SERVICES" \
                    | grep -v -x -e postgres -e redis -e traefik || true
            )

            if [ -n "$RUNNING_APP_SERVICES" ]; then
                echo "refusing to restore while app services are running:" >&2
                echo "$RUNNING_APP_SERVICES" >&2
                echo "stop them first (docker compose ... stop api ...) or pass --force" >&2
                exit 2
            fi
        fi

        docker compose -f .docker/compose/prod.yaml --env-file=.env exec -T postgres \
            sh -c 'pg_restore --clean --dbname="$POSTGRES_DB" --if-exists --username="$POSTGRES_USER"' \
            < "$DUMP_FILE"
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
            psql -At \
                --command="SELECT count(*) FROM django_migrations" \
                --dbname=postgres \
                --username=postgres)
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
