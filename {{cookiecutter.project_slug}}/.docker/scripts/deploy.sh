#!/bin/sh
set -eu
umask 077

# Deploys a published release by repointing APP_VERSION in .env, pulling the
# image, and replacing the running containers. Rollback IS this script run
# with an earlier tag. Run from the project root. The database schema is not
# rolled back; keep migrations backward-compatible one release back.

USAGE="usage: deploy.sh <tag, e.g. v1.2.3>"

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

APP_VERSION=$1

if ! expr "$APP_VERSION" : 'v[0-9][0-9]*\.[0-9][0-9]*\.[0-9][0-9]*$' >/dev/null; then
    echo "tag must look like v<major>.<minor>.<patch>" >&2
    exit 2
fi

[ -f .env ] || { echo "no .env here; run from the project root" >&2; exit 2; }
{%- if cookiecutter.use_traefik == "yes" %}

command -v docker-rollout >/dev/null 2>&1 || {
    echo "docker-rollout is required for Traefik zero-downtime deploys" >&2
    exit 2
}
{%- endif %}

env_tmp=$(mktemp .env.tmp.XXXXXX)
trap 'rm -f "$env_tmp"' EXIT HUP INT TERM

awk -v app_version="$APP_VERSION" '
    BEGIN { written = 0 }
    /^APP_VERSION=/ {
        if (!written) {
            print "APP_VERSION=" app_version
            written = 1
        }
        next
    }
    { print }
    END {
        if (!written) {
            print "APP_VERSION=" app_version
        }
    }
' .env > "$env_tmp"
mv "$env_tmp" .env
trap - EXIT HUP INT TERM

docker compose -f .docker/compose/prod.yaml --env-file=.env pull
{%- if cookiecutter.use_traefik == "yes" %}
docker rollout -f .docker/compose/prod.yaml --env-file=.env api
{%- endif %}
docker compose -f .docker/compose/prod.yaml --env-file=.env up -d --wait
docker compose -f .docker/compose/prod.yaml --env-file=.env exec -T api \
    curl -fsS -m 3 -o /dev/null \
    http://127.0.0.1:8000/api/ready
