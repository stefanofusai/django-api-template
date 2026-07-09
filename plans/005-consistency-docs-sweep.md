# Plan 005: Consistency sweep — README quickstart, AGENTS.md test-client guidance, dev Redis auth gating, postgres-image guard coverage, GHCR naming docs, stale `plans/` refs

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving to the
> next step. If anything in the "STOP conditions" section occurs, stop and
> report — do not improvise. When done, update the status row for this plan
> in `plans/README.md` — unless a reviewer dispatched you and told you they
> maintain the index. The six items (A-F) are independent; if one hits a STOP
> condition, finish the others and report the blocked one.
>
> **Drift check (run first)**:
> `git diff --stat e0ec725..HEAD -- README.md AGENTS.md .pre-commit-config.yaml scripts/check_postgres_image.py tests/check_postgres_image_test.py cookiecutter.json '{{cookiecutter.project_slug}}/AGENTS.md' '{{cookiecutter.project_slug}}/.docker/compose/dev.yaml' '{{cookiecutter.project_slug}}/README.md'`
> If any in-scope file changed since this plan was written, compare the
> "Current state" excerpts against the live code before proceeding; on a
> mismatch, treat it as a STOP condition for that item only.

## Status

- **Priority**: P3
- **Effort**: M (six S-sized independent items)
- **Risk**: LOW
- **Depends on**: none (coordinate with plan 004 if executed concurrently — both edit the generated `README.md`; land 004 first or anchor edits on headings)
- **Category**: docs / dx
- **Planned at**: commit `e0ec725`, 2026-07-09

## Why this matters

Six small drifts left behind by the last development cycle (JWT migration,
OpenAPI drift gate, plans-directory deletion). Individually cosmetic;
together they're exactly the kind of stale guidance that misleads the humans
and agents this template is built to serve. Worst of the six: a user who
follows the root README's post-generation quickstart (instead of the hook's
terminal output) commits a project with no committed OpenAPI schemas and
fails their first CI run at the drift gate — broken out of the box.

## Current state

This repository is a cookiecutter template. Files under
`{{cookiecutter.project_slug}}/` are Jinja-rendered into generated projects
(EXCEPT `.github/workflows/*` and `.agents/*`, which are copied without
rendering). Always quote paths containing `{{cookiecutter.project_slug}}` in
shell commands.

**Item A — root README quickstart omits the OpenAPI export.**
`README.md:151-158` (root):

```shell
uv sync --locked
cp .env.example .env
uv run pre-commit install --install-hooks
git add -A
git commit -m "feat: initial project scaffold"
```

But the authoritative next-steps the post-gen hook prints
(`hooks/post_gen_project.py:177-186`) include, before the commit:

```
mkdir -p docs/openapi
uv run python manage.py export_openapi_schema --api=internal --output=docs/openapi/openapi-internal.json
uv run python manage.py export_openapi_schema --api=v1 --output=docs/openapi/openapi-v1.json
```

The generated `.github/workflows/openapi-schema-export.yaml` fails CI when
generated schemas differ from committed ones — including when they're absent.

**Item B — generated AGENTS.md names a fixture that doesn't exist.**
`{{cookiecutter.project_slug}}/AGENTS.md:193` (one unconditional bullet, no
Jinja guard):

```
- Test API endpoints through the ninja `TestClient` fixtures (`internal_api_client`, `v1_api_client`, `authenticated_client`) using `response.data` and router-relative paths; pass `user=` (or use `authenticated_client`) for authenticated endpoints.
```

Facts: the real fixture is `authenticated_v1_api_client`
(`{{cookiecutter.project_slug}}/tests/conftest.py:106`), which exists only
when `use_example_api == "yes"`. It returns an `AuthenticatedTestClient`
(`tests/utils.py`) that authenticates via `user=` in session bakes and via
`headers={"Authorization": "Bearer ..."}` in JWT bakes — the Jinja branches
are in `tests/utils.py`. The bare `user=` advice is wrong for JWT bakes.

