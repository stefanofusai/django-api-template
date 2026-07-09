#!/bin/sh
set -eu

# Archives the bundled Compose media volume through a throwaway tar container,
# restores an archive into the live media volume, or verifies an existing archive
# with tar. Run from the project root (compose -f paths are relative). Schedule
# backups via host cron; copy archives off-host - a backup on the same disk as
# the media volume does not survive host loss. Stop the api service and any
# worker services before restore; restores extract over the existing media tree
# without deleting files created after the backup.

USAGE="usage: media-backup.sh backup <backup-dir> [keep-count]
       media-backup.sh restore <archive> [--force]
       media-backup.sh verify <archive>"

if [ "$#" -lt 1 ]; then
    echo "$USAGE" >&2
    exit 2
fi

COMMAND=$1
shift

TAR_IMAGE=alpine:3.22.2

case $COMMAND in
    backup)
        BACKUP_DIR=${1:?$USAGE}
        KEEP_COUNT=${2:-14}

        case $KEEP_COUNT in
            ''|0|*[!0-9]*) echo "keep-count must be a positive integer" >&2; exit 2 ;;
        esac

        mkdir -p "$BACKUP_DIR"

        STAMP=$(date -u +%Y%m%dT%H%M%SZ)
        TMP_ARCHIVE="$BACKUP_DIR/$STAMP.tar.gz.tmp"
        trap 'rm -f "$TMP_ARCHIVE"' EXIT

        MEDIA_VOLUME=$(
            docker compose -f .docker/compose/prod.yaml --env-file=.env config --format json \
                | python3 -c 'import json, sys; print(json.load(sys.stdin)["volumes"]["media_data"]["name"])'
        )

        docker run --rm \
            -v "$MEDIA_VOLUME":/media:ro \
            "$TAR_IMAGE" \
            tar -czf - -C /media . \
            > "$TMP_ARCHIVE"

        if [ ! -s "$TMP_ARCHIVE" ]; then
            echo "tar produced an empty archive; refusing to promote" >&2
            rm -f "$TMP_ARCHIVE"
            exit 1
        fi

        mv "$TMP_ARCHIVE" "$BACKUP_DIR/$STAMP.tar.gz"
        trap - EXIT

        # Keep the newest KEEP_COUNT archives; timestamps sort lexicographically.
        # Portable "all but newest N": count, then delete the oldest (total - N).
        total=$(find "$BACKUP_DIR" -maxdepth 1 -name '*.tar.gz' -type f | wc -l | tr -d ' ')
        remove=$((total - KEEP_COUNT))
        if [ "$remove" -gt 0 ]; then
            find "$BACKUP_DIR" -maxdepth 1 -name '*.tar.gz' -type f | sort | head -n "$remove" | while read -r old_archive; do
                rm -f "$old_archive"
            done
        fi
        ;;
    restore)
        ARCHIVE=${1:?$USAGE}
        FORCE=${2:-}

        if [ -n "$FORCE" ] && [ "$FORCE" != "--force" ]; then
            echo "$USAGE" >&2
            exit 2
        fi

        if [ ! -f "$ARCHIVE" ]; then
            echo "no such archive: $ARCHIVE" >&2
            exit 2
        fi

        if ! tar -tzf "$ARCHIVE" >/dev/null; then
            echo "archive cannot be read by tar: $ARCHIVE" >&2
            exit 2
        fi

        if ! tar -tzf "$ARCHIVE" | awk '
            $0 == "" || $0 ~ /^\// || $0 ~ /(^|\/)\.\.(\/|$)/ { bad = 1 }
            END { exit bad }
        '; then
            echo "archive contains unsafe media paths: $ARCHIVE" >&2
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

        MEDIA_VOLUME=$(
            docker compose -f .docker/compose/prod.yaml --env-file=.env config --format json \
                | python3 -c 'import json, sys; print(json.load(sys.stdin)["volumes"]["media_data"]["name"])'
        )

        docker run --rm -i \
            -v "$MEDIA_VOLUME":/media \
            "$TAR_IMAGE" \
            tar -xzf - -C /media \
            < "$ARCHIVE"
        ;;
    verify)
        ARCHIVE=${1:?$USAGE}
        if [ ! -f "$ARCHIVE" ]; then
            echo "no such archive: $ARCHIVE" >&2
            exit 2
        fi

        FIRST_ENTRY=$(tar -tzf "$ARCHIVE" | sed -n '1p')
        if [ -z "$FIRST_ENTRY" ]; then
            echo "archive contains no media entries: $ARCHIVE" >&2
            exit 1
        fi

        echo "verify OK: $ARCHIVE contains media entries"
        ;;
    *)
        echo "$USAGE" >&2
        exit 2
        ;;
esac
