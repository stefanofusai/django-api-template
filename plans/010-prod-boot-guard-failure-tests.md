# Plan 010: Add failure-path tests for the coverage-omitted prod boot guards

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving to the
> next step. If anything in the "STOP conditions" section occurs, stop and
> report — do not improvise. When done, update the status row for this plan
> in `plans/README.md` — unless a reviewer dispatched you and told you they
> maintain the index.
>
> **Drift check (run first)**:
> `git diff --stat 75c4dce..HEAD -- '{{cookiecutter.project_slug}}/tests/config/unit/prod_settings_test.py' '{{cookiecutter.project_slug}}/src/config/settings/environments/prod.py'`
> If any in-scope file changed since this plan was written, compare the
> "Current state" excerpts against the live code before proceeding; on a
> mismatch, treat it as a STOP condition.

## Status

- **Priority**: P2
- **Effort**: S
- **Risk**: LOW
- **Depends on**: 009 (soft — plan 009 also edits
  `{{cookiecutter.project_slug}}/tests/config/unit/prod_settings_test.py`,
  including `_base_prod_env` hostname literals; execute after it or
  coordinate to avoid merge conflicts)
- **Category**: tests
- **Planned at**: commit `75c4dce`, 2026-07-08

## Why this matters

The generated project's production settings contain three security boot
guards: reject an insecure `django-insecure-` SECRET_KEY, reject the default
(slug-derived) database password, and reject the default Redis password. They
are the last line of defense against booting production with scaffold
credentials. `prod.py` is listed in `[tool.coverage.run] omit` in the
generated `pyproject.toml`, so the 100% coverage gate never sees these
branches — and no test exercises them. A refactor that inverts a condition or
breaks the comparison would ship silently. Three small subprocess tests close
that hole.

## Current state

This repo is a **cookiecutter template**. Files under
`{{cookiecutter.project_slug}}/` contain Jinja and cannot run directly —
verification means baking a project and running its suite there. Always
single-quote paths containing `{{cookiecutter.project_slug}}` in shell
commands.

Relevant files:

- `{{cookiecutter.project_slug}}/src/config/settings/environments/prod.py` —
  the guards (template source; note the Jinja knob gates):

```python
# prod.py:13-15 (unconditional)
if SECRET_KEY.startswith("django-insecure-"):  # noqa: F821  # ty: ignore[unresolved-reference]
    msg = "SECRET_KEY must be replaced with a securely generated value in production."
    raise ImproperlyConfigured(msg)

# prod.py:23-25 (unconditional)
if DATABASES["default"].get("PASSWORD") == "{{ cookiecutter.project_slug.replace('-', '_') }}":  # noqa: F821  # ty: ignore[unresolved-reference]
    msg = "The default database password must be replaced with a securely generated value in production."
    raise ImproperlyConfigured(msg)

# prod.py:32-36 (inside {%- if cookiecutter.redis == "compose" %})
if env("REDIS_PASSWORD") == "{{ cookiecutter.project_slug.replace('-', '_') }}":
    msg = "The default Redis password must be replaced with a securely generated value in production."
    raise ImproperlyConfigured(msg)
```

Ordering fact you rely on: the default-password guards above run BEFORE the
password-*match* guards that follow them in the file (`prod.py:28`,
`prod.py:38`), so overriding only the password env var deterministically
triggers the default-password message, not the mismatch message.

- `{{cookiecutter.project_slug}}/tests/config/unit/prod_settings_test.py` —
  the test file to extend. It already has the exact pattern to copy
  (subprocess import of `config.settings` with env overrides):

```python
# prod_settings_test.py:33-42 — the exemplar to model all three new tests on
def test_prod_settings_reject_example_allowed_host_when_example_domain_is_configured(
    faker: Faker,
) -> None:
    result = _import_prod_settings(
        faker,
        {"ALLOWED_HOSTS": "localhost,127.0.0.1,example.com"},
    )

    assert result.returncode != 0
    assert "ALLOWED_HOSTS must not contain example.com in production." in result.stderr
```

