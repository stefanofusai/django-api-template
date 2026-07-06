# Plan 001: Run the baked test suite against real PostgreSQL

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving to the
> next step. If anything in the "STOP conditions" section occurs, stop and
> report — do not improvise. When done, update the status row for this plan
> in `plans/README.md` — unless a reviewer dispatched you and told you they
> maintain the index.
>
> **Drift check (run first)**:
> `git diff --stat d333a73..HEAD -- '{{cookiecutter.project_slug}}/pyproject.toml' '{{cookiecutter.project_slug}}/.github' '{{cookiecutter.project_slug}}/.docker/compose/dev.yaml' '{{cookiecutter.project_slug}}/.docker/Dockerfile' .github/workflows/ci.yaml README.md`
> If any in-scope file changed since this plan was written, compare the
> "Current state" excerpts against the live code before proceeding; on a
> mismatch, treat it as a STOP condition.

## Status

- **Priority**: P1
- **Effort**: M
- **Risk**: MED
- **Depends on**: none (run FIRST — plan 002 edits the same workflow files)
- **Category**: tests
- **Planned at**: commit `d333a73`, 2026-07-05

## Why this matters

The generated project targets PostgreSQL in every real environment
(psycopg is the only DB driver dependency; dev/prod compose run
`postgres:18.4`), but the test suite runs against `sqlite:///:memory:`.
SQLite hides engine differences that matter in production — type coercion
looseness, transaction/locking semantics, constraint enforcement details —
and it means the shipped migrations are never exercised against the real
engine by the suite. The maintainer has decided tests must run on real
PostgreSQL. This is an explicit maintainer mandate; the old audit note
"real-backend test lane superseded by the compose smoke test" is
overridden.

## Current state

This repo is a **cookiecutter template**. The generated project lives
under the literal directory `{{cookiecutter.project_slug}}/` (quote it in
shell). Files inside it contain Jinja (`{{ cookiecutter.* }}`,
`{% if %}`) that must stay valid. Two paths are copied **without**
rendering (see `cookiecutter.json` `_copy_without_render`):
`.github/workflows/*` and `.agents/*` — those files must NOT contain Jinja
or slug-derived values.

Relevant files:

- `{{cookiecutter.project_slug}}/pyproject.toml` — pytest config; the
  SQLite pin lives here:

  ```toml
  # pyproject.toml:89-105
  [tool.pytest.ini_options]
  DJANGO_SETTINGS_MODULE = "config.settings"
  addopts = "--cov=src --cov-fail-under=100 --cov-report=term-missing:skip-covered --numprocesses=auto"
  env = [
      "ALLOWED_HOSTS=localhost,127.0.0.1,testserver",
      "CACHE_URL=locmemcache://",
      "DATABASE_URL=sqlite:///:memory:",
      "DJANGO_ENV=ci",
      "SECRET_KEY=ci-secret-for-tests-0123456789-abcdefghijklmnopqrstuvwxyz",
  ]
  ```

  Note: `pyproject.toml` IS rendered by cookiecutter, so it may use
  `{{ cookiecutter.* }}` expressions.

- `{{cookiecutter.project_slug}}/src/config/settings/components/database.py`
  — DB comes solely from the `DATABASE_URL` env var:

  ```python
  DATABASES = {"default": env.db("DATABASE_URL")}
  DATABASES["default"]["CONN_HEALTH_CHECKS"] = True
  DATABASES["default"]["CONN_MAX_AGE"] = env.int("CONN_MAX_AGE", default=60)
  ```

- `{{cookiecutter.project_slug}}/src/config/settings/environments/ci.py` —
  the CI overlay does NOT touch the database; no change needed there.

- `{{cookiecutter.project_slug}}/.github/workflows/tests.yaml` — runs
  `uv run --group=ci --locked --no-default-groups pytest` directly on the
  runner with **no service containers** (28 lines total; steps: checkout,
  setup-python, setup-uv, `uv sync`, `./.github/scripts/deploy-check.sh`,
  pytest). Copied without rendering — keep it slug-free.

