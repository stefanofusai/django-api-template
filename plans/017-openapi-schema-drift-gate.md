# Plan 017: Commit the OpenAPI schemas and fail CI on contract drift

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving to the
> next step. If anything in the "STOP conditions" section occurs, stop and
> report — do not improvise. When done, update the status row for this plan
> in `plans/README.md` — unless a reviewer dispatched you and told you they
> maintain the index.
>
> **Drift check (run first)**:
> `git diff --stat 16a12b3..HEAD -- '{{cookiecutter.project_slug}}/.github/workflows/openapi-schema-export.yaml' '{{cookiecutter.project_slug}}/src/apps/notes/controllers.py' '{{cookiecutter.project_slug}}/src/apps/api/management/commands/export_openapi_schema.py' '{{cookiecutter.project_slug}}/tests/api/unit/export_openapi_schema_test.py' '{{cookiecutter.project_slug}}/README.md' hooks/post_gen_project.py README.md`
> If any in-scope file changed since this plan was written, compare the
> "Current state" excerpts against the live code before proceeding; on a
> mismatch, treat it as a STOP condition.

## Status

- **Priority**: P3
- **Effort**: M
- **Risk**: LOW-MED
- **Depends on**: none
- **Category**: dx / ci
- **Planned at**: commit `16a12b3`, 2026-07-09

This plan replaces the former 017 design spike (since removed from
`plans/`). The settled decision is **Option A**: the generated project commits its OpenAPI
schemas under `docs/openapi/` and CI fails a pull request whose committed
schemas are stale. No push-from-CI, no credentials; the workflow stays
Jinja-free. Client SDK generation stays a non-goal.

## Why this matters

The root README promises an "OpenAPI schema export command and schema
artifact workflow for client generation". Today the generated
`OpenAPI Schema Export` workflow exports `openapi-internal.json` and
`openapi-v1.json` on every PR/push and stops at `actions/upload-artifact`.
Consumers get a schema buried in per-run CI artifacts: no reviewable schema
diffs on PRs, no drift signal when an endpoint changes contract, no committed
source of truth for a client generator to track. The promise is one step
short of delivered.

This plan commits the two schemas into the generated repo and turns the
export workflow into a **drift gate**: it re-exports the schemas and
`git diff`s them against the committed copies, so a PR that changes the API
contract without regenerating the schema fails visibly and reviewers see the
contract change as a diff.

## Current state

This repo is a **cookiecutter template**. Files under
`{{cookiecutter.project_slug}}/` contain Jinja and cannot be run directly —
verification means baking a project and running its export there. Always
single-quote paths containing `{{cookiecutter.project_slug}}` in the shell.
`.github/workflows/*` inside the project directory is `_copy_without_render`
(pure YAML, NO Jinja allowed).

Empirical findings from a bake at `16a12b3` (see Test plan for the exact
commands), which drive every decision below:

- **Determinism**: the `internal` schema and the `v1` schema when
  `use_example_api=no` are byte-stable across runs. The `v1` schema when
  `use_example_api=yes` is **NOT** byte-stable: ninja-extra appends
  `uuid.uuid4().hex[:8]` to every controller operation id when its
  per-controller `use_unique_op_id` flag is left at its default `True`
  (`ninja_extra/controllers/base.py`, `_add_operation_from_route_function`):

  ```python
  route_function.route.route_params.operation_id = (
      f"{controller_name}_{route_function.route.view_func.__name__}"
  )
  if self.use_unique_op_id:
      route_function.route.route_params.operation_id += (
          f"_{uuid.uuid4().hex[:8]}"
      )
  ```

  Two export runs produce e.g. `notes_create_note_4fd19de6` then
  `notes_create_note_a15c1578`. A `git diff --exit-code` gate over the
  committed schema would fail spuriously on every run without a fix. **This
  is an example-API contract change, not a command change** (see the note in
  Step 1) — it is the load-bearing scope decision in this plan.

- **DB not needed**: the export runs with the workflow's mock
  `DATABASE_URL` (pointing at a Postgres that does not exist — there is no
  Postgres service in this workflow) and exits 0. Schema generation touches
  no database. Confirmed for both knob values.

