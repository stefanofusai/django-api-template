# Plan 014: Ship an `export_openapi_schema` command and a CI job that publishes the schema artifact

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving on. If
> anything in "STOP conditions" occurs, stop and report — do not improvise.
> When done, update this plan's status row in `plans/README.md` — unless a
> reviewer dispatched you and told you they maintain the index.
>
> **Drift check (run first)**:
> `git diff --stat ae42991..HEAD -- "{{cookiecutter.project_slug}}/src/apps/api" "{{cookiecutter.project_slug}}/pyproject.toml" .github/workflows/ci.yaml`
> If any in-scope file changed since this plan was written, compare "Current
> state" against the live code before proceeding; on a mismatch, STOP.

## Status

- **Priority**: P3
- **Effort**: S–M
- **Risk**: LOW
- **Depends on**: none
- **Category**: dx
- **Planned at**: commit `ae42991`, 2026-07-07 (re-verified against live code same day)

## Repository context (read before anything else)

This is a **Cookiecutter template**. Source is under the literal directory
`{{cookiecutter.project_slug}}/` — **quote it in shell**. Files inside contain
Jinja that must stay valid.

- The baked project enforces **100% test coverage** on `src/` (`pyproject.toml`:
  `--cov=src --cov-fail-under=100`). **Any new file under `src/` must be fully
  covered by a test in this same plan**, or the suite fails.
- **`.github/workflows/*` and `.agents/*` inside `{{cookiecutter.project_slug}}/`
  are copied WITHOUT rendering** — no Jinja there. Knob-conditional logic for
  workflows lives in rendered `.github/scripts/*.sh` (see `deploy-check.sh`,
  `migrations-check.sh` for the pattern).
- The **repo-root** `.github/workflows/ci.yaml` is the template's own CI and IS
  an author-time YAML file you may edit.
- **Verification means baking**: `uvx cookiecutter . --no-input -o /tmp/bake`.
  Baked tests need a running `postgres:18.4`.

## Why this matters

The project already produces an OpenAPI schema (django-ninja serves it at
`/api/openapi.json` and `/api/v1/openapi.json`, and the Schemathesis contract
test in `tests/api/integration/schema_test.py` loads it). But there is no
first-class way to **emit the schema as a file** — for committing to a repo,
diffing across changes in review, or feeding a typed-client generator
(openapi-generator, `openapi-typescript`, etc.). Consumers of an API service
routinely need exactly that. A tiny management command plus a CI step that
publishes the schema as a build artifact turns the already-present schema into
a usable deliverable, at near-zero maintenance cost and consistent with the
template's "everything the API layer needs is already here" posture.

## Current state

`{{cookiecutter.project_slug}}/src/apps/api/api.py` constructs two
`NinjaAPI` instances:

```python
internal_api = NinjaAPI(title=f"{project_name} (internal)", docs_decorator=docs_decorator, urls_namespace="internal")
# ... health + ready routers ...
v1_api = NinjaAPI(title=project_name, version="1.0.0", docs_decorator=docs_decorator, urls_namespace="v1")
{%- if cookiecutter.use_example_api == "yes" %}
v1_api.add_router("/notes", notes_router)
{%- endif %}
```

`django-ninja`'s `NinjaAPI` exposes `.get_openapi_schema()`, which returns the
schema as a dict-like `OpenAPISchema` (no server or DB needed — it introspects
registered routes). `project_name` comes from `config.pyproject` (see
`src/config/pyproject.py`).

There is **no** `management/` directory under any app today
(`find "{{cookiecutter.project_slug}}/src" -type d -name management` → empty).

**Conventions (from `AGENTS.md`)**:
- Tests live in `tests/<app>/{unit,integration}/`; the marker is derived from
  the path segment by `tests/conftest.py`. A management-command test is a unit
  test → `tests/api/unit/`.
- Test file names end `_test.py`; test names follow
  `test_<subject>_<expected>_when_<condition>`; functions alphabetized.
- Ruff selects `ALL`; keep imports/typing tidy. Never add
  `from __future__ import annotations`.
- Only add comments that state constraints the code can't show.
- Pin any new dependency to an exact latest version (this plan needs **none**).