- `.github/workflows/ci.yaml` (repo root) — the `bake` job (9 matrix
  cases) bakes a project and runs `uv run pytest` at lines 71-73, also
  with no service containers.

- `{{cookiecutter.project_slug}}/.docker/compose/dev.yaml:93-107` — the
  dev `postgres` service (image `postgres:18.4`, healthcheck via
  `pg_isready`) publishes **no host port**, so host-run pytest cannot
  reach it today.

- `{{cookiecutter.project_slug}}/.env.example:19-29` — dev compose
  Postgres credentials: `POSTGRES_DB`, `POSTGRES_PASSWORD`,
  `POSTGRES_USER` all default to the underscored slug
  (`{{ cookiecutter.project_slug.replace('-', '_') }}`). The official
  postgres image makes `POSTGRES_USER` a **superuser**, so it can create
  test databases.

- `{{cookiecutter.project_slug}}/.github/scripts/deploy-check.sh:10` —
  `DATABASE_URL=sqlite:///:memory:` used for
  `manage.py check --deploy --fail-level=WARNING --tag=security`. This
  command never opens a DB connection; the URL is parse-only.

- `{{cookiecutter.project_slug}}/.docker/Dockerfile:40` — the same
  parse-only `DATABASE_URL=sqlite:///:memory:` throwaway value for the
  `collectstatic` RUN (comment at lines 32-33 explains).

- Docs that currently state the SQLite arrangement:
  - Root `README.md:50-51` (Design Decisions): "PostgreSQL is the
    database target; SQLite is used only by the CI test overlay."
  - Baked `{{cookiecutter.project_slug}}/README.md:50-54` (Architecture):
    "`ci` uses SQLite, eager Celery tasks, and in-memory storage." (two
    Jinja branches)
  - Baked `README.md:409-415` (Testing): "The suite uses CI settings,
    in-memory SQLite and storage, …" (two Jinja branches)
  - Baked `README.md:433-443` and root `README.md:139-149`
    (Verification): list `uv run pytest` with no Postgres prerequisite.
  - Root `AGENTS.md:112-118` (Verification): same list.

Key mechanics the design relies on (verified during planning):

- **pytest-env `D:` prefix**: an `env` entry written as `D:VAR=value` is
  a *default* — it is only applied when `VAR` is not already set in the
  environment. Plain entries override the environment unconditionally.
  This lets CI inject its own `DATABASE_URL` while local runs fall back
  to the dev-compose URL.
- **pytest-django + xdist**: the suite runs `--numprocesses=auto`;
  pytest-django creates one test database per worker by suffixing the
  name (`test_<name>_gw0`, `test_<name>_gw1`, …). Creating them requires
  the `CREATEDB` privilege — satisfied because both the dev-compose user
  and the CI service user are superusers.
- **Django + Postgres test DB creation** connects to the `postgres`
  maintenance database to `CREATE DATABASE`, so the database named in
  `DATABASE_URL` does not itself need to exist before the run.

## Commands you will need

All from the repo root unless stated. `rtk` prefix optional if available.

| Purpose | Command | Expected on success |
|---------|---------|---------------------|
| Bake a project | `uvx cookiecutter . --no-input -o /tmp/plan001` | `/tmp/plan001/my-project` exists |
| Install baked deps | `cd /tmp/plan001/my-project && uv sync --locked` | exit 0 |
| Throwaway Postgres | `docker run -d --name plan001-pg -p 5432:5432 -e POSTGRES_DB=postgres -e POSTGRES_PASSWORD=postgres -e POSTGRES_USER=postgres postgres:18.4` | container running |
| Baked tests (CI-style) | `DATABASE_URL=postgres://postgres:postgres@localhost:5432/postgres uv run pytest` | all pass, 100% coverage |
| Baked pre-commit | `git add -A && uv run pre-commit run --all-files` | exit 0 |
| Root pre-commit | `pre-commit run --all-files` | exit 0 |
| Cleanup | `docker rm -f plan001-pg` | removed |