- The export command
  (`{{cookiecutter.project_slug}}/src/apps/api/management/commands/export_openapi_schema.py`
  — note: `apps/api`, not `apps/core`) already serializes with
  `json.dumps(..., indent=2, sort_keys=True)` and appends a trailing
  newline, so key ordering and whitespace are stable. **No command change is
  required for determinism.** It does not create the output's parent
  directory — a missing `docs/openapi/` raises `FileNotFoundError`, so the
  workflow and runbook create it (Steps 2 and 4).

- `{{cookiecutter.project_slug}}/.github/workflows/openapi-schema-export.yaml`
  (rendered verbatim): single job `export-openapi-schemas`;
  `uv sync --group=ci --locked --no-default-groups`; export step with env
  `ALLOWED_HOSTS`, `CACHE_URL: locmemcache://`, mock `DATABASE_URL`,
  `DEFAULT_FROM_EMAIL`, `DJANGO_ENV: ci`, `SECRET_KEY`; then
  `actions/upload-artifact@v7.0.1` of the two root-level JSON files.
  `permissions: contents: read`; `persist-credentials: false` on checkout.

- `{{cookiecutter.project_slug}}/src/apps/api/api.py`: `v1_api` is
  constructed for **both** knob values — a `NinjaExtraAPI` with the
  `NotesController` registered when `use_example_api=yes`, a plain `NinjaAPI`
  with no routes (empty `paths`) when `use_example_api=no`. So both
  `openapi-internal.json` and `openapi-v1.json` are always exportable, and
  the committed-schema set is the **same two files for both knob values** (the
  `v1` file just has empty `paths` when the example API is off). The
  Jinja-free workflow therefore needs no knob awareness.

- `{{cookiecutter.project_slug}}/.gitignore` has `docs/_build/` but does not
  ignore `docs/openapi/`; there is no existing `docs/` directory in a bake.

- The generated `README.md` (around line 258) has the developer runbook line
  `Export OpenAPI schema files for client generation:` with a single
  `python manage.py export_openapi_schema --api=v1 --output=openapi-v1.json`.

- The root `README.md` feature list (around line 23) says "OpenAPI schema
  export command and schema artifact workflow for client generation".

- `hooks/post_gen_project.py` prints a "Next steps" block ending in
  `git add -A && git commit -m 'feat: initial project scaffold'`. The
  OpenAPI workflow is NOT in that hook's `REMOVED_PATHS`/`REMOVED_DIRS`, so it
  ships for every knob combination.

- Root `.github/workflows/ci.yaml` `bake` matrix bakes a project, runs
  `uv sync --locked`, `pytest`, migration checks, and `pre-commit run
  --all-files` — it never executes the generated project's GitHub Actions
  workflows. So the OpenAPI drift gate is exercised only in a generated
  repo's own CI, and **root ci.yaml needs no change**.

## Commands you will need