## Commands you will need

| Purpose | Command | Expected |
|---------|---------|----------|
| Bake default | `uvx cookiecutter . --no-input -o /tmp/bake` | `/tmp/bake/my-project/` |
| Run command (stdout) | `cd /tmp/bake/my-project && DJANGO_ENV=ci CACHE_URL=locmemcache:// SECRET_KEY=x ALLOWED_HOSTS=localhost DATABASE_URL=postgres://postgres:postgres@localhost:5432/postgres uv run manage.py export_openapi_schema --api=v1` | valid JSON on stdout, exit 0 |
| Baked tests | `cd /tmp/bake/my-project && DATABASE_URL=postgres://postgres:postgres@localhost:5432/postgres uv run pytest` | 100% cov, all pass |
| Baked pre-commit | `cd /tmp/bake/my-project && git add -A && uv run pre-commit run --all-files` | exit 0 |
| Root pre-commit | (repo root) `uvx pre-commit run --all-files` | exit 0 |

Use the exact CI env-var set from `.github/scripts/deploy-check.sh` when a bare
`SECRET_KEY=x` is rejected by a prod-style guard (the command runs under
`DJANGO_ENV=ci`, so the insecure-key guard does not apply — a placeholder key
is fine).

## Scope

**In scope** (create unless noted):
- `{{cookiecutter.project_slug}}/src/apps/api/management/__init__.py` (create)
- `{{cookiecutter.project_slug}}/src/apps/api/management/commands/__init__.py` (create)
- `{{cookiecutter.project_slug}}/src/apps/api/management/commands/export_openapi_schema.py` (create)
- `{{cookiecutter.project_slug}}/tests/api/unit/export_openapi_schema_test.py` (create)
- `{{cookiecutter.project_slug}}/.github/workflows/openapi.yaml` (create — no Jinja; copied as-is)
- `.github/workflows/ci.yaml` (repo root) — no change required unless you choose
  to also gate it in the bake matrix (optional; see Step 5).
- `{{cookiecutter.project_slug}}/README.md` — one line under "What You Get".

**Out of scope**:
- Committing generated schema JSON into the template and adding a
  `git diff --exit-code` drift gate. This is a deliberate follow-up, not this
  plan — see Maintenance notes for why (it would require running Django inside
  the `post_gen_project.py` hook to seed a per-knob baseline).
- `src/apps/api/api.py` — do not change how the APIs are constructed.
- Any change to the Schemathesis contract test.

## Git workflow

- Work on `main`. Do NOT branch/commit/push/PR unless the operator says so.
  If committing: Conventional Commits, e.g.
  `feat: add export_openapi_schema management command`.

## Steps

### Step 1: Create the management command

Create the two `__init__.py` files (empty) and the command. The command should
accept `--api {internal,v1}` (default `v1`) and an optional `--output PATH`;
with no `--output` it writes to stdout. Deterministic output (sorted keys,
trailing newline) so diffs are stable:

```python
import json
from pathlib import Path
from typing import ClassVar

from django.core.management.base import BaseCommand, CommandParser

from apps.api.api import internal_api, v1_api


class Command(BaseCommand):
    help = "Export an API's OpenAPI schema as JSON."

    apis: ClassVar[dict[str, object]] = {"internal": internal_api, "v1": v1_api}

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("--api", choices=sorted(self.apis), default="v1")
        parser.add_argument("--output", default=None)

    def handle(self, *args: object, **options: object) -> None:
        api = self.apis[options["api"]]
        schema = json.dumps(dict(api.get_openapi_schema()), indent=2, sort_keys=True)

        if options["output"] is None:
            self.stdout.write(schema)

        else:
            Path(options["output"]).write_text(schema + "\n")
```

Adjust types/signature to satisfy `ty` and ruff `ALL` (the executor should run
the hooks and fix any lint precisely — e.g. `**options: object` indexing may
need a cast or a typed options read; follow whatever ruff/ty demand without
adding `# type: ignore` unless a marker already models the same pattern
elsewhere in the repo). Match `django-ninja`'s actual `get_openapi_schema()`
return type — confirm by reading the installed package
(`.venv/lib/python*/site-packages/ninja/openapi/schema.py`) if the `dict(...)`
wrapping is unnecessary or wrong.