**Item C — dev Redis auth references an env var that external bakes don't
emit.** `{{cookiecutter.project_slug}}/.docker/compose/dev.yaml:112-121` — the
`redis` service is unconditional and reads `${REDIS_PASSWORD}` twice:

```yaml
  redis:
    command:
      - redis-server
      - --appendonly
      - "yes"
      - --requirepass
      - ${REDIS_PASSWORD}
    environment:
      REDISCLI_AUTH: ${REDIS_PASSWORD}
```

But `.env.example:89-94` emits `REDIS_PASSWORD` only inside
`{%- if cookiecutter.redis == "compose" %}`. In a `redis=external` bake,
`docker compose ... up` warns `variable is not set` and the dev Redis runs
with an empty `--requirepass` (auth disabled). This is *self-consistent* —
the external-branch dev `CACHE_URL` (`.env.example`: `rediscache://redis:6379/0`)
is passwordless, and the dev redis publishes no host ports — but it's noisy
and inconsistent with the compose branch.

IMPORTANT: do NOT "fix" this by emitting `REDIS_PASSWORD` unconditionally —
that would give the dev Redis a password that the external-branch passwordless
`CACHE_URL` doesn't carry, breaking dev cache connections. The right fix (the
file IS Jinja-rendered): gate the two auth lines on the same knob as
`.env.example`.

**Item D — `check_postgres_image.py` doesn't guard `ci-services.yaml`.**
`scripts/check_postgres_image.py:7-14`:

```python
CANONICAL = Path("{{cookiecutter.project_slug}}/.docker/compose/prod.yaml")
FILES = [
    Path("{{cookiecutter.project_slug}}/.docker/compose/dev.yaml"),
    Path("{{cookiecutter.project_slug}}/.github/workflows/migration-checks.yaml"),
    Path("{{cookiecutter.project_slug}}/.github/workflows/tests.yaml"),
    Path(".github/workflows/ci.yaml"),
]
```

Missing: `{{cookiecutter.project_slug}}/.docker/compose/ci-services.yaml`,
which pins `image: postgres:18.4` at line 32 and is composed into every CI
smoke boot. Tests live in `tests/check_postgres_image_test.py` (they test the
pure `check()` function; none asserts `FILES` contents).

**Item E — GHCR image name is coupled to two cookiecutter variables without
saying so.** `{{cookiecutter.project_slug}}/.docker/compose/prod.yaml:46,104,134`
pull `ghcr.io/{{ cookiecutter.github_username | lower }}/{{ cookiecutter.project_slug }}:${APP_VERSION:-unreleased}`,
while the generated `release.yaml` pushes to `ghcr.io/${GITHUB_REPOSITORY,,}`
(owner/repo of the actual GitHub repository). If the repo is org-owned
(owner ≠ `github_username`) or named differently from `project_slug`, the
first real deploy fails at `docker compose pull`. Currently documented
nowhere: `cookiecutter.json`'s prompt says only "GitHub username used for
Dependabot assignees", and the root README Variables table matches.

**Item F — stale `plans/` references.** The plans directory was deleted in
`e0ec725` and recreated by this advisor cycle — so the two references below
are stale-then-accidentally-true again; fix them to be *deliberate*:

- Root `AGENTS.md:26`: "Root-level files control the template itself:
  `cookiecutter.json`, `hooks/`, `.github/`, `plans/`, and `README.md`." —
  keep `plans/` but this list's framing is fine once plans/ exists again;
  verify the sentence still reads correctly and leave it if so.
