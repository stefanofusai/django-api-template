# Plan 009: Standardize placeholder hostnames — `.test` for machine-consumed values, `example.com` for docs — and record the rule in AGENTS.md

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving to the
> next step. If anything in the "STOP conditions" section occurs, stop and
> report — do not improvise. When done, update the status row for this plan
> in `plans/README.md` — unless a reviewer dispatched you and told you they
> maintain the index.
>
> **Drift check (run first)**:
> `git diff --stat 75c4dce..HEAD -- '{{cookiecutter.project_slug}}/.docker/Dockerfile' '{{cookiecutter.project_slug}}/.github/scripts/' '{{cookiecutter.project_slug}}/.github/workflows/openapi-schema-export.yaml' '{{cookiecutter.project_slug}}/pyproject.toml' '{{cookiecutter.project_slug}}/tests/api/integration/cors_test.py' '{{cookiecutter.project_slug}}/tests/config/unit/prod_settings_test.py' '{{cookiecutter.project_slug}}/tests/factories.py' '{{cookiecutter.project_slug}}/AGENTS.md' AGENTS.md .github/workflows/ci.yaml`
> If any in-scope file changed since this plan was written, re-locate the
> literals by grep (`grep -rn 'example\.com'`) before editing; if a literal
> no longer exists, treat it as a STOP condition.

## Status

- **Priority**: P3
- **Effort**: S
- **Risk**: LOW
- **Depends on**: 004 (soft — both edit
  `{{cookiecutter.project_slug}}/pyproject.toml` AND
  `{{cookiecutter.project_slug}}/AGENTS.md`; execute after it or coordinate
  to avoid merge conflicts)
- **Category**: dx / tech-debt
- **Planned at**: commit `75c4dce`, 2026-07-08

## Why this matters

The mock-env standardization (old plan 022, commit `6a0372f`) fixed mock
*values* (`mock-<var>` literals) but explicitly scoped hostname placeholders
out. The residue: machine-consumed throwaway hostnames are split between
`*.example.test` and `*.example.com`, inconsistently even within single files
(`docker-smoke.sh` uses `api.example.test` for ALLOWED_HOSTS but
`smtp.example.com` for EMAIL_HOST; `prod_settings_test.py` uses `.test`
everywhere except its Sentry DSN). The rule this plan enforces, decided by
the maintainer on 2026-07-08:

- **`example.com`** — only for values a human reads and replaces:
  cookiecutter defaults, README prose, `.env.example` comments, error
  messages, and the `prod.py` boot sentinel.
- **`*.example.test` / `example.test`** — every machine-consumed placeholder
  in tests, CI scripts, workflows, and Dockerfile build env.

Beyond consistency, `.test` is reserved at the DNS level (RFC 6761) and can
never resolve, while `example.com` is a live IANA-operated host — so a
misconfigured test or build step that actually attempts an SMTP connection,
CORS fetch, or Sentry flush fails instantly and locally instead of doing real
DNS. Same defense-in-depth logic as the `mock-<var>` literals.

## Current state

This repo is a **cookiecutter template**; files under
`{{cookiecutter.project_slug}}/` may contain Jinja — the edits below are pure
literal string replacements and add no Jinja. Always single-quote
`{{cookiecutter.project_slug}}` paths in shell commands.
`.github/workflows/*` inside the project dir is `_copy_without_render`
(plain YAML — fine to edit, never add Jinja there).

Every `example.com` occurrence to CHANGE to the `.test` equivalent
(same subdomain, TLD swap), verified by grep at `75c4dce`:

1. `{{cookiecutter.project_slug}}/.docker/Dockerfile`
   - `:48` `DEFAULT_FROM_EMAIL=noreply@example.com \`
   - `:52` `EMAIL_HOST=smtp.example.com \`
   - `:65` `SENTRY_DSN=https://mock-sentry-key@sentry.example.com/1 \`
2. `{{cookiecutter.project_slug}}/.github/scripts/deploy-check.sh`
   - `:18`, `:47` `DEFAULT_FROM_EMAIL=noreply@example.com \`
   - `:22`, `:51` `EMAIL_HOST=smtp.example.com \`
   - `:31`, `:60` `SENTRY_DSN=https://mock-sentry-key@sentry.example.com/1 \`