**Verify**: run the "Run command (stdout)" command from the table →
`python -c "import json,sys; json.load(sys.stdin)"` on its output exits 0, and
the JSON has a top-level `"openapi"` key.

### Step 2: Test the command (required for 100% coverage)

Create `tests/api/unit/export_openapi_schema_test.py`. Model its structure on
an existing unit test (`tests/api/unit/api_test.py`). Cover both branches so
coverage stays at 100%:

- `test_export_openapi_schema_writes_valid_json_to_stdout_when_no_output` —
  `call_command("export_openapi_schema", "--api=internal", stdout=buf)`, parse
  `buf.getvalue()`, assert `schema["openapi"]` present and `"paths"` includes a
  probe route.
- `test_export_openapi_schema_writes_file_when_output_given` — pass
  `--output=<tmp_path/schema.json>` (pytest `tmp_path` fixture), assert the file
  exists, ends with a newline, and parses as JSON.
- If `use_example_api=yes`, optionally assert the v1 schema `paths` include a
  `/notes` route — but keep this test file present and passing for **both**
  knob states (do not reference notes unconditionally; guard with Jinja
  `{%- if cookiecutter.use_example_api == "yes" %}` if you add it).

Use `django.core.management.call_command` and an `io.StringIO` buffer. No DB is
needed, but keep `pytestmark = pytest.mark.django_db` only if the command
touches the ORM (it does not — omit the marker unless a test fails without it).

**Verify**:
`cd /tmp/bake/my-project && DATABASE_URL=postgres://postgres:postgres@localhost:5432/postgres uv run pytest`
→ all pass, coverage 100% (the new command lines are all covered).

### Step 3: Add the baked CI workflow that publishes the schema artifact

Create `{{cookiecutter.project_slug}}/.github/workflows/openapi.yaml` (plain
YAML — no Jinja, since this dir is copied unrendered). Model it on
**`migrations-check.yaml`** — it has the full setup chain to copy (checkout,
setup-python with `python-version-file: pyproject.toml`, setup-uv, then
`uv sync --group=ci --locked --no-default-groups`). Do NOT model the install
step on `dependency-audit.yaml`: that workflow has no `uv sync` step (it runs
`uv audit` directly). Steps:

1. Install ci deps.
2. Export both schemas to files:
   `uv run --group=ci --locked --no-default-groups manage.py export_openapi_schema --api=internal --output=openapi-internal.json`
   and the same for `--api=v1 --output=openapi-v1.json`.
   Provide the required env inline in the step (`DJANGO_ENV: ci`,
   `CACHE_URL: locmemcache://`, `SECRET_KEY`, `ALLOWED_HOSTS`, a parse-only
   `DATABASE_URL` — no Postgres service is needed because the command makes no
   DB connection; confirm this by running Step 1 with an unreachable DB host).
3. Upload both files via `actions/upload-artifact`. Pin to an **exact
   version** (`@vX.Y.Z`), matching the repo's convention — every action here
   is exact-pinned (`actions/checkout@v6.0.3`, `actions/setup-python@v6.2.0`,
   `astral-sh/setup-uv@v8.2.0`); never use a floating `@vX` / `@vX.x` ref.
   Use the latest release tag (check the upstream releases page; if you have
   no web access, note in your report that the pin needs confirming).

Match the `name:`, `on:` (pull_request + push to main), and `concurrency:`
blocks used by the other baked workflows exactly.

**Verify**: bake and run the BAKED pre-commit's workflow linters —
`cd /tmp/bake/my-project && git add -A && uv run pre-commit run actionlint
check-github-workflows --all-files` exits 0. (The repo-root pre-commit
`exclude`s the whole template dir, so root actionlint never sees this file —
do not rely on it.) Also confirm no Jinja crept into the file:
`grep -c "cookiecutter" "{{cookiecutter.project_slug}}/.github/workflows/openapi.yaml"` → 0.

### Step 4: Confirm the DB-independence claim

