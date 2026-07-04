# Plan 008: Add django-celery-beat with a dedicated beat service

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving to the
> next step. If anything in the "STOP conditions" section occurs, stop and
> report — do not improvise. When done, update the status row for this plan
> in `plans/README.md` — unless a reviewer dispatched you and told you they
> maintain the index.
>
> **Drift check (run first)**: `git diff --stat 924bfba..HEAD -- '{{cookiecutter.project_slug}}/pyproject.toml' '{{cookiecutter.project_slug}}/src/config/settings/' '{{cookiecutter.project_slug}}/.docker/' '{{cookiecutter.project_slug}}/README.md'`
> On any change, compare "Current state" excerpts against the live code; on a
> mismatch, treat it as a STOP condition. (Plans 002/007 legitimately touch
> compose files, prod.py and README — expect those diffs.)

## Status

- **Priority**: P2
- **Effort**: M
- **Risk**: LOW–MED (new always-on service; schedule store adds migrations)
- **Depends on**: 002 (healthcheck conventions in compose), recommended after 003 (migrations ordering is otherwise irrelevant)
- **Category**: direction
- **Planned at**: commit `924bfba`, 2026-07-04

## Why this matters

The template ships Celery workers and even vendors a `django-celery-expert`
skill whose `references/periodic-tasks.md` documents Celery Beat — but there
is no beat scheduler service, no `django-celery-beat` dependency, and thus no
way to run periodic tasks. Every real service grows a cron-shaped need;
adding beat *after* the fact means re-deriving service wiring each time. This
plan adds `django-celery-beat` with the **DatabaseScheduler** (schedules
managed in the admin/ORM, consistent with `django-celery-results` already
storing results in the DB) and a dedicated single-instance `beat` compose
service.

Context the maintainer should know (recorded for honesty): the sibling
`../scraper` project was examined as the requested reference — it does NOT use
django-celery-beat; it implements a custom Postgres scheduler
(`apps/scheduler`, `SELECT ... FOR UPDATE SKIP LOCKED`) because it schedules
per-row monitors. For a general-purpose template, django-celery-beat is the
right default; scraper's *service layout conventions* (one process per
concern, scripts in `.docker/scripts/`, settings in one component) are what
this plan borrows.

## Important context: this is a cookiecutter template

- Project code lives under the literal `{{cookiecutter.project_slug}}/` dir —
  quote it in shell. Preserve Jinja placeholders verbatim (compose files use
  `$$` escapes — also preserve).
- Verification = bake + run the baked suite; service behavior via
  `docker compose` locally and Plan 013's CI smoke test.

## Current state

- `{{cookiecutter.project_slug}}/pyproject.toml` deps include
  `celery[redis]==5.6.3`, `django-celery-results==2.6.0` (alphabetized, exact
  pins).
- `{{cookiecutter.project_slug}}/src/config/settings/components/apps.py`
  third-party section:

  ```python
  # Third-party
  "django_celery_results",
  "django_structlog",
  "extra_checks",
  ```

- `{{cookiecutter.project_slug}}/src/config/settings/components/celery.py` —
  alphabetized `CELERY_*` constants, currently no beat settings:

  ```python
  CELERY_ACCEPT_CONTENT = ["json"]
  CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True
  CELERY_BROKER_URL = env("CELERY_BROKER_URL", default="redis://redis:6379/1")
  ...
  ```

- `{{cookiecutter.project_slug}}/.docker/scripts/worker.sh` — the script
  pattern to mirror:

  ```sh
  #!/bin/sh
  set -eu

  exec celery \
      -A config \
      worker \
      --concurrency="$CELERY_WORKER_CONCURRENCY" \
      --hostname=worker@%h \
      --loglevel="$LOG_LEVEL" \
      --max-tasks-per-child="$CELERY_WORKER_MAX_TASKS_PER_CHILD"
  ```

  Scripts are executable (pre-commit `check-shebang-scripts-are-executable`).
- `{{cookiecutter.project_slug}}/.docker/compose/prod.yaml` — services
  `api`, `postgres`, `redis`, `worker` in alphabetical order; the `worker`
  service is the shape to mirror (build/env/DJANGO_ENV/depends_on api
  service_healthy/restart: unless-stopped; dev.yaml adds the manage.py+src
  volumes). Migrations run in api's `pre_start`, and worker's
  `depends_on: api: service_healthy` is what guarantees migrations completed —
  beat needs the same guarantee (DatabaseScheduler reads its tables).
