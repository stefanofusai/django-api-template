#!/bin/sh
set -eu

# Runs a Django management command inside the running production api
# container. Run from the project root. Interactive commands
# (createsuperuser, shell, dbshell) work: exec allocates a TTY when the
# invoking terminal has one.

USAGE="usage: manage.sh <command> [args...]"

if [ "$#" -lt 1 ]; then
    echo "$USAGE" >&2
    exit 2
fi

case $1 in
    -h|--help)
        echo "$USAGE"
        exit 0
        ;;
esac

exec docker compose -f .docker/compose/prod.yaml --env-file=.env \
    exec api python manage.py "$@"
