#!/bin/sh
set -eu

# Deploys a published release by repointing APP_VERSION in .env, pulling the
# image, and replacing the running containers. Rollback IS this script run
# with an earlier tag. Run from the project root. The database schema is not
# rolled back; keep migrations backward-compatible one release back.

APP_VERSION=${1:?usage: deploy.sh <tag, e.g. v1.2.3>}

case $APP_VERSION in
    v[0-9]*.[0-9]*.[0-9]*) ;;
    *) echo "tag must look like v<major>.<minor>.<patch>" >&2; exit 2 ;;
esac

[ -f .env ] || { echo "no .env here; run from the project root" >&2; exit 2; }
{%- if cookiecutter.use_traefik == "yes" %}

command -v docker-rollout >/dev/null 2>&1 || {
    echo "docker-rollout is required for Traefik zero-downtime deploys" >&2
    exit 2
}
{%- endif %}

if grep -q '^APP_VERSION=' .env; then
    sed -i.bak "s/^APP_VERSION=.*/APP_VERSION=$APP_VERSION/" .env
    rm -f .env.bak
else
    printf 'APP_VERSION=%s\n' "$APP_VERSION" >> .env
fi

docker compose -f .docker/compose/prod.yaml --env-file=.env pull
{%- if cookiecutter.use_traefik == "yes" %}
docker rollout -f .docker/compose/prod.yaml --env-file=.env api
{%- endif %}
docker compose -f .docker/compose/prod.yaml --env-file=.env up -d --wait