3. `{{cookiecutter.project_slug}}/.github/scripts/docker-smoke.sh`
   - `:52` `replace_env EMAIL_HOST "smtp.example.com"`
   - `:71` `replace_env SENTRY_DSN "https://mock-sentry-key@sentry.example.com/1"`
   - (`:36` ALLOWED_HOSTS already uses `api.example.test` — the target style)
4. `{{cookiecutter.project_slug}}/.github/scripts/migrations-check.sh`
   - `:10`, `:24` `CORS_ALLOWED_ORIGINS=https://app.example.com \`
   - `:14`, `:28` `DEFAULT_FROM_EMAIL=noreply@example.com \`
5. `{{cookiecutter.project_slug}}/.github/workflows/openapi-schema-export.yaml`
   - `:34` `DEFAULT_FROM_EMAIL: noreply@example.com`
6. `{{cookiecutter.project_slug}}/pyproject.toml` (`[tool.pytest.ini_options] env`)
   - `:150` `"CORS_ALLOWED_ORIGINS=https://app.example.com",`
   - Also (~`:141`): `"DEFAULT_FROM_EMAIL=noreply@{{ cookiecutter.domain_name }}",`
     → replace with the fixed literal `"DEFAULT_FROM_EMAIL=noreply@example.test",`
     (maintainer decision: test env values must not vary with the docs-default
     knob; `tests/core/unit/tasks_test.py:55` asserts against
     `settings.DEFAULT_FROM_EMAIL`, not a hardcoded domain, so this is safe).
7. `{{cookiecutter.project_slug}}/tests/api/integration/cors_test.py`
   - `:4`, `:8`, `:11`, `:14`, `:26`, `:34`, `:38` `https://app.example.com`
   - `:20` `https://evil.example.com`
   (all inside `@override_settings`/headers/asserts — change every
   occurrence; the test is self-consistent, so a partial change fails it)
8. `{{cookiecutter.project_slug}}/tests/config/unit/prod_settings_test.py`
   - `:130` `"SENTRY_DSN": f"https://{sentry_key}@sentry.example.com/1",`
   (the rest of `_base_prod_env` already uses `.test` — the target style)
9. `{{cookiecutter.project_slug}}/tests/factories.py`
   - `:11` `email = factory.Sequence(lambda n: f"user-{n}@example.com")`
10. Root `.github/workflows/ci.yaml`
    - `:272`, `:290` `SENTRY_DSN=https://mock-sentry-key@sentry.example.com/1`
    (`:263`, `:280`, `:299` ALLOWED_HOSTS already use `api.example.test`)

