# Plan 016: Assert production settings values, not only import survival

> **Executor instructions**: Add assertions only for rendered branches that
> exist in each bake. Run all representative variants and update the index.
>
> **Drift check (run first)**: `rtk git diff --stat b367191..HEAD -- '{{cookiecutter.project_slug}}/src/config/settings/environments/prod.py' '{{cookiecutter.project_slug}}/tests/config/unit/prod_settings_test.py' '.github/workflows/ci.yaml'`

## Status

- **Priority**: P2
- **Effort**: M
- **Risk**: LOW
- **Depends on**: none
- **Category**: tests
- **Planned at**: commit `b367191`, 2026-07-10

## Why this matters

Production settings are omitted from coverage and subprocess tests emphasize
boot guards. S3 storage options, SMTP/Resend backend values, secure cookies,
proxy settings, and WhiteNoise mutation can drift while import still succeeds.
These values define deployment behavior and deserve direct assertions.

## Current state

- `pyproject.toml` intentionally omits `prod.py` from coverage.
- `prod_settings_test.py` already provides isolated subprocess imports and a
  base production environment; extend that pattern.
- Conditional branches include S3/local media, Resend/SMTP/none, proxy/no
  proxy, CORS, and Sentry.

## Commands you will need

| Purpose | Command | Expected |
|---|---|---|
| Focused | `rtk uv run pytest tests/config/unit/prod_settings_test.py -q` | pass |
| Deploy check | `rtk ./.github/scripts/deploy-check.sh` | exit 0 |
| Full | `rtk uv run pytest` | pass, coverage 100% |

## Scope

**In scope**:
- `{{cookiecutter.project_slug}}/tests/config/unit/prod_settings_test.py`
- `.github/workflows/ci.yaml` only if a representative bake is missing
- production settings code only if tests reveal a real defect (STOP first)

**Out of scope**:
- Removing the production coverage omission.
- Real S3, SMTP, Resend, or Sentry network calls.
- Changing production defaults to satisfy a mistaken test.

## Git workflow

Do not commit or push unless explicitly requested.

## Steps

### Step 1: Inventory rendered settings contracts

For each branch, list exact expected values from `prod.py` and its component
settings: storage backend/options, static backend, email backend/host/TLS,
CSRF/session cookie security, SSL redirect/proxy header, CORS requirement,
logging formatter, and Sentry initialization prerequisites.

**Verify**: inventory maps each assertion to an existing bake case.

### Step 2: Add subprocess value assertions

Extend the existing helper to serialize selected settings from a fresh process
without making external connections. Add alphabetized tests for S3, local
media, Resend, SMTP, no-email, proxy, no-proxy, static files, and secure-cookie
branches. Use fixed `.test` hostnames and faker values per repository rules.

**Verify**: focused tests pass in the matching bakes.

### Step 3: Ensure representative CI coverage

Map tests to default, smtp, minimal, no-proxy, and external-backing cases. Add
only the smallest missing bake needed; do not create a Cartesian matrix.

**Verify**: every conditional assertion is collected in at least one CI bake.

### Step 4: Run full checks

Run focused/full pytest and pre-commit for the representative bakes.

**Verify**: all pass at 100% coverage.

## Test plan

Assert exact settings dictionaries/tuples, not string presence in source. Mock
or disable SDK initialization only through environment selection already used
by tests.

## Done criteria

- [ ] S3/local, email-provider, proxy, static, and cookie values are asserted.
- [ ] Every conditional test is collected by a CI bake.
- [ ] No real external network call occurs.
- [ ] Full representative suites pass.

## STOP conditions

- A new assertion exposes a source defect; report it before expanding this
  test-only plan to production code.
- Importing a branch necessarily makes a real provider network call.

## Maintenance notes

When adding a production setting branch, add a direct value assertion and map
it to a named bake case.
