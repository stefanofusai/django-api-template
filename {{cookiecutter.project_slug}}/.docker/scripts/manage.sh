#!/bin/sh
set -eu

# Runs a Django management command inside the running production api
# container. Run from the project root. Interactive commands
# (createsuperuser, shell, dbshell) work: exec allocates a TTY when the
# invoking terminal has one.

: "${1:?usage: manage.sh <command> [args...]}"

exec docker compose -f .docker/compose/prod.yaml --env-file=.env \
    exec api python manage.py "$@"