The helper `_import_prod_settings(faker, overrides)` (lines 134-147) merges
`_base_prod_env(faker)` with `overrides`, sets `PYTHONPATH=src`, and runs
`python -c "import config.settings"` in a subprocess, returning the
`CompletedProcess`. `_base_prod_env` sets `DJANGO_ENV=prod` and healthy
values for everything, including a random `POSTGRES_PASSWORD`/
`REDIS_PASSWORD` and a `DATABASE_URL` whose password matches
`POSTGRES_PASSWORD`.

Conventions: existing knob-gated tests in this file are wrapped in Jinja
blocks like `{% if cookiecutter.redis == "compose" -%} ... {% endif -%}`
with the closing tag after two blank lines — copy that shape exactly from
the surrounding tests. Test names follow
`test_prod_settings_reject_<what>_when_<condition>`.

## Commands you will need

| Purpose | Command | Expected on success |
|---------|---------|---------------------|
| Bake default | `uvx cookiecutter . -o /tmp/verify-009 --no-input` | exit 0, project at /tmp/verify-009/my-project |
| Bake redis-external | `uvx cookiecutter . -o /tmp/verify-009-ext --no-input postgres=external redis=external use_traefik=no` | exit 0 |
| Install (in bake) | `uv sync --locked` | exit 0 |
| Targeted tests (no DB needed — these are subprocess tests) | `uv run pytest tests/config/unit/prod_settings_test.py --no-cov -p no:randomly` | all pass |
| Full suite (needs Postgres) | `cp .env.example .env && docker compose -f .docker/compose/dev.yaml --env-file=.env up -d --wait postgres && uv run pytest` | all pass, coverage 100% |
| Lint (in bake) | `git add -A && uv run pre-commit run --all-files` | exit 0 |

## Scope

**In scope** (the only file you should modify):

- `{{cookiecutter.project_slug}}/tests/config/unit/prod_settings_test.py`

**Out of scope** (do NOT touch):

- `{{cookiecutter.project_slug}}/src/config/settings/environments/prod.py` —
  the guards themselves are correct; this plan only adds tests.
- The coverage `omit` list in `{{cookiecutter.project_slug}}/pyproject.toml` —
  `prod.py` stays omitted (importing prod settings in-process would break the
  test run; the subprocess pattern exists precisely for this).

## Git workflow

- Branch off `main` (or commit directly if the operator's workflow is
  trunk-based — match how recent commits landed; `git log` shows direct
  commits to main).
- Commit message style: conventional commits, e.g.
  `test: cover the prod boot guards' failure paths`.
- Do NOT push unless instructed.

## Steps

### Step 1: Add the SECRET_KEY guard test (unconditional)

In `{{cookiecutter.project_slug}}/tests/config/unit/prod_settings_test.py`,
after `test_prod_settings_reject_example_allowed_host_when_example_domain_is_configured`,
add:

```python
def test_prod_settings_reject_insecure_secret_key_when_scaffold_value_is_kept(
    faker: Faker,
) -> None:
    result = _import_prod_settings(
        faker,
        {"SECRET_KEY": "django-insecure-mock-secret-key"},
    )

    assert result.returncode != 0
    assert (
        "SECRET_KEY must be replaced with a securely generated value in production."
        in result.stderr
    )
```

**Verify**: file compiles as a template — proceed to step 4's bake; no
per-step bake needed yet.

### Step 2: Add the default database password guard test (unconditional)

Add (note: this is a Jinja-templated test file — write the
`{{ cookiecutter.project_slug.replace('-', '_') }}` expressions literally;
they render to e.g. `my_project` at bake time):

```python
def test_prod_settings_reject_default_database_password_when_scaffold_value_is_kept(
    faker: Faker,
) -> None:
    result = _import_prod_settings(
        faker,
        {
            "DATABASE_URL": (
                "postgres://{{ cookiecutter.project_slug.replace('-', '_') }}"
                ":{{ cookiecutter.project_slug.replace('-', '_') }}"
                "@postgres:5432/{{ cookiecutter.project_slug.replace('-', '_') }}"
            ),
        },
    )

    assert result.returncode != 0
    assert (
        "The default database password must be replaced with a securely "
        "generated value in production." in result.stderr
    )
```

