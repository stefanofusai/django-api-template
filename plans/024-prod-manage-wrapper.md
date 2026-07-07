# Plan 024: Ship `manage.sh` — a production wrapper for `manage.py` commands against the running stack

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving on. If
> anything in "STOP conditions" occurs, stop and report — do not improvise.
> When done, update this plan's status row in `plans/README.md` — unless a
> reviewer dispatched you and told you they maintain the index.
>
> **Drift check (run first)**:
> `git diff --stat ae42991..HEAD -- "{{cookiecutter.project_slug}}/.docker/scripts/" "{{cookiecutter.project_slug}}/README.md" "{{cookiecutter.project_slug}}/.docker/Dockerfile"`
> If any changed since this plan was written, compare "Current state" against
> the live files before proceeding; on a mismatch, STOP. (Plans 001/002/022/023
> add or edit sibling scripts and the same README section — reconcile if
> landed.)

## Status

- **Priority**: P3
- **Effort**: S
- **Risk**: LOW (a thin wrapper; no behavior of its own beyond arg passthrough)
- **Depends on**: none (coordinates with 022/023 — same `.docker/scripts/`
  conventions and same README `## Production` prose)
- **Category**: dx / operations
- **Planned at**: commit `ae42991`, 2026-07-07

## Repository context (read before anything else)

This is a **Cookiecutter template**; source under
`{{cookiecutter.project_slug}}/` (**quote it in shell**). `.docker/scripts/*`
is rendered (Jinja allowed; this script needs none). There is **no shellcheck
pre-commit hook** until plan 006 lands — lint with `sh -n` +
`uvx --from shellcheck-py shellcheck <file>` directly. Verification means
baking; the behavioral check needs a booted prod stack (Docker + Compose
≥ 5.3.0).

## Why this matters

Running a management command against production requires this incantation:

```
docker compose -f .docker/compose/prod.yaml --env-file=.env exec api python manage.py <command>
```

It is long, and its failure mode is nasty: reach for the wrong compose file
(`dev.yaml` — muscle memory from local work) and the command silently runs
against the **dev** stack's database. And this is not a rare operation: the
template ships no registration endpoints (a documented decision — see the
credential-provisioning direction note in `plans/README.md`), so
`createsuperuser` is the **day-one operation of every single deployment** —
the only way to mint the first credential. `dbshell`, `shell`, and
`clearsessions` follow the same path. A three-line wrapper removes the
incantation and pins the compose file, matching the repo's convention that
recurring operational commands ship as scripts (`postgres-backup.sh`,
`postgres-restore.sh` — plan 002, `deploy.sh` — plan 022).

## Current state

There is no wrapper: `ls "{{cookiecutter.project_slug}}/.docker/scripts/"` →
`celery-beat.sh`, `celery-worker.sh`, `dev.sh`, `gunicorn.sh`,
`migrations.sh`, `postgres-backup.sh` (plus `postgres-restore.sh`/`deploy.sh`
if plans 002/022 landed). No `manage.sh`.

The exact in-container invocation to mirror —
`{{cookiecutter.project_slug}}/.docker/scripts/migrations.sh` (full file):

```sh
#!/bin/sh
set -eu

python manage.py \
    migrate \
    --no-input
```

i.e. inside the container it is plain `python manage.py …`: the Dockerfile's
runtime stage sets `ENV PATH=/app/.venv/bin:$PATH` (line 69),
`ENV PYTHONPATH=/app/src` (line 71), and `WORKDIR /app` (line 74) — no `uv
run` needed in-container.

`{{cookiecutter.project_slug}}/README.md` `## Production` (line 218+) — the
section where the wrapper gets documented. (Plans 008/009/022 edit nearby
prose; reconcile.)

**Conventions**: `#!/bin/sh` + `set -eu`; `${1:?usage}` argument style; short
flags before long, `--flag=value`; scripts are mode 0755 (the baked
`check-shebang-scripts-are-executable` hook enforces it).

## Commands you will need

| Purpose | Command | Expected |
|---------|---------|----------|
| Bake default | `uvx cookiecutter . --no-input -o /tmp/bake` | contains `manage.sh` |
| Parse check | `sh -n "{{cookiecutter.project_slug}}/.docker/scripts/manage.sh"` | exit 0 |
| Shellcheck | `uvx --from shellcheck-py shellcheck "{{cookiecutter.project_slug}}/.docker/scripts/manage.sh"` | exit 0 |
| Behavioral check | see Step 2 (needs a booted stack) | `manage.sh check` exits 0 |
| Baked + root pre-commit | as in other plans | exit 0 |

## Scope

**In scope**:
- `{{cookiecutter.project_slug}}/.docker/scripts/manage.sh` (create — ships
  for ALL knobs; every bake has `prod.yaml`, so no
  `hooks/post_gen_project.py` deletion rule).
- `{{cookiecutter.project_slug}}/README.md` — document it in `## Production`,
  with `createsuperuser` as the worked example.

**Out of scope**:
- Any dev-stack wrapper (`uv run manage.py …` locally is already trivial and
  documented).
- Whitelisting/restricting which commands may run — the operator is root on
  the host; a filter adds friction, not safety.