- Admin theme: django-unfold 0.96.0. **Verified: unfold 0.96 has NO
  django_celery_beat contrib module** (`unfold/contrib/` contains constance,
  filters, forms, guardian, hijack, import_export, inlines, location_field,
  simple_history). django-celery-beat registers its own admin classes; they
  will render with default-ish styling inside the unfold shell. Accept this —
  do NOT invent an unfold integration.
- django-celery-beat latest release verified on PyPI at planning time:
  **2.9.0** (2026-02-28). Confirm it declares support for Django 6 before
  pinning (check its classifiers/README on PyPI); per AGENTS.md use the
  latest release at execution time.
- AGENTS.md rules that bind this plan: `celery -A config` (not `--app=`),
  alphabetize compose service keys and list items, long commands multi-line
  with backslashes, "Long-running services should use restart policies".

## Commands you will need

| Purpose | Command | Expected on success |
|---------|---------|---------------------|
| Bake | `uvx cookiecutter . --no-input -o $BAKE` | exit 0 |
| Tests | `cd $BAKE/my-project && uv run pytest` | all pass, 100% |
| Hooks | `cd $BAKE/my-project && git add -A && uv run pre-commit run --all-files` | all pass |
| Migration check (inside bake) | `uv run python manage.py migrate --plan` (env: ci defaults from pyproject) | plan includes `django_celery_beat` migrations |
| Stack (local, needs Docker) | `cp .env.example .env && docker compose -f .docker/compose/dev.yaml up -d --wait` | all services healthy/running |
| Beat log check | `docker compose -f .docker/compose/dev.yaml logs beat` | shows `beat: Starting...` and DatabaseScheduler |

## Scope

**In scope**:
- `{{cookiecutter.project_slug}}/pyproject.toml` (one dependency)
- `{{cookiecutter.project_slug}}/src/config/settings/components/apps.py`
- `{{cookiecutter.project_slug}}/src/config/settings/components/celery.py`
- `{{cookiecutter.project_slug}}/.docker/scripts/beat.sh` (create, executable)
- `{{cookiecutter.project_slug}}/.docker/compose/dev.yaml`
- `{{cookiecutter.project_slug}}/.docker/compose/prod.yaml`
- `{{cookiecutter.project_slug}}/README.md`

**Out of scope**:
- Defining any actual periodic task or schedule entry — projects do that.
- `CELERY_BEAT_SCHEDULE` static entries — DatabaseScheduler is the chosen
  store; both mechanisms at once would be confusing.