- `.pre-commit-config.yaml:4`:
  `exclude: ^(\{\{cookiecutter\.project_slug\}\}/|hooks/|plans/)` — this
  exclude is again load-bearing now that `plans/` exists (plan files must not
  be subjected to the template's format hooks); verify and leave it.

So item F reduces to: confirm both references are consistent with the
recreated `plans/` directory and change NOTHING unless one is actually
broken. (The audit flagged them while `plans/` was deleted; this plan's own
existence un-staled them. Recorded here so the finding is closed with
reasoning, not silently dropped.)

**Conventions** (root `AGENTS.md`): alphabetize list entries when order
doesn't matter; extended YAML block style; conventional commits; keep root
guidance in root AGENTS.md and generated-app guidance in the generated
AGENTS.md.

## Commands you will need

| Purpose | Command | Expected on success |
|---------|---------|---------------------|
| Root unit tests | `uvx pytest tests` | all pass |
| Root pre-commit | `uvx pre-commit run --all-files` | exit 0 |
| Bake default | `uvx cookiecutter . -o /tmp/verify-005 --no-input` | exit 0 |
| Bake redis-external | `uvx cookiecutter . -o /tmp/verify-005-ext --no-input redis=external` | exit 0 |
| Bake example API (jwt) | `uvx cookiecutter . -o /tmp/verify-005-jwt --no-input use_example_api=yes api_auth=jwt` | exit 0 |
| Dev boot (optional, item C) | in a baked project: `cp .env.example .env && docker compose -f .docker/compose/dev.yaml --env-file=.env up -d --wait postgres redis && docker compose -f .docker/compose/dev.yaml --env-file=.env down -v` | no "variable is not set" warning; redis healthy |

## Scope

**In scope** (the only files you should modify):

- `README.md` (root — item A)
- `{{cookiecutter.project_slug}}/AGENTS.md` (item B)
- `{{cookiecutter.project_slug}}/.docker/compose/dev.yaml` (item C)
- `scripts/check_postgres_image.py` and `tests/check_postgres_image_test.py` (item D)
- `cookiecutter.json` (item E — the `github_username` prompt string only)
- `{{cookiecutter.project_slug}}/README.md` (item E — one note in the Production/Deploying section)

**Out of scope** (do NOT touch, even though they look related):

- `{{cookiecutter.project_slug}}/.env.example` — see item C's IMPORTANT note.
- `{{cookiecutter.project_slug}}/.github/workflows/release.yaml` — pushing to
  `GITHUB_REPOSITORY` is correct; the fix is documentation, not plumbing an
  env var through compose (adjudicated: not worth the moving part for a
  template).
- `hooks/post_gen_project.py` — its printed next-steps are the source of
  truth item A copies FROM.
- Root `AGENTS.md` / `.pre-commit-config.yaml` beyond item F's
  verify-and-leave.

## Git workflow

- Branch: `advisor/005-consistency-docs-sweep`
- Commit style: conventional commits, one commit per item (e.g.
  `docs: add openapi export to post-generation quickstart`,
  `fix: gate dev redis auth on the redis knob`, ...).
- Do NOT push or open a PR unless the operator instructed it.

## Steps

### Step A: Sync the root README quickstart with the hook's next-steps

In root `README.md`, in the "After generation:" code block (~line 151),
insert between `uv run pre-commit install --install-hooks` and `git add -A`:

```shell
mkdir -p docs/openapi
uv run python manage.py export_openapi_schema --api=internal --output=docs/openapi/openapi-internal.json
uv run python manage.py export_openapi_schema --api=v1 --output=docs/openapi/openapi-v1.json
```

(Exactly the hook's lines, `hooks/post_gen_project.py:181-183`.)

**Verify**: `diff <(grep -A9 "After generation:" README.md | grep -E "uv |git |mkdir") <(sed -n '/Next steps/,/git add/p' hooks/post_gen_project.py | grep -oE '(uv |git |mkdir).*' | sed "s/\\\\n\"$//")`
— or more simply: manually confirm the README block now lists the same 7
commands in the same order as the hook's `print`, then
`grep -c export_openapi_schema README.md` → 2.

### Step B: Fix the generated AGENTS.md test-client bullet

Replace the single bullet at `{{cookiecutter.project_slug}}/AGENTS.md:193`
with accurate, knob-aware guidance. Target shape (adjust wording to match the
file's voice; the Jinja guards are the load-bearing part):

```markdown
- Test API endpoints through the ninja `TestClient` fixtures
  (`internal_api_client`, `v1_api_client`{% if cookiecutter.use_example_api == "yes" %}, `authenticated_v1_api_client`{% endif %})
  using `response.data` and router-relative paths.
{%- if cookiecutter.use_example_api == "yes" and cookiecutter.api_auth == "jwt" %}
- For authenticated endpoints use `authenticated_v1_api_client`, which sends
  a Bearer access token via `headers` (see `tests/utils.py`); do not pass
  `user=` for JWT-authenticated routes.
{%- elif cookiecutter.use_example_api == "yes" %}
- For authenticated endpoints use `authenticated_v1_api_client`, or pass
  `user=` to a bare client for session-authenticated routes.
{%- endif %}
```

Note the generated AGENTS.md may or may not already use Jinja elsewhere —
check the file top for `{% raw %}` blocks before adding Jinja; if the whole
file is wrapped in `{% raw %}`, STOP for item B and report (Jinja inside raw
renders literally).

**Verify**: bake all three variants from the command table.
`grep -c authenticated_client` on each baked `AGENTS.md` → 0 (grep exits 1).
`grep -c authenticated_v1_api_client` → ≥1 in the example-api bakes, 0 in the
default (empty-API) bake. In the JWT bake, the bullet mentions Bearer
headers, not `user=`.

### Step C: Gate dev Redis auth on the redis knob

In `{{cookiecutter.project_slug}}/.docker/compose/dev.yaml`, wrap the two
auth pieces of the `redis` service in the same guard `.env.example` uses:

```yaml
  redis:
    command:
      - redis-server
      - --appendonly
      - "yes"
{%- if cookiecutter.redis == "compose" %}
      - --requirepass
      - ${REDIS_PASSWORD}
    environment:
      REDISCLI_AUTH: ${REDIS_PASSWORD}
{%- endif %}
```

(Check the actual current layout first — `environment:` holds only
`REDISCLI_AUTH`, so it moves inside the guard wholesale. Keep the
healthcheck, image, and volumes untouched.)

**Verify**: bake `redis=external` →
`grep -c REDIS_PASSWORD /tmp/verify-005-ext/my-project/.docker/compose/dev.yaml`
→ 0. Bake default (redis=compose) → same grep → 2. Optionally boot the
external bake's dev postgres+redis (command table) → no "variable is not
set" warning, redis healthy.

### Step D: Add `ci-services.yaml` to the postgres-image guard

In `scripts/check_postgres_image.py`, add to `FILES` (alphabetical — it goes
first among the project_slug compose paths):

```python
    Path("{{cookiecutter.project_slug}}/.docker/compose/ci-services.yaml"),
```

In `tests/check_postgres_image_test.py`, add a guard test (alphabetized among
the existing test functions) so the list can't silently regress:

```python
def test_files_list_covers_ci_services_compose() -> None:
    assert (
        Path("{{cookiecutter.project_slug}}/.docker/compose/ci-services.yaml")
        in check_postgres_image.FILES
    )
```

**Verify**: `uvx pytest tests` → all pass;
`python scripts/check_postgres_image.py` → exit 0 (all pins currently agree
at 18.4; if this FAILS, a real drift exists — report it, don't paper over
it).

### Step E: Document the GHCR owner/repo coupling

1. `cookiecutter.json` — change the `github_username` prompt from
   "GitHub username used for Dependabot assignees" to
   "GitHub owner (user or org) used for Dependabot assignees and the GHCR
   image path".
2. Root `README.md` Variables table — update the `github_username` row's
   description to match.
3. Generated `{{cookiecutter.project_slug}}/README.md`, "Deploying releases"
   area (`### Deploying releases (recommended)` heading, ~line 290; anchor on
   the heading): add one short paragraph stating that the prod compose file
   pulls `ghcr.io/<github_username>/<project_slug>` while the release
   workflow pushes to the actual `owner/repo` of the GitHub repository —
   these must coincide (repo named `<project_slug>`, owned by
   `<github_username>`), and if the repo is renamed or moved to an org, the
   three `image:` lines in `.docker/compose/prod.yaml` must be updated.

**Verify**: `grep -n "GHCR image path" cookiecutter.json README.md` → 1 match
each; `grep -n "must coincide\|renamed or moved" '{{cookiecutter.project_slug}}/README.md'`
→ ≥ 1 match. Bake default → the note renders in the baked README.

### Step F: Verify (don't change) the `plans/` references

Confirm `plans/` exists at the repo root (recreated by the advisor cycle that
wrote this plan), that root `AGENTS.md:26` listing `plans/` is therefore
accurate, and that `.pre-commit-config.yaml:4`'s exclude regex keeps plan
files out of format hooks (`uvx pre-commit run --all-files` must not modify
anything under `plans/`).

**Verify**: `ls plans/ | head -3` shows plan files;
`uvx pre-commit run --all-files` → exit 0 with `git status` showing no
modifications under `plans/`.

### Step G: Full verification sweep

Root `uvx pre-commit run --all-files` and `uvx pytest tests`; bake the three
variants and spot-check per-item verifications above. The root pre-commit's
`generated-format` hook re-bakes and ruff-checks generated combos — it must
stay green after items B/C/E touched Jinja-bearing files.

**Verify**: all exit 0.

## Test plan

- Item D gets a real unit test (step D). Items A/B/C/E/F are docs/config;
  their regression protection is the grep-based done criteria plus the
  `generated-format` root hook and CI bake matrix that already exercise
  rendered output for multiple knob combos.

## Done criteria

Machine-checkable. ALL must hold:

- [ ] `grep -c export_openapi_schema README.md` → 2
- [ ] Baked example-api projects contain no `authenticated_client` (bare) reference in AGENTS.md; JWT bake's AGENTS.md describes Bearer-header auth
- [ ] `redis=external` bake: `grep -c REDIS_PASSWORD .docker/compose/dev.yaml` → 0; default bake → 2
- [ ] `uvx pytest tests` → all pass including `test_files_list_covers_ci_services_compose`
- [ ] `python scripts/check_postgres_image.py` → exit 0
- [ ] `grep -n "GHCR image path" cookiecutter.json` → 1 match; generated README carries the coupling note
- [ ] Root `uvx pre-commit run --all-files` → exit 0, nothing under `plans/` modified
- [ ] `git status` shows no modified files outside the in-scope list
- [ ] `plans/README.md` status row updated

## STOP conditions

Stop and report back (do not improvise) if:

- (Item B) the generated `AGENTS.md` wraps content in `{% raw %}` blocks.
- (Item C) the dev.yaml redis service layout differs from the excerpt (e.g.
  `environment:` gained more keys — then only `REDISCLI_AUTH` moves inside
  the guard, and the block needs restructuring you should propose, not
  invent).
- (Item D) `python scripts/check_postgres_image.py` fails after the change —
  a REAL pin drift exists; report the mismatching file and tags.
- (Any item) the root `generated-format` hook fails on a knob combination
  after your Jinja edits — report the failing combo and diff rather than
  iterating blindly more than twice.

## Maintenance notes

- Item A: if the hook's printed next-steps change again, the README block
  must follow — consider (future work, not this plan) a root test asserting
  the README block matches the hook's `print` content.
- Item C: if dev Redis ever needs auth for external bakes, the fix is a
  dev-specific password line in `.env.example`'s external branch PLUS a
  passworded dev `CACHE_URL` — the two must move together.
- Item E: revisit if the maintainer later prefers plumbing an
  `IMAGE_REF`-style env var through compose + release instead of documented
  coupling.
- Reviewer should scrutinize: Jinja whitespace control in items B/C (rendered
  YAML indentation is the top break risk) and that item E's prompt text stays
  within cookiecutter.json's JSON string escaping rules.