Run Step 1's command with a deliberately unreachable database host:
```
cd /tmp/bake/my-project
DJANGO_ENV=ci CACHE_URL=locmemcache:// SECRET_KEY=x ALLOWED_HOSTS=localhost \
  DATABASE_URL=postgres://u:p@127.0.0.1:1/none \
  uv run manage.py export_openapi_schema --api=v1
```
**Verify**: exits 0 with valid JSON (proving the CI workflow needs no Postgres
service). If it tries to connect and fails, STOP — the workflow in Step 3 must
then add a postgres service and this plan's env assumptions change.

### Step 5: (Optional) gate it in the template's own CI

Only if you want the template's `ci.yaml` `bake` job to exercise the command on
every variant: add a step after "Run migration checks" that runs the export for
both APIs (reusing the bake's postgres env is fine). Keep it minimal. This adds
no new *job* (still the `Bake ${{ matrix.case }}` check), so no branch-protection
change is required. Skip this step if unsure; the baked `openapi.yaml` already
proves the command works per bake in the baked project's own CI.

### Step 6: Document it

Add one bullet to `{{cookiecutter.project_slug}}/README.md` "What You Get":
e.g. "`manage.py export_openapi_schema` command and a CI job that publishes the
OpenAPI schema as a build artifact for client generation." Keep list ordering
consistent with neighbors.

**Verify**: repo-root `uvx pre-commit run markdownlint --all-files` exits 0.

## Test plan

- New unit test file `tests/api/unit/export_openapi_schema_test.py` (Step 2),
  covering stdout and `--output` branches → keeps coverage at 100%.
- Structural pattern: `tests/api/unit/api_test.py`.
- Full verification: baked `uv run pytest` (all pass, 100% cov) on a **default**
  bake and on a **`use_example_api=yes`** bake (to confirm the test file is
  valid in both knob states):
  `uvx cookiecutter . --no-input -o /tmp/bake-ex use_example_api=yes`.

## Done criteria

ALL must hold:

- [ ] `manage.py export_openapi_schema --api=v1` prints valid JSON containing an `"openapi"` key (default bake).
- [ ] `--output=<file>` writes valid JSON ending in a newline.
- [ ] The command exits 0 with an **unreachable** `DATABASE_URL` (Step 4).
- [ ] Baked `uv run pytest` passes at 100% coverage on default and `use_example_api=yes` bakes.
- [ ] `{{cookiecutter.project_slug}}/.github/workflows/openapi.yaml` exists, contains no `cookiecutter` string, and passes actionlint + check-github-workflows.
- [ ] Baked `git add -A && uv run pre-commit run --all-files` exits 0.
- [ ] Root `uvx pre-commit run --all-files` exits 0.
- [ ] README updated; no out-of-scope files modified (`git status`).
- [ ] `plans/README.md` status row updated.

## STOP conditions

Stop and report (do not improvise) if:

- `NinjaAPI.get_openapi_schema()` does not exist or returns something that is
  not JSON-serializable via the shown approach (the installed django-ninja
  version differs from expectations — read the package and report the real API).
- The command requires a live DB connection (Step 4 fails) — the CI workflow
  design changes.
- Achieving 100% coverage on the command would require contorting the code
  (e.g. an unreachable branch) — reconsider the command's shape and report.
- The `src/apps/api` code has drifted from the "Current state" excerpt.

## Maintenance notes

- **Deferred: committed schema + drift gate.** The higher-ceiling version
  commits `openapi/*.json` into each baked repo and adds a
  `export ... && git diff --exit-code` gate (mirroring the migration-drift
  check). It was deferred because seeding a correct per-knob baseline requires
  running Django inside `hooks/post_gen_project.py` (like the Dockerfile's
  throwaway-env `collectstatic`), which is a meaningfully larger and riskier
  change. Revisit if consumers want the schema tracked in git rather than as a
  CI artifact.
- The Schemathesis contract test already guards that the schema and runtime
  behavior stay consistent; this command does not duplicate that.
- Reviewer should confirm: no Jinja in the baked workflow file, the command has
  no hidden DB dependency, and coverage stays at 100% for **both**
  `use_example_api` states.
- If more `NinjaAPI` instances are added later, extend the command's `apis`
  mapping and the workflow's export steps.
