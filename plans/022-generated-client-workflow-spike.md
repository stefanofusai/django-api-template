# Plan 022: Design one opt-in generated API client workflow

> **Executor instructions**: Produce a design/prototype verdict, not a
> multi-language client platform. Update the index when complete.
>
> **Drift check (run first)**: `rtk git diff --stat b367191..HEAD -- 'README.md' '{{cookiecutter.project_slug}}/README.md' '{{cookiecutter.project_slug}}/.github/workflows/openapi-schema-export.yaml' '{{cookiecutter.project_slug}}/docs/openapi/'`

## Status

- **Priority**: P3
- **Effort**: M
- **Risk**: MED
- **Depends on**: none
- **Category**: direction
- **Planned at**: commit `b367191`, 2026-07-10

## Why this matters

The template commits and drift-checks OpenAPI schemas and calls them “ready
for client generation,” but every downstream project must choose a generator,
configure deterministic output, and wire releases itself. One opt-in reference
workflow could make the promise concrete without making client tooling a
mandatory template dependency.

## Current state

- Schemas are exported for internal and v1 APIs.
- Schema drift is already a CI gate.
- No client language, generator, package registry, or compatibility policy is
  selected.

## Commands you will need

| Purpose | Command | Expected |
|---|---|---|
| Bake schema project | `rtk uvx cookiecutter . -o /tmp/plan-022 --no-input use_example_api=yes api_auth=jwt` | created |
| Export schema | `rtk uv run python manage.py export_openapi_schema --api=v1 --output=/tmp/plan-022-schema.json` | exit 0 |
| Compare output | `rtk git diff --no-index --exit-code /tmp/client-a /tmp/client-b` | exit 0 |

## Scope

**In scope**:
- disposable prototypes for one client ecosystem
- `docs/decisions/generated-client-workflow.md` (create)
- an optional workflow/recipe only if approved after prototype

**Out of scope**:
- Supporting multiple languages in the first iteration.
- Committing generated clients to the template by default.
- Generating a client for internal probes unless justified.

## Git workflow

Keep prototypes under temporary directories. Do not commit generated client
output or a workflow unless the maintainer accepts the recorded verdict.

## Steps

### Step 1: Select a reference consumer

Use repository/user evidence to choose one ecosystem; absent evidence,
prototype TypeScript because OpenAPI client generation most commonly serves a
separate browser/frontend consumer. Compare two maintained generators on
determinism, nullable/UUID/date handling, auth support, runtime dependency,
and versioning.

**Verify**: decision matrix names exact versions and licenses.

### Step 2: Prototype deterministically

Generate from committed `openapi-v1.json` twice in clean temporary directories
and require byte-identical output. Exercise notes list/create/auth types in a
small compile-only consumer. Do not write generated output into source yet.

**Verify**: two generation hashes match and sample consumer compiles.

### Step 3: Define opt-in workflow and compatibility policy

Specify trigger order after schema drift, artifact/package destination,
semantic version source, breaking-change behavior, credentials, cache, and
whether output is an artifact, branch, or registry package. Default to manual
workflow dispatch until demand is proven.

**Verify**: threat model covers untrusted schema changes and package-write
permissions.

### Step 4: Record verdict

Write the decision document with adopt/defer verdict, exact prototype commands,
open questions, maintenance owner, and revisit trigger. Implement an optional
workflow only if the maintainer approves the selected ecosystem.

## Test plan

Compile a minimal consumer against generated auth, UUID/date, pagination, and
nullable types. Generate twice from identical schema and compare every byte;
run the prototype workflow without package-write permission first.

## Done criteria

- [ ] One generator/ecosystem has reproducible evidence.
- [ ] Auth, UUID, date, pagination, and nullable types compile correctly.
- [ ] Opt-in release/permission model is specified.
- [ ] Adopt/defer verdict is documented.

## STOP conditions

- No consumer ecosystem is preferred and the maintainer declines TypeScript.
- Generator output is nondeterministic or requires an unpinned remote service.
- Workflow needs broad package-write permissions on pull requests.

## Maintenance notes

Revisit when a real downstream client appears or OpenAPI compatibility checks
are added.