Occurrences to KEEP (`example.com` is correct there — touching any of these
is out of scope): `cookiecutter.json` (`domain_name`, `author_email`
defaults), root `README.md`, `{{cookiecutter.project_slug}}/README.md`,
`{{cookiecutter.project_slug}}/.env.example` comments,
`hooks/pre_gen_project.py:53` error message,
`src/config/settings/environments/prod.py:9-10` boot sentinel,
`tests/config/unit/prod_settings_test.py:38,42` (the sentinel's own test),
and everything under `{{cookiecutter.project_slug}}/.agents/` (vendored
reference docs).

Verified constraint: root `scripts/check_dockerfile_prod_env.py` contains no
hostname literals, so the Dockerfile edit has no invariant-script coupling.

**Where the rule gets recorded (Step 2).** The generated
`{{cookiecutter.project_slug}}/AGENTS.md` already carries the sibling
convention from the mock-env standardization, a bullet at ~lines 113-119
(anchor by CONTENT, not line number — plan 004 item F deletes two rtk lines
above it):

```markdown
- Mock env values (CI workflows, CI scripts, the Dockerfile's build-time
  collectstatic env, pytest env) use fixed `mock-<variable-name>` literals,
  ...
```

The hostname rule becomes the bullet directly after it. The ROOT `AGENTS.md`
has no mock-values bullet; its "## Template Maintenance" section (bullets
like "Keep operational constants fixed...", "Add environment variables only
for secrets...") is where template-editing rules live — the root version of
the bullet goes there, near the env-var bullets.

## Commands you will need

| Purpose | Command | Expected on success |
|---------|---------|---------------------|
| Locate all sites | `grep -rn 'example\.com' '{{cookiecutter.project_slug}}' .github/workflows/ci.yaml \| grep -v '/.agents/'` | the lists above |
| Bake (cors, full) | `uvx cookiecutter . -o /tmp/verify-009/cors --no-input use_example_api=yes api_auth=jwt api_throttling=basic use_cors=yes use_csp=yes` | project generated |
| Bake (smtp) | `uvx cookiecutter . -o /tmp/verify-009/smtp --no-input email_provider=smtp` | project generated |
| Suite (in bake, needs Docker) | `cp .env.example .env && docker compose -f .docker/compose/dev.yaml --env-file=.env up -d --wait postgres && uv sync --locked && uv run pytest` | all pass, 100% coverage |
| Lint (in bake) | `uvx ruff@0.15.16 format --check . && uvx ruff@0.15.16 check .` | exit 0 |
| Baked hooks (in bake, after `git add -A`) | `uv run pre-commit run shellcheck --all-files && uv run pre-commit run actionlint --all-files` | pass |
| Root checks | `uvx pre-commit run --all-files` | all hooks pass |

## Scope

**In scope** (the only files you should modify — literal TLD/value swaps
only, exactly the sites listed in Current state):
- `{{cookiecutter.project_slug}}/.docker/Dockerfile`
- `{{cookiecutter.project_slug}}/.github/scripts/deploy-check.sh`
- `{{cookiecutter.project_slug}}/.github/scripts/docker-smoke.sh`
- `{{cookiecutter.project_slug}}/.github/scripts/migrations-check.sh`
- `{{cookiecutter.project_slug}}/.github/workflows/openapi-schema-export.yaml`
- `{{cookiecutter.project_slug}}/pyproject.toml`
- `{{cookiecutter.project_slug}}/tests/api/integration/cors_test.py`
- `{{cookiecutter.project_slug}}/tests/config/unit/prod_settings_test.py`
- `{{cookiecutter.project_slug}}/tests/factories.py`
- `{{cookiecutter.project_slug}}/AGENTS.md` (Step 2 — one new bullet only)
- `AGENTS.md` (root, Step 2 — one new bullet only)
- `.github/workflows/ci.yaml` (root — the two SENTRY_DSN lines only)

**Out of scope** (do NOT touch):
- Every KEEP site listed in Current state.
- `localhost`/`127.0.0.1` values — real loopback, not placeholders.
- `postgres`/`redis` compose hostnames — real service names.
- Any `mock-<var>` value literal — already standardized (old plan 022).

## Git workflow

- Branch: `advisor/009-standardize-placeholder-hostnames`
- Two commits, e.g.
  `ci: standardize machine-consumed placeholder hostnames on example.test`
  and `docs: record the placeholder hostname rule in AGENTS.md`.
- Do NOT push or open a PR unless the operator instructed it.

## Steps

### Step 1: Apply the swaps

For every CHANGE site in Current state, replace the `example.com` hostname
with the same-subdomain `example.test` equivalent (`noreply@example.test`,
`smtp.example.test`, `sentry.example.test`, `app.example.test`,
`evil.example.test`, `user-{n}@example.test`), and swap pyproject's
DEFAULT_FROM_EMAIL knob-derived value for the fixed literal (site 6).

**Verify** (the authoritative sweep):
```
grep -rn 'example\.com' '{{cookiecutter.project_slug}}' .github/workflows/ci.yaml | grep -v '/.agents/'
```
→ ONLY these remain: `.env.example` comments (3 lines), both `README.md`s,
`cookiecutter.json` (root files aren't in this grep — check them separately
if unsure), `src/config/settings/environments/prod.py:9-10`,
`tests/config/unit/prod_settings_test.py:38,42`. Nothing under `.docker/`,
`.github/`, `pyproject.toml`, `tests/` (except prod_settings_test 38/42), or
`factories.py`.

### Step 2: Record the rule in both AGENTS.md files

In `{{cookiecutter.project_slug}}/AGENTS.md`, add directly AFTER the
"Mock env values ..." bullet (see Current state for the anchor):

```markdown
- Placeholder hostnames follow a two-tier rule: `example.com` appears only in
  human-facing documentation (README prose, `.env.example` comments) and the
  production `ALLOWED_HOSTS` boot sentinel; machine-consumed placeholders in
  tests, CI scripts, workflows, and the Docker build env use reserved `.test`
  hostnames such as `smtp.example.test`, which can never resolve publicly.
```

In the root `AGENTS.md`, add to the "## Template Maintenance" section, next
to the environment-variable bullets:

```markdown
- Use `example.com` placeholders only in human-facing documentation and
  cookiecutter defaults; machine-consumed placeholders in template tests, CI,
  and the Docker build env use `.test` hostnames such as
  `sentry.example.test`. The production boot sentinel deliberately checks for
  `example.com` because that is the `domain_name` default.
```

Match each file's surrounding wrapping and prose style; adjust wording to fit
but keep both halves of the rule (where `example.com` is allowed, where
`.test` is required) and the sentinel rationale in the root version.

**Verify**:
```
grep -c 'example.test' AGENTS.md '{{cookiecutter.project_slug}}/AGENTS.md'
```
→ ≥ 1 in each. Then bake default and confirm the bullet renders in the
generated project: `grep -n 'Placeholder hostnames' /tmp/verify-009/cors/my-project/AGENTS.md`
→ 1 match (re-bake if Step 1's bake predates this edit).

### Step 3: Full-suite verification on both bakes

In the **cors bake**: ruff format/check → exit 0; Postgres up; `uv run pytest`
→ all pass at 100% coverage (this executes `cors_test.py` with the new
origins and `tasks_test.py` against the new DEFAULT_FROM_EMAIL). Note: if
`ruff format` fails on `tests/api/integration/throttling_test.py`, that is
plan 001's still-open defect B, not yours — report it and continue.

In the **smtp bake**: `uv run pytest` → all pass (exercises
`prod_settings_test.py`'s EMAIL_HOST path plus the new Sentry DSN literal).

### Step 4: Script, workflow, and docs lint

In the cors bake, after `git add -A`:
`uv run pre-commit run shellcheck --all-files`,
`uv run pre-commit run actionlint --all-files`, and
`uv run pre-commit run markdownlint --all-files` → pass (guards the three
`.sh` scripts, the workflow edit, and the new AGENTS.md bullet). Root:
`uvx pre-commit run --all-files` → pass (covers the root ci.yaml edit via
actionlint/zizmor/yamllint and the root AGENTS.md bullet via markdownlint).

## Test plan

No new tests — existing tests are the guard: `cors_test.py` asserts the
exact new origins, `tasks_test.py` asserts DEFAULT_FROM_EMAIL wiring,
`prod_settings_test.py` imports prod settings with the new DSN, and the CI
bake matrix + compose smoke re-execute the scripts/Dockerfile env end-to-end
on push.

## Done criteria

Machine-checkable. ALL must hold:

- [ ] Step 1's sweep grep output matches the stated allowlist exactly
- [ ] `grep -c 'example\.test' '{{cookiecutter.project_slug}}/.docker/Dockerfile'` → 3
- [ ] The rule bullet exists in BOTH AGENTS.md files and renders in a bake (Step 2 greps)
- [ ] cors bake and smtp bake: `uv run pytest` exit 0 at 100% coverage
- [ ] Baked shellcheck + actionlint + markdownlint pass; root `uvx pre-commit run --all-files` passes
- [ ] `git status --short` shows changes ONLY to the twelve in-scope files
- [ ] `plans/README.md` status row updated

## STOP conditions

Stop and report back (do not improvise) if:

- A listed literal is not found at (or near) its cited line — the file
  drifted; re-locate by grep, and if the occurrence is gone entirely, report
  instead of guessing.
- Any test failure in Step 2 other than plan 001's known throttling_test
  ruff-format defect — especially any test that turns out to assert a
  hardcoded `example.com` this plan's inventory missed.
- You find additional `example.com` occurrences in machine-consumed contexts
  not listed here — apply the rule ONLY if the context is unambiguous
  (test/CI/build env value); otherwise report it.

## Maintenance notes

- The rule is now recorded in both AGENTS.md files (Step 2), so agents and
  reviewers enforce it on future changes. The boot sentinel specifically MUST
  stay `example.com` — it exists to catch the unmodified `domain_name`
  default, which is `example.com`; the root bullet says so.
- If plan 004 (item F, rtk removal) has not yet landed when this executes,
  the generated AGENTS.md anchors shift by two lines — that is why Step 2
  anchors by content, not line number.
- Site 6's DEFAULT_FROM_EMAIL change decouples the pytest env from the
  `domain_name` knob; if a future test ever needs the knob-derived value,
  derive it in the test, not in the shared env.
- The `.agents/` vendored docs keep `example.com` freely — they are generic
  Django reference material, not template config.
