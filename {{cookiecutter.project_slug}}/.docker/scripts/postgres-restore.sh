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