- An unfold admin skin for beat models (none exists on the pinned version).
- Custom-scheduler approaches (scraper's design) — recorded above, not built.

## Git workflow

- Branch: `advisor/008-celery-beat`
- Conventional commit, e.g. `feat: add django-celery-beat scheduler service`
- Do NOT push or open a PR unless the operator instructed it.

## Steps

### Step 1: Dependency + installed app + scheduler setting

1. `pyproject.toml` deps: add `"django-celery-beat==2.9.0",` (alphabetical:
   before `django-celery-results`; bump if PyPI has newer — verify Django 6
   support first).
2. `components/apps.py` third-party section: add `"django_celery_beat",`
   before `"django_celery_results",`.
3. `components/celery.py`: add in alphabetical position (after
   `CELERY_ACCEPT_CONTENT`, before `CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP`):

   ```python
   CELERY_BEAT_SCHEDULER = "django_celery_beat.schedulers:DatabaseScheduler"
   ```

**Verify**: fresh bake → `uv run pytest` → all pass, 100% (django-celery-beat
adds migrations that pytest-django applies; no src code was added, so
coverage is unaffected). Then `uv run python manage.py migrate --plan` inside
the bake (with the pyproject ci env, e.g. via
`DJANGO_ENV=ci ... uv run python manage.py migrate --plan` using the same env
values pytest uses) → the plan lists `django_celery_beat` migrations.

### Step 2: beat.sh

Create `{{cookiecutter.project_slug}}/.docker/scripts/beat.sh` (mode 755 —
`chmod +x` after creating; the pre-commit hooks fail otherwise):

```sh
#!/bin/sh
set -eu

exec celery \
    -A config \
    beat \
    --loglevel="$LOG_LEVEL"
```

(The scheduler class comes from settings; no CLI flag needed.)

**Verify**: `test -x '{{cookiecutter.project_slug}}/.docker/scripts/beat.sh'`
→ exit 0.

### Step 3: Compose services

Add a `beat` service to BOTH compose files, alphabetically placed (between
`api` and `postgres`). Mirror the `worker` service of the same file exactly
(build/env_file/environment/depends_on/restart/volumes), with two deltas:
`command: /app/.docker/scripts/beat.sh` and **no healthcheck** (beat exposes
no cheap liveness signal; a failing beat exits and the restart policy
restarts it — state that in the README). Keep `depends_on: api:
service_healthy` (guarantees migrations, which DatabaseScheduler's tables
need). prod.yaml: `restart: unless-stopped`; dev.yaml: include the
`manage.py` + `src` volume mounts like worker.

**Only one beat instance may run** — do not add replicas; note it in the
README (Step 4).

**Verify**: in a bake, `cp .env.example .env && docker compose -f
.docker/compose/dev.yaml config` → renders, `beat` present with the exact
worker-derived shape. If Docker available: `up -d --wait` → beat container
running; `docker compose -f .docker/compose/dev.yaml logs beat` → shows
DatabaseScheduler startup; `down -v`.

### Step 4: README

- Architecture/Local Setup: add `beat` to the service list ("the development
  Compose file starts `api`, `beat`, `postgres`, `redis`, and `worker`" —
  alphabetical).
- Add a short "Periodic tasks" paragraph: schedules are managed in the Django
  admin (Periodic tasks section) via django-celery-beat's DatabaseScheduler;
  run exactly ONE beat instance; beat has no healthcheck — it relies on the
  restart policy.

**Verify**: `uv run pre-commit run markdownlint --all-files` in bake → passes.

### Step 5: Full verification loop

**Verify**: fresh bake → `uv run pytest` → all pass, 100%;
`git add -A && uv run pre-commit run --all-files` → all pass; compose config
renders for BOTH dev and prod files.

## Test plan

No new pytest tests: the app's migrations are exercised by the existing suite
(pytest-django migrates the test DB), and scheduler behavior is
django-celery-beat's own tested code. Service-level verification is Step 3's
local `up -d --wait` + beat log check, and permanently Plan 013's smoke test
(which must assert the beat container is running — see that plan).

## Done criteria

- [ ] `grep -n "django-celery-beat" '{{cookiecutter.project_slug}}/pyproject.toml'` → one exact pin
- [ ] `grep -n "django_celery_beat" '{{cookiecutter.project_slug}}/src/config/settings/components/apps.py'` → present, before django_celery_results
- [ ] `grep -n "CELERY_BEAT_SCHEDULER" '{{cookiecutter.project_slug}}/src/config/settings/components/celery.py'` → DatabaseScheduler
- [ ] `beat.sh` exists and is executable
- [ ] Both compose files contain a `beat` service; `docker compose config` renders both
- [ ] Baked project: `uv run pytest` → all pass, 100%
- [ ] Baked project: `uv run pre-commit run --all-files` → all pass
- [ ] No files outside the in-scope list modified (`git status`)
- [ ] `plans/README.md` status row updated

## STOP conditions

- django-celery-beat's latest release does not declare Django 6 support, or
  the bake's `uv lock` fails to resolve it against Django 6.0.6 — report the
  version conflict; do not downgrade Django.
- Its migrations fail under the sqlite ci test settings (would break the 100%
  suite) — report.
- The admin renders broken (not merely unstyled) beat pages under unfold —
  report with a screenshot/description; do not write custom admin classes.

## Maintenance notes

- Plan 013's smoke test should assert `beat` is in `running` state (it has no
  healthcheck, so `--wait` doesn't gate on it — the assertion is a `docker
  compose ps` state check).
- When the first periodic task is added, it should follow Plan 006's
  documented result policy (`ignore_result` default; opt in when needed) and
  be idempotent (at-least-once delivery).
- django-celery-beat's tables ride the normal migration path; nothing special
  on upgrades beyond `migrate` in `pre_start`.