## Scope

**In scope** (the only files you should modify):

- `{{cookiecutter.project_slug}}/pyproject.toml` (pytest `env` list only)
- `{{cookiecutter.project_slug}}/.docker/compose/dev.yaml` (postgres
  `ports` only)
- `{{cookiecutter.project_slug}}/.github/workflows/tests.yaml`
- `{{cookiecutter.project_slug}}/.github/scripts/deploy-check.sh`
- `{{cookiecutter.project_slug}}/.docker/Dockerfile` (the throwaway
  `DATABASE_URL` value only)
- `.github/workflows/ci.yaml` (the `bake` job only)
- `README.md` (root; Design Decisions + Verification wording)
- `{{cookiecutter.project_slug}}/README.md` (Architecture, Testing,
  Verification wording)
- `AGENTS.md` (root; Verification note)

**Out of scope** (do NOT touch):

- `CACHE_URL=locmemcache://` in the pytest env — the cache stays fake in
  tests by maintainer choice; real Redis fidelity is covered by the
  compose smoke test. Do not add a Redis service anywhere.
- `.docker/compose/prod.yaml`, the `docker-compose-smoke` and
  `docker-build` CI jobs, `.pre-commit-config.yaml`.
- Coverage configuration and `--cov-fail-under=100`.
- The CI settings overlay `ci.py` (it has no DB knowledge).

## Git workflow

- Work directly on `main`; do not create or switch to a plan branch unless the
  operator explicitly asks.
- Do NOT commit, push, or open a PR unless the operator explicitly instructs it.
- If asked to commit, use a conventional commit such as
  `test: run the suite against real PostgreSQL` (repo history uses
  `feat:`/`docs:`/`build:` prefixes).

## Steps

### Step 1: Make the pytest DATABASE_URL a Postgres default

In `{{cookiecutter.project_slug}}/pyproject.toml`, replace the line

```toml
    "DATABASE_URL=sqlite:///:memory:",
```

with

```toml
    "D:DATABASE_URL=postgres://{{ cookiecutter.project_slug.replace('-', '_') }}:{{ cookiecutter.project_slug.replace('-', '_') }}@localhost:5432/{{ cookiecutter.project_slug.replace('-', '_') }}",
```

Keep the list ordered alphabetically by variable name (the `D:` prefix
does not change its sort position). The default matches the dev-compose
credentials in `.env.example`, so a developer who has the dev stack's
Postgres running (Step 2 publishes its port) can run `uv run pytest` with
zero setup; CI overrides the variable (Step 3).

**Verify**: `grep -n "DATABASE_URL" '{{cookiecutter.project_slug}}/pyproject.toml'`
→ exactly one match, the new `D:`-prefixed line.

### Step 2: Publish the dev Postgres port to localhost

In `{{cookiecutter.project_slug}}/.docker/compose/dev.yaml`, add to the
`postgres` service (after `image:`, matching the key order used by the
`api` service — alphabetical-ish; place `ports:` between `image:` and
`volumes:`):

```yaml
    # Published for host-run pytest, which defaults DATABASE_URL to this
    # service (see [tool.pytest.ini_options] env). Bound to loopback only.
    ports:
      - "127.0.0.1:5432:5432"
```

**Verify**: bake (`uvx cookiecutter . --no-input -o /tmp/plan001-step2`)
and run `docker compose -f .docker/compose/dev.yaml config` inside the
baked project after `cp .env.example .env` → renders without error and
shows the published port. (If Docker is unavailable, `uvx --from
yamllint yamllint .docker/compose/dev.yaml` on the baked file must pass.)

### Step 3: Add a Postgres service to the baked tests workflow

`{{cookiecutter.project_slug}}/.github/workflows/tests.yaml` is copied
without rendering — use only static values. Give the `pytest` job:

```yaml
    services:
      postgres:
        # Keep this image in sync with .docker/compose/{dev,prod}.yaml;
        # Dependabot does not track images inside workflow service blocks.
        image: postgres:18.4
        env:
          POSTGRES_DB: postgres
          POSTGRES_PASSWORD: postgres
          POSTGRES_USER: postgres
        ports:
          - 5432:5432
        options: >-
          --health-cmd="pg_isready --username=postgres"
          --health-interval=5s
          --health-retries=5
          --health-timeout=5s
```

and set the override on the test step so the slug-free URL wins over the
rendered default (pytest-env only applies `D:` entries when the variable
is unset):

```yaml
      - name: Run tests
        env:
          DATABASE_URL: postgres://postgres:postgres@localhost:5432/postgres
        run: uv run --group=ci --locked --no-default-groups pytest
```

Follow the repo YAML style: extended block style, no flow sequences.

**Verify**: `uvx --from actionlint actionlint '{{cookiecutter.project_slug}}/.github/workflows/tests.yaml'`
→ exit 0. (actionlint is also a root pre-commit hook; the final
`pre-commit run --all-files` re-checks it.)

### Step 4: Add the same service to the root bake job

In `.github/workflows/ci.yaml`, add an identical `services:` block to the
`bake` job (all 9 matrix cases share it), and the same
`env: DATABASE_URL: postgres://postgres:postgres@localhost:5432/postgres`
on its `Run tests` step (lines 71-73). Do not touch the other jobs.

**Verify**: `uvx --from actionlint actionlint .github/workflows/ci.yaml`
→ exit 0.

### Step 5: Remove the last SQLite references from the parse-only sites

Both sites never open a DB connection; keep them parse-only but aligned
with the Postgres-only story:

- `{{cookiecutter.project_slug}}/.github/scripts/deploy-check.sh:10`:
  replace `DATABASE_URL=sqlite:///:memory: \` with
  `DATABASE_URL=postgres://postgres:postgres@localhost:5432/postgres \`
- `{{cookiecutter.project_slug}}/.docker/Dockerfile:40`: same
  replacement. The existing comment ("Throwaway values: …") already
  explains these are never read at runtime; extend it with
  "; the DATABASE_URL is parse-only — no connection is made."

**Verify**: `grep -rn "sqlite" '{{cookiecutter.project_slug}}'
--include='*.sh' --include='Dockerfile' --include='*.toml'` → no matches.

### Step 6: Update the documentation

- Root `README.md` Design Decisions: replace the bullet
  "PostgreSQL is the database target; SQLite is used only by the CI test
  overlay." with
  "PostgreSQL is the database target everywhere, including tests: the
  suite runs against a real Postgres so migrations and engine semantics
  are exercised."
- Root `README.md` Verification section: before `uv run pytest`, add a
  line noting tests need a reachable Postgres, e.g.
  `docker compose -f .docker/compose/dev.yaml up -d postgres` (after
  `cp .env.example .env`).
- Root `AGENTS.md` Verification: same note, one bullet.
- Baked `{{cookiecutter.project_slug}}/README.md`:
  - Architecture overlay bullets (both Jinja branches): "`ci` uses
    SQLite" → "`ci` uses eager Celery tasks and in-memory storage; the
    database always comes from `DATABASE_URL`" (adapt each branch).
  - Testing section (both branches): replace "in-memory SQLite and
    storage" wording with real-Postgres wording, and add before the
    `uv run pytest` block:

    ```shell
    docker compose -f .docker/compose/dev.yaml up -d postgres
    ```

    plus one sentence: tests connect to `localhost:5432` by default and
    honor a `DATABASE_URL` environment override; pytest-xdist creates
    per-worker `test_*_gwN` databases.
  - Verification section: add the same `up -d postgres` line before
    `uv run pytest`.

**Verify**: `grep -rni "sqlite" README.md AGENTS.md '{{cookiecutter.project_slug}}/README.md'`
→ no matches.

### Step 7: Full bake verification (default + hyphenated slug)