| Purpose | Command | Expected on success |
|---------|---------|---------------------|
| Bake (example API on) | `uvx cookiecutter . -o /tmp/verify-017 --no-input use_example_api=yes api_auth=jwt` | project at `/tmp/verify-017/my-project` |
| Bake (example API off) | `uvx cookiecutter . -o /tmp/verify-017-noapi --no-input use_example_api=no` | project at `/tmp/verify-017-noapi/my-project` |
| Install CI deps (in bake) | `uv sync --group=ci --locked --no-default-groups` | exit 0 |
| Export a schema (in bake) | `uv run --group=ci --locked --no-default-groups manage.py export_openapi_schema --api=v1 --output=docs/openapi/openapi-v1.json` (with the workflow env exported) | file written, exit 0 |
| Generated tests (in bake) | `uv run pytest -q` (needs the bake matrix's Postgres, or run only the DB-free export tests with `--no-cov`) | passing |
| Workflow lint (repo root) | `uvx pre-commit run actionlint --all-files` and `uvx pre-commit run check-github-workflows --all-files` and `uvx pre-commit run zizmor --all-files` | exit 0 |

The export step's env, copied verbatim from the workflow:

```shell
export ALLOWED_HOSTS=localhost CACHE_URL=locmemcache:// \
  DATABASE_URL=postgres://postgres:mock-postgres-password@localhost:5432/postgres \
  DEFAULT_FROM_EMAIL=noreply@example.com DJANGO_ENV=ci \
  SECRET_KEY=mock-secret-key-0123456789-abcdefghijklmnopqrstuvwxyz
```

## Scope

**In scope** (all inside the generated project except the two root files):

- `{{cookiecutter.project_slug}}/src/apps/notes/controllers.py` — add
  `use_unique_op_id=False` to the `NotesController` `@api_controller`
  decorator (determinism fix; example-API contract change).
- `{{cookiecutter.project_slug}}/tests/api/unit/export_openapi_schema_test.py`
  — add an operation-id regression test (guards the fix above).
- `{{cookiecutter.project_slug}}/.github/workflows/openapi-schema-export.yaml`
  — export into `docs/openapi/`, add the drift-check step, repoint the
  artifact upload. Pure YAML, no Jinja.
- `{{cookiecutter.project_slug}}/README.md` — rewrite the schema-export
  runbook line to describe committed schemas + the drift gate + the bootstrap
  command.
- `hooks/post_gen_project.py` — add the schema bootstrap to the "Next steps"
  printout so a fresh repo's first push is not red.
- `README.md` (root) — update the feature-list wording to match what ships.

**Out of scope** (do NOT touch):

- `src/apps/api/management/commands/export_openapi_schema.py` — already
  deterministic (`sort_keys=True`, `indent=2`); no change needed.
- Client SDK generation — remains a non-goal (Maintenance notes).
- The API surface itself beyond the one `use_unique_op_id=False` flag.
- Root `.github/workflows/ci.yaml` — the bake matrix does not run generated
  workflows; nothing to add.

## Git workflow

- Conventional commits, e.g. `feat: commit OpenAPI schemas and gate CI on
  contract drift` (or split: one `fix:` for the deterministic operation ids +
  test, one `ci:`/`docs:` for the workflow and runbook prose).
- Do NOT push unless instructed.

## Steps

### Step 1: Make the `v1` schema deterministic

In `{{cookiecutter.project_slug}}/src/apps/notes/controllers.py`, add
`use_unique_op_id=False` to the `NotesController` decorator:

```python
@api_controller(
    "/notes",
    auth={% if cookiecutter.api_auth == "jwt" %}jwt_auth{% else %}django_auth{% endif %},
    tags=["notes"],
{%- if cookiecutter.api_throttling == "basic" %}
    throttle=get_public_api_throttles(),
{%- endif %}
    use_unique_op_id=False,
)
```

(Add the line as the last keyword argument, after the existing conditional
`throttle=` block, so it renders correctly for every knob combination.)

**Why this is the fix, and why it is safe**: the random suffix is assigned
once, at controller registration (module import of `apps.api.api`), and
persisted on the route — it is *not* regenerated per export. Two export
*processes* therefore disagree, which is exactly what a committed-schema gate
cannot tolerate. Disabling the suffix yields stable, human-meaningful
operation ids (`notes_create_note`, `notes_list_notes`, …) — strictly better
for client generation. There is no collision risk: ninja-extra composes the
id as `{controller_name}_{view_func_name}`, and a single controller cannot
define two methods with the same name. This affects only `use_example_api=yes`
(the plain `NinjaAPI` schemas carry no controller operation ids).

**Verify** (in a `use_example_api=yes` bake, with the export env exported):
`uv run --group=ci --locked --no-default-groups manage.py export_openapi_schema --api=v1`
twice and `diff` the two outputs → identical; and the operation ids are the
bare `notes_*` names with no hex suffix.

### Step 2: Add the operation-id regression test

The double-export-and-diff proof from Step 1 works only across *processes*.
Inside a single pytest process the schema is imported once, so a
double-export-in-one-process test would pass even with the bug (false green).
Instead assert the exact operation ids. Append to
`{{cookiecutter.project_slug}}/tests/api/unit/export_openapi_schema_test.py`
(the file ships for both knobs, so guard the new test with Jinja — it is only
meaningful when the notes controller exists):

```python
{%- if cookiecutter.use_example_api == "yes" %}


def test_export_openapi_schema_uses_stable_operation_ids() -> None:
    stdout = StringIO()

    call_command("export_openapi_schema", "--api=v1", stdout=stdout)

    schema = json.loads(stdout.getvalue())
    operation_ids = {
        operation["operationId"]
        for path in schema["paths"].values()
        for operation in path.values()
    }
    assert operation_ids == {
        "notes_create_note",
        "notes_delete_note",
        "notes_get_note",
        "notes_list_notes",
        "notes_update_note",
    }
{%- endif %}
```

This needs no database (schema generation is DB-free) and fails if the
`use_unique_op_id=False` flag is ever dropped (the ids gain hex suffixes).

**Verify**: in a `use_example_api=yes` bake,
`uv run pytest tests/api/unit/export_openapi_schema_test.py --no-cov -q` →
all pass (including the new test); temporarily remove the Step 1 flag and
confirm this test FAILS, then restore it.

### Step 3: Turn the export workflow into a drift gate

Edit
`{{cookiecutter.project_slug}}/.github/workflows/openapi-schema-export.yaml`.
Change the export step to write into `docs/openapi/` (creating it first),
add a drift-check step, and repoint the artifact upload. Leave the job name,
env block values, checkout, Python/uv setup, and `uv sync` untouched:

```yaml
      - name: Export OpenAPI schemas
        env:
          ALLOWED_HOSTS: localhost
          CACHE_URL: locmemcache://
          DATABASE_URL: postgres://postgres:mock-postgres-password@localhost:5432/postgres
          DEFAULT_FROM_EMAIL: noreply@example.com
          DJANGO_ENV: ci
          SECRET_KEY: mock-secret-key-0123456789-abcdefghijklmnopqrstuvwxyz
        run: |
          mkdir -p docs/openapi
          uv run --group=ci --locked --no-default-groups manage.py export_openapi_schema --api=internal --output=docs/openapi/openapi-internal.json
          uv run --group=ci --locked --no-default-groups manage.py export_openapi_schema --api=v1 --output=docs/openapi/openapi-v1.json
      - name: Check for schema drift
        run: |
          git add --intent-to-add docs/openapi/
          if ! git diff --exit-code -- docs/openapi/; then
            echo "::error::Committed OpenAPI schemas under docs/openapi/ are stale. Regenerate them (see the README's API section) and commit the result."
            exit 1
          fi
      - name: Upload OpenAPI schemas
        uses: actions/upload-artifact@v7.0.1
        with:
          name: openapi-schemas
          path: docs/openapi/
```

The `git add --intent-to-add` before `git diff --exit-code` is load-bearing:
a plain `git diff` ignores untracked files, so a repo whose schemas were never
committed would pass the gate silently. Intent-to-add makes never-committed
schema files appear in the diff, so the gate also catches "you forgot to
bootstrap". `mkdir -p docs/openapi` keeps the export from dying with
`FileNotFoundError` if the directory was deleted, degrading to a clean drift
failure instead. No new workflow permissions are needed — `git add`/`git diff`
are local operations, so `contents: read` and `persist-credentials: false`
stay as-is.

**Verify** (repo root): `uvx pre-commit run actionlint --all-files`,
`uvx pre-commit run check-github-workflows --all-files`, and
`uvx pre-commit run zizmor --all-files` → exit 0. Then rehearse the gate in a
bake: export into `docs/openapi/`, `git add` + commit them, re-export
unchanged and run
`git add --intent-to-add docs/openapi/ && git diff --exit-code -- docs/openapi/`
→ exit 0; then edit a schema by hand and rerun → exit 1.

### Step 4: Rewrite the generated README runbook

In `{{cookiecutter.project_slug}}/README.md`, replace the current
`Export OpenAPI schema files for client generation:` line and its code block
with prose that explains the committed schemas, the gate, and the regenerate
command:

```markdown
The versioned (`v1`) and internal OpenAPI schemas are committed under
`docs/openapi/` so API contract changes surface as reviewable diffs, and the
`OpenAPI Schema Export` workflow fails any pull request whose committed
schemas are stale. Regenerate and commit them whenever you change the API, and
point your OpenAPI client generator at these files:

```shell
mkdir -p docs/openapi
uv run python manage.py export_openapi_schema --api=internal --output=docs/openapi/openapi-internal.json
uv run python manage.py export_openapi_schema --api=v1 --output=docs/openapi/openapi-v1.json
```
```

Both commands apply for every knob value (the `v1` file is an empty-`paths`
schema when the example API is off), so no Jinja conditional is needed here.
The bare `uv run python manage.py …` form works in a developer's environment
after `cp .env.example .env` (the dev overlay + `.env` supply `SECRET_KEY`,
`DATABASE_URL`, etc.) — verified; the export needs no database.

**Verify**: `uvx pre-commit run markdownlint --all-files` in the bake → exit 0;
and read the rendered section for both `use_example_api` values.

### Step 5: Bootstrap the schemas in the post-gen "Next steps"

A freshly baked repo has no `docs/openapi/` schemas (the post-gen hook cannot
run Django — no dependencies at bake time), so its **first** push would fail
the new gate on missing files. Prevent that by adding the bootstrap to the
"Next steps" printout in `hooks/post_gen_project.py`, before the initial
commit line and after `cp .env.example .env` (the export needs `.env` and the
synced venv):

```python
    print(
        "\nNext steps:\n"
        "  uv sync --locked\n"
        "  cp .env.example .env\n"
        "  uv run pre-commit install --install-hooks\n"
        "  mkdir -p docs/openapi\n"
        "  uv run python manage.py export_openapi_schema --api=internal --output=docs/openapi/openapi-internal.json\n"
        "  uv run python manage.py export_openapi_schema --api=v1 --output=docs/openapi/openapi-v1.json\n"
        "  git add -A && git commit -m 'feat: initial project scaffold'\n"
    )
```

This edits only the printed string (no logic), works for both knob values, and
mirrors the README runbook so the committed schemas exist before the first
commit.

**Chosen bootstrap mechanism, and the rejected alternative**: a documented
one-time command (here + the README) is the lightest mechanism that fits the
repo. A local `repo: local` pre-commit hook that re-exports and re-stages the
schemas was rejected: every hook in the generated `.pre-commit-config.yaml`
today is an upstream repo or otherwise venv-independent (ruff, ty, actionlint,
zizmor, …); a `manage.py`-invoking hook would need the synced project venv,
`DJANGO_ENV`, and the full mock-env set, cutting against the grain and
duplicating the CI gate that already enforces currency on every PR.

**Verify**: bake a fresh project and confirm the printed "Next steps" lists
the two export commands before the commit line; run them in the bake and
confirm `docs/openapi/openapi-internal.json` and `docs/openapi/openapi-v1.json`
appear.

### Step 6: Fix the root README wording

In the root `README.md` feature list, replace:

```markdown
- OpenAPI schema export command and schema artifact workflow for client
  generation
```

with wording that matches what ships:

```markdown
- OpenAPI schema export command with committed `docs/openapi/` schemas and a
  CI drift gate, ready for client generation
```

**Verify**: `uvx pre-commit run markdownlint --all-files` at the repo root →
exit 0.

## Test plan

- **Determinism, both knobs** (already run at `16a12b3`; re-run after Step 1):
  bake `use_example_api=yes` and `use_example_api=no`; in each,
  `uv sync --group=ci --locked --no-default-groups`, export `internal` and
  `v1` twice with the workflow env, and `diff` each pair. Expect all four
  pairs byte-identical after Step 1. (`use_example_api=no` `v1` has empty
  `paths` and is already stable; the fix is what stabilizes
  `use_example_api=yes` `v1`.)
- **DB-free**: the exports above succeed with the mock `DATABASE_URL` and no
  Postgres service — confirming the gate needs no database.
- **Regression test** (Step 2): passes with the fix, fails without it (remove
  the flag, rerun, restore).
- **Gate green/red** (Step 3): commit the schemas, re-export unchanged →
  `git diff --exit-code` exits 0; hand-edit a schema → exits 1; delete
  `docs/openapi/` and rerun the workflow's steps → `mkdir -p` recreates it and
  intent-to-add flags the now-untracked files (exit 1).
- **Lint**: actionlint, check-github-workflows, zizmor (workflow),
  markdownlint (both READMEs) all clean.
- **No behavior regression**: the generated `pytest` suite (bake matrix's
  Postgres) still passes with `use_unique_op_id=False` — no test asserts the
  old suffixed ids.

## Done criteria

- [ ] `use_example_api=yes` `v1` schema is byte-stable across two export
  processes; operation ids are the bare `notes_*` names
- [ ] New `test_export_openapi_schema_uses_stable_operation_ids` passes with
  the fix and fails without it
- [ ] The export workflow writes to `docs/openapi/`, runs the intent-to-add
  drift check, and uploads `docs/openapi/`; actionlint /
  check-github-workflows / zizmor pass
- [ ] Gate rehearsal: green on unchanged re-export, red on a hand-edited
  schema
- [ ] Generated README runbook and `hooks/post_gen_project.py` "Next steps"
  bootstrap the two schemas before the initial commit; markdownlint passes
- [ ] Root README feature-list wording updated
- [ ] The management command is unchanged
- [ ] Both knob bakes clean; `git status` at repo root clean apart from
  in-scope files
- [ ] `plans/README.md` status row updated

## STOP conditions

Stop and report back if:

- After adding `use_unique_op_id=False`, the `use_example_api=yes` `v1`
  export is still not byte-stable across two processes — there is a second
  source of non-determinism (record the diff; do not paper over it in the
  export command).
- The export command turns out to require a live database in some
  configuration (the mock-env run should not) — it changes the workflow's
  cost.
- Disabling the unique operation id triggers a ninja-extra duplicate-id error
  at import (would mean two controller methods share a name — re-check the
  controller before proceeding).
- `git diff --exit-code` behaves differently on the CI runner's git version
  than in local rehearsal (e.g. intent-to-add not catching untracked files) —
  the gate correctness depends on it.

## Maintenance notes

- Client SDK generation (e.g. a `use_typescript_client` knob) stays a
  non-goal; committed schemas are the handoff point for any downstream
  generator a user chooses to run.
- The committed schema set is knob-independent: both
  `docs/openapi/openapi-internal.json` and `docs/openapi/openapi-v1.json`
  ship for every knob combination (the `v1` file is an empty-`paths` schema
  when `use_example_api=no`). Because the post-gen hook does not create or
  remove these files, they are NOT part of `hooks/post_gen_project.py`'s
  removal lists and plan 013's removal-list guard does not apply to them. If a
  future change ever makes the schema set knob-dependent, add the files to the
  removal lists and coordinate with plan 013's existence guard.
- If a new controller is added to the `v1` API, give its `@api_controller` the
  same `use_unique_op_id=False` (or the schema regains non-deterministic ids
  and the drift gate flaps); the Step 2 regression test only covers the notes
  controller, so extend it alongside any new controller.
- **Coordinate with plan 021 (JWT replacement).** 021 removes plan 006's
  custom `TokensController` and registers `django-ninja-jwt` controllers for
  `use_example_api=yes api_auth=jwt` bakes. If 021 lands first, make the Step
  2 expected-id set and committed `openapi-v1.json` include the stable
  `/token/*` JWT operation ids instead of any `tokens_*` ids. If the library
  emits nondeterministic operation ids, stop and resolve that before landing a
  committed-schema drift gate.
- The root ci.yaml bake matrix does not execute generated workflows, so the
  drift gate is not exercised in this template's own CI — its verification is
  the bake rehearsal in this plan and, thereafter, generated repos' own CI.
