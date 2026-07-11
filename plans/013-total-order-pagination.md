# Plan 013: Give every notes pagination order a deterministic tiebreaker

> **Executor instructions**: Fix both default and client-selected ordering.
> Run all gates and update the index; do not land a default-only partial fix.
>
> **Drift check (run first)**: `rtk git diff --stat b367191..HEAD -- '{{cookiecutter.project_slug}}/src/apps/notes/' '{{cookiecutter.project_slug}}/tests/notes/'`

## Status

- **Priority**: P2
- **Effort**: M
- **Risk**: LOW
- **Depends on**: none
- **Category**: bug
- **Planned at**: commit `b367191`, 2026-07-10

## Why this matters

Limit/offset pagination requires a total ordering. Notes default to only
`-created_at`, and client-selected `created_at` or `title` ordering also has no
unique tiebreaker. Timestamp/title ties can therefore move rows across page
boundaries, causing skipped or duplicate results. This resource is the pattern
generated projects copy.

## Current state

- `models.py:19-23` sets `ordering = ("-created_at",)` and indexes
  `(owner, -created_at)`.
- `controllers.py:97` uses ninja-extra `Ordering` with `created_at` and `title`.
- Pinned `Ordering.get_ordering()` returns the validated client fields;
  `ordering_queryset()` passes them directly to `QuerySet.order_by`.
- The committed initial migration mirrors model ordering and must remain in
  lockstep.

## Commands you will need

| Purpose | Command | Expected |
|---|---|---|
| Bake | `rtk uvx cookiecutter . -o /tmp/plan-013 --no-input use_example_api=yes` | created |
| Focused | `rtk uv run pytest tests/notes -q` | pass |
| Migration | `rtk ./.github/scripts/migrations-check.sh` | no changes |
| Full | `rtk uv run pytest` | pass, coverage 100% |

## Scope

**In scope**:
- `{{cookiecutter.project_slug}}/src/apps/notes/models.py`
- `{{cookiecutter.project_slug}}/src/apps/notes/migrations/0001_initial.py`
- `{{cookiecutter.project_slug}}/src/apps/notes/controllers.py`
- notes unit/integration tests

**Out of scope**:
- Replacing offset pagination with cursor pagination.
- Adding trigram or title indexes.
- Changing response schemas.

## Git workflow

Do not commit or push unless explicitly requested.

## Steps

### Step 1: Add tied-row pagination tests

Create at least five notes for one user and force identical `created_at`
values with a queryset update. Fetch three pages and assert all IDs are unique
and complete. Repeat with explicit `?ordering=title` after forcing identical
titles, and with descending ordering. Add a direct assertion for the model
ordering contract.

**Verify**: contract assertions fail before implementation; endpoint tests may
be nondeterministic before the fix, so do not rely on a flaky failure alone.

### Step 2: Fix default ordering and migration state

Set model and initial migration ordering to
`("-created_at", "-id")`. UUIDv7 makes `-id` a deterministic unique
tiebreaker. Do not change the existing index without measured evidence.

**Verify**: migration check reports no generated changes.

### Step 3: Enforce a tiebreaker for explicit ordering

Add a resource-local `TotalOrdering(Ordering)` class in `controllers.py`.
Override the pinned `get_ordering(items, value)` signature, call `super()`, and
when a nonempty client ordering lacks `id`/`-id`, append `-id`. Use this class
in the decorator while keeping the public allowed fields unchanged.

Match the exact upstream return/input type annotations from
django-ninja-extra 0.31.5 so Ruff and Ty pass; do not use `Any` or a blanket
ignore.

**Verify**: explicit title/created_at tie tests pass.

### Step 4: Verify session and JWT example bakes

Run full pytest, migrations, schema drift, and pre-commit in session and JWT
example bakes.

**Verify**: all pass and OpenAPI output is unchanged.

## Test plan

Cover default, ascending explicit, descending explicit, already-requested `id`
if allowed internally, page disjointness, and user ownership isolation.

## Done criteria

- [ ] Default and explicit orders always end in a unique ID tiebreaker.
- [ ] Model and migration state agree.
- [ ] Tied-row page tests are deterministic and pass.
- [ ] Session/JWT schemas and suites pass.

## STOP conditions

- Upstream `Ordering` signature differs from the pinned 0.31.5 source.
- Appending a non-public `id` tiebreaker is rejected by upstream validation.
- Migration check proposes an unrelated schema change.

## Maintenance notes

Any new paginated exemplar must use a total order. Recheck the subclass when
ninja-extra changes ordering internals.