The message string must match `prod.py:24` exactly — check the live file for
the exact wording and line-wrap the assertion however ruff-format requires.

### Step 3: Add the default Redis password guard test (redis == "compose" only)

Add, wrapped in the same Jinja gate style as the existing
`{% if cookiecutter.redis == "compose" -%}` block (place it inside or
adjacent to that existing block, matching its whitespace-control style
exactly):

```python
def test_prod_settings_reject_default_redis_password_when_scaffold_value_is_kept(
    faker: Faker,
) -> None:
    result = _import_prod_settings(
        faker,
        {"REDIS_PASSWORD": "{{ cookiecutter.project_slug.replace('-', '_') }}"},
    )

    assert result.returncode != 0
    assert (
        "The default Redis password must be replaced with a securely "
        "generated value in production." in result.stderr
    )
```

(The base env's `CACHE_URL` still carries the random password, but the
default-password guard at `prod.py:34` raises before the CACHE_URL match
guard at `prod.py:38`, so the asserted message is deterministic.)

### Step 4: Bake and run the targeted tests

```shell
uvx cookiecutter . -o /tmp/verify-009 --no-input
cd /tmp/verify-009/my-project
uv sync --locked
uv run pytest tests/config/unit/prod_settings_test.py --no-cov
```

**Verify**: all tests pass, including the 3 new ones.

### Step 5: Verify the redis=external variant renders and passes

```shell
uvx cookiecutter . -o /tmp/verify-009-ext --no-input postgres=external redis=external use_traefik=no
cd /tmp/verify-009-ext/my-project
uv sync --locked
uv run pytest tests/config/unit/prod_settings_test.py --no-cov
```

**Verify**: passes; the Redis test from step 3 must be ABSENT in this bake
(`grep -c reject_default_redis_password tests/config/unit/prod_settings_test.py`
→ `0`).

### Step 6: Full-gate check on the default bake

In `/tmp/verify-009/my-project`:

```shell
cp .env.example .env
docker compose -f .docker/compose/dev.yaml --env-file=.env up -d --wait postgres
uv run pytest
git init -q && git add -A
uv run pre-commit run --all-files
docker compose -f .docker/compose/dev.yaml --env-file=.env down -v
```

**Verify**: pytest exits 0 with coverage 100%; pre-commit exits 0 (this
catches ruff-format/I001 issues in the templated test file — the bake matrix
runs exactly this). If Docker is unavailable, report that the full-suite
check was skipped and why.

## Test plan

The plan IS the tests. Cases covered: insecure SECRET_KEY prefix (new),
default DB password (new), default Redis password (new, redis=compose only).
Pattern: `test_prod_settings_reject_example_allowed_host_when_example_domain_is_configured`.

## Done criteria

- [ ] 3 new tests exist in the template file, Redis one Jinja-gated on
  `redis == "compose"`
- [ ] Step 4 targeted run passes on the default bake
- [ ] Step 5 confirms the redis=external bake renders without the Redis test
  and passes
- [ ] Step 6 full suite + pre-commit pass on the default bake (or Docker
  unavailability reported)
- [ ] `git status` shows only the one in-scope file modified
- [ ] `plans/README.md` status row updated

## STOP conditions

Stop and report back (do not improvise) if:

- The guard messages in the live `prod.py` differ from the excerpts (the
  assertions would be wrong — re-sync them, and if the guards themselves
  moved or changed semantics, stop).
- Step 4 fails because the subprocess import needs env vars not provided by
  `_base_prod_env` (would mean settings drifted since 75c4dce).
- The default-password guard turns out to fire on the base env itself
  (would mean `_base_prod_env` uses the slug-derived password — it doesn't
  today; it uses `faker.bothify` values).

## Maintenance notes

- If a fourth boot guard is ever added to `prod.py`, add its failure-path
  test here in the same pattern — the coverage gate will NOT remind you,
  because `prod.py` is coverage-omitted.
- Reviewer should scrutinize: exact message strings vs `prod.py`, and the
  Jinja gate placement for the Redis test (must match the existing block's
  whitespace-control style or the bake matrix's format check fails).