- `hooks/post_gen_project.py`.

## Git workflow

- Work directly on `main`. Do NOT branch/commit/push/PR unless told. If asked
  to commit: Conventional Commits, e.g.
  `feat: add manage.sh wrapper for production management commands`.

## Steps

### Step 1: Create `manage.sh`

Create `{{cookiecutter.project_slug}}/.docker/scripts/manage.sh`, mode 0755:

```sh
#!/bin/sh
set -eu

# Runs a Django management command inside the running production api
# container. Run from the project root. Interactive commands
# (createsuperuser, shell, dbshell) work: exec allocates a TTY when the
# invoking terminal has one.

: "${1:?usage: manage.sh <command> [args...]}"

exec docker compose -f .docker/compose/prod.yaml --env-file=.env \
    exec api python manage.py "$@"
```

Load-bearing details:
- **No `-T`**: `docker compose exec` allocates a TTY when attached to one, so
  `createsuperuser`'s prompts work; when invoked from a non-TTY context
  (cron, CI) compose degrades gracefully. Do not add `-T` — it would break
  every interactive command this wrapper exists for.
- **Plain `python manage.py`**, mirroring `migrations.sh` — the container's
  venv is on `PATH` and `WORKDIR` is `/app`; no `uv run`.
- `exec` replaces the shell so exit codes and signals pass through untouched
  (Ctrl-C in a `shell` session behaves correctly).
- The `:` + `${1:?…}` form validates without consuming the argument, so
  `"$@"` forwards everything verbatim.

**Verify**: `sh -n` exit 0; shellcheck exit 0;
`ls -l …/manage.sh` shows `-rwxr-xr-x`.

### Step 2: Behavioral check (needs a booted stack)

Boot a default bake the way the root CI smoke does (prod-safe `.env` via
`uuidgen` placeholders), then from the bake root:

```
./.docker/scripts/manage.sh check
./.docker/scripts/manage.sh shell -c "print('wrapper ok')"
```

**Verify**: `check` exits 0 ("System check identified no issues" or the
prod-expected output); the shell one-liner prints `wrapper ok` and exits 0.
Then `down -v`. If Docker is unavailable, note it in your report — the
wrapper is thin enough that Step 1's static gates plus the excerpt-fidelity
check (invocation matches `migrations.sh` + Dockerfile env) are acceptable,
but say explicitly that the live check did not run.

### Step 3: Document it

In `{{cookiecutter.project_slug}}/README.md` `## Production`, add a short
passage: management commands against the running stack go through
`./.docker/scripts/manage.sh <command>`, with the day-one example
`./.docker/scripts/manage.sh createsuperuser` (the template deliberately
ships no registration endpoints, so this is how the first credential is
minted). Place it near the existing operational prose; keep the style.

**Verify**: `grep -c "manage.sh createsuperuser" "{{cookiecutter.project_slug}}/README.md"` ≥ 1;
root `uvx pre-commit run markdownlint --all-files` exits 0.

### Step 4: Regression

Default bake AND minimal bake
(`use_celery=none email_provider=none use_sentry=no use_s3_media=no
use_traefik=no`): the script ships in both, `sh -n` passes on the rendered
copies, baked pre-commit exits 0. Root pre-commit exits 0.

## Test plan

- No pytest (operational shell; `AGENTS.md` forbids config-only tests).
  Gates: `sh -n` + shellcheck, executable bit, the live `check`/`shell`
  probes (Step 2), README grep, and the two-bake regression.

## Done criteria

ALL must hold:

- [ ] `manage.sh` exists, mode 0755, `#!/bin/sh` + `set -eu`, forwards `"$@"` to `python manage.py` inside the `api` service via the prod compose file, uses `exec`, has no `-T`.
- [ ] `sh -n` + shellcheck clean.
- [ ] Live check ran (`manage.sh check` exit 0 on a booted default bake) OR the report explicitly states Docker was unavailable.
- [ ] README documents the wrapper with `createsuperuser` as the example.
- [ ] Script ships on default and minimal bakes; baked + root pre-commit exit 0.
- [ ] No out-of-scope files modified (`git status`); `plans/README.md` status row updated.

## STOP conditions

Stop and report (do not improvise) if:

- The in-container invocation differs from `migrations.sh`'s
  `python manage.py` pattern (Dockerfile drifted — report before adapting).
- Interactive commands fail through the wrapper on a real TTY (compose exec
  TTY behavior differs from expectations — report the observed behavior).
- shellcheck demands a bashism (shebang stays `/bin/sh`).

## Maintenance notes

- If a future plan renames the compose file or the `api` service, this
  wrapper is one of the touchpoints (grep `.docker/scripts/` for
  `prod.yaml`).
- Piping stdin into the wrapper (e.g. `manage.sh dbshell < dump.sql`) may
  need `-T`; deliberately not handled — `postgres-restore.sh` owns the
  restore path, and other piped uses are rare enough to run the raw compose
  command. Revisit only on real demand.
- A reviewer should scrutinize: `"$@"` quoting (arguments with spaces must
  survive), and that the README example is `createsuperuser` (the day-one
  op), not something generic.