```shell
docker run -d --name plan001-pg -p 5432:5432 \
  -e POSTGRES_DB=postgres -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_USER=postgres postgres:18.4
uvx cookiecutter . --no-input -o /tmp/plan001
cd /tmp/plan001/my-project && uv sync --locked
DATABASE_URL=postgres://postgres:postgres@localhost:5432/postgres \
  uv run pytest
git add -A && uv run pre-commit run --all-files
```

Then repeat the bake + pytest with a hyphenated slug to prove the
rendered default URL is well-formed even though CI overrides it:

```shell
uvx cookiecutter . --no-input -o /tmp/plan001b project_name="My API Server 2"
cd /tmp/plan001b/my-api-server-2 && uv sync --locked
DATABASE_URL=postgres://postgres:postgres@localhost:5432/postgres \
  uv run pytest
grep -n "D:DATABASE_URL=postgres://my_api_server_2:" pyproject.toml
```

Also prove the **default** path (no env override) works against
slug-credential Postgres:

```shell
docker rm -f plan001-pg
docker run -d --name plan001-pg -p 5432:5432 \
  -e POSTGRES_DB=my_project -e POSTGRES_PASSWORD=my_project \
  -e POSTGRES_USER=my_project postgres:18.4
cd /tmp/plan001/my-project && uv run pytest
docker rm -f plan001-pg
```

**Verify**: all three pytest runs pass with 100% coverage; the grep shows
the underscored slug in the default URL.

### Step 8: Root repo checks

```shell
pre-commit run --all-files
```

**Verify**: exit 0.

## Test plan

No new test files: the change is infrastructure. The gates are the three
full-suite runs in Step 7 (CI-style override, hyphenated slug, and
default-URL path), which together exercise: migrations applied on real
Postgres, xdist per-worker DB creation, and the pytest-env `D:` fallback.

## Done criteria

Machine-checkable. ALL must hold:

- [ ] `grep -rn "sqlite" '{{cookiecutter.project_slug}}'` → no matches
      (any file)
- [ ] Baked default project: `DATABASE_URL=postgres://postgres:postgres@localhost:5432/postgres uv run pytest`
      exits 0 at 100% coverage with a live Postgres
- [ ] Baked default project: `uv run pytest` (no env override) exits 0
      against a Postgres with slug credentials on `localhost:5432`
- [ ] `actionlint` passes on both workflow files
- [ ] Baked `pre-commit run --all-files` and root
      `pre-commit run --all-files` exit 0
- [ ] `git status` shows no modified files outside the in-scope list
- [ ] `plans/README.md` status row updated

## STOP conditions

Stop and report back (do not improvise) if:

- Docker is unavailable or cannot run a Postgres container on this
  machine — the suite can no longer be verified without one.
- Host port 5432 is already occupied and cannot be freed. (Do NOT
  silently pick another port: the default URL, dev compose mapping, and
  docs all assume 5432. Report so the maintainer can choose a port.)
- `uv run pytest` fails with the env override set even though Postgres is
  healthy — pytest-env may not be honoring the `D:` prefix in the pinned
  version (`pytest-env==1.6.0` supports it; if behavior differs, report).
- Any existing test fails on Postgres for a reason that looks like an
  engine-behavior difference (not wiring) — that is a real finding the
  maintainer must see, not something to patch around.
- The tests.yaml change would require Jinja/slug values — it must stay
  render-free.

## Maintenance notes

- The `postgres:18.4` pin now lives in FOUR places: dev.yaml, prod.yaml,
  and the two workflow service blocks. Dependabot bumps the compose
  files only — workflow service images must be bumped by hand (comment
  added in Step 3 warns about this).
- Any future plan adding a required env var to the pytest environment
  must decide plain vs `D:`-prefixed: plain entries silently override
  developer shells; `D:` entries can be overridden by CI and developers.
- Plan 002 adds a migration-drift gate to the same workflows — execute it
  after this plan to avoid merge friction.
- Deferred follow-up (not planned): document `--reuse-db` for faster
  local iteration; today every run recreates the test databases.
