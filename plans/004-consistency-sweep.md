# Plan 004: Consistency sweep — CI smoke gating, anymail app, docs guards, rtk removal, artifact scrub

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving to the
> next step. If anything in the "STOP conditions" section occurs, stop and
> report — do not improvise. When done, update the status row for this plan
> in `plans/README.md` — unless a reviewer dispatched you and told you they
> maintain the index.
>
> **Drift check (run first)**:
> `git diff --stat eee3978..HEAD -- '{{cookiecutter.project_slug}}/.docker/compose/ci-services.yaml' '{{cookiecutter.project_slug}}/src/config/settings/components/apps.py' '{{cookiecutter.project_slug}}/README.md' '{{cookiecutter.project_slug}}/AGENTS.md' hooks/post_gen_project.py`
> If any in-scope file changed since this plan was written, compare the
> "Current state" excerpts against the live code before proceeding; on a
> mismatch, treat it as a STOP condition.

## Status

- **Priority**: P2
- **Effort**: M
- **Risk**: LOW
- **Depends on**: none (touches `README.md`/`AGENTS.md` — execute after 003,
  which adds one README sentence, to avoid merge conflicts; soft ordering)
- **Category**: bug / docs / dx
- **Planned at**: commit `eee3978`, 2026-07-08

## Why this matters

Six small, independently verified inconsistencies from the 2026-07-08 deep
audit. None is individually urgent; together they are the difference between
a template that is right and one that is *almost* right: a CI smoke race, a
library wired against its documented setup, generated docs that reference
things the bake deleted, maintainer-personal tooling instructions shipped to
every downstream project, and stale build artifacts copied into every fresh
project.

## Current state

This repo is a **cookiecutter template**. Files under
`{{cookiecutter.project_slug}}/` contain Jinja; verify by baking. Always
single-quote paths containing `{{cookiecutter.project_slug}}` in shell
commands. Conventions (root `AGENTS.md`): alphabetize where order doesn't
matter; extended YAML block style; conventional commits.

**(A) CI smoke race for external Postgres/Redis.**
`{{cookiecutter.project_slug}}/.docker/compose/prod.yaml:15-25` emits the
api service's `depends_on` only for `postgres == "compose"` /
`redis == "compose"`; external bakes drop it (correct for real deployments —
the DB isn't a compose service there). But the CI overlay
`{{cookiecutter.project_slug}}/.docker/compose/ci-services.yaml` (merged over
prod.yaml by the generated `docker-checks.yaml` smoke job) adds stand-in
`postgres`/`redis` services with healthchecks **without** restoring the
`depends_on`, so `api`'s `pre_start` (`migrations.sh` — plain
`python manage.py migrate`, no retry) can fire before the stand-in Postgres
finishes initdb. Currently masked by image build time; it's a latent flake.
Current overlay (abridged; read the full 45-line file):

```yaml
# CI-only stand-ins for external backing services; merged over prod.yaml by
# the docker-checks smoke job. Never use in production.
{% if cookiecutter.postgres != "external" and cookiecutter.redis != "external" -%}
services: {}
{%- else -%}
services:
{%- if cookiecutter.postgres == "external" %}
  postgres:
    environment: ...
    healthcheck: ...
    image: postgres:18.4
{%- endif %}
{%- if cookiecutter.redis == "external" %}
  redis:
    command: ...
    healthcheck: ...
    image: redis:8.8.0
{%- endif %}
{%- endif %}
```

**(B) `anymail` missing from INSTALLED_APPS.**
`{{cookiecutter.project_slug}}/src/config/settings/environments/prod.py`
(resend branch) sets `EMAIL_BACKEND = "anymail.backends.resend.EmailBackend"`
and `ANYMAIL = {...}`, but
`{{cookiecutter.project_slug}}/src/config/settings/components/apps.py` never
adds `"anymail"`. Sending works without it, but django-anymail's documented
setup includes the app (system checks, status signals, webhook views). The
third-party block currently reads:

```python
    # Third-party
    "axes",
{%- if cookiecutter.use_cors == "yes" %}
    "corsheaders",
{%- endif %}
    ...
```

`"anymail"` sorts before `"axes"`. Only the `resend` provider uses anymail
(`smtp` uses Django's builtin backend; the `django-anymail[resend]` dependency
in `pyproject.toml` is already guarded by
`{% if cookiecutter.email_provider == "resend" %}`) — guard the app entry the
same way. Related: `pyproject.toml`'s `[tool.deptry.per_rule_ignores]` DEP002
has a comment "Loaded via EMAIL_BACKEND dotted path in
settings/environments/prod.py." for `django-anymail` — update that comment to
mention INSTALLED_APPS (deptry still can't see either, so the ignore stays).

**(C) Generated README tells Celery-less operators to sync
`CELERY_BROKER_URL`.** Two unguarded mentions in
`{{cookiecutter.project_slug}}/README.md`:
- ~line 391 (inside `{% if cookiecutter.postgres == "compose" %}`): "Keep
  `REDIS_PASSWORD` in sync with the credentials embedded in `CACHE_URL` and
  `CELERY_BROKER_URL`."
- ~line 430 (inside the `postgres != compose` / `redis == "compose"` branch):
  "Keep it in sync with the credentials embedded in `CACHE_URL` and
  `CELERY_BROKER_URL`; production boot refuses..."
A third mention (~line 565) is already correctly guarded by
`use_celery != "none"` — use its guard style. When `use_celery=none`, the
baked `.env.example` has no `CELERY_BROKER_URL`, so the sentence instructs
syncing a variable that doesn't exist. The fix is inline Jinja so the sentence
reads "embedded in `CACHE_URL`" (celery=none) vs "embedded in `CACHE_URL` and
`CELERY_BROKER_URL`" (otherwise), in both places.

**(D) Generated AGENTS.md references deleted files.** In
`{{cookiecutter.project_slug}}/AGENTS.md` (line numbers post-`61eec63`, which
added ~11 lines above these):
- ~Line 140, an UNGUARDED bullet: "The example notes resource uses
  `apps.notes.controllers.NotesController`, a django-ninja-extra class-based
  controller; ..." — renders even when `use_example_api=no`, where
  `src/apps/notes/` is deleted by `hooks/post_gen_project.py`. Wrap the whole
  bullet in `{% if cookiecutter.use_example_api == "yes" %}` / `{% endif %}`,
  matching the guarded bullets above it (the token-auth bullet uses exactly
  this pattern). The bullet's second half ("`/api/health` and `/api/ready`
  remain plain function-based routers on `internal_api`") is knob-independent
  — keep that statement rendering unconditionally, either by splitting the
  bullet or moving the clause; prefer the smallest diff that leaves no
  dangling reference.
- ~Line 152, the Testing section: "Shared helpers stay at the `tests/` root
  (`conftest.py`, `factories.py`, `utils.py`)." — `tests/utils.py` is deleted
  when `use_example_api=no`. Make the `utils.py` mention conditional with
  inline Jinja:
  `` (`conftest.py`, `factories.py`{% if cookiecutter.use_example_api == "yes" %}, `utils.py`{% endif %}) ``.
- The post-gen hook collapses runs of 3+ newlines in AGENTS.md/README.md, so
  guarded blocks may rely on that; verify renders, don't hand-trace.

**(E) Stale build artifacts inside the template directory are copied into
every bake.** `{{cookiecutter.project_slug}}/.ruff_cache/` and
`{{cookiecutter.project_slug}}/tests/__pycache__/` exist on disk (untracked;
`git ls-files` confirms) and cookiecutter copies the working tree, so every
locally-baked project ships a stale `.pyc` (built against pytest 9.1.1, pin
is 9.0.3) and a warm ruff cache. Fix twice: delete them now, and make
`hooks/post_gen_project.py` scrub defensively. The hook's existing style:
`REMOVED_PATHS`/`REMOVED_DIRS` constants + deletion loops in `main()`,
helpers under `# Utils` alphabetized. Add a scrub in `main()` after the
`REMOVED_DIRS` loop:

```python
    for cache_dir in Path().rglob("__pycache__"):
        shutil.rmtree(cache_dir)

    for cache_dir in Path().rglob(".ruff_cache"):
        shutil.rmtree(cache_dir)
```

(Note: `hooks/post_gen_project.py` contains Jinja substitutions at the top
(`{{ cookiecutter.x | tojson }}` constants) and is not plain Python until
rendered — edit carefully, keep your addition Jinja-free.)

**(F) Maintainer-personal `rtk` tooling instructions ship in every generated
project.** `rtk` is the template maintainer's private token-optimizing CLI
proxy; downstream users don't have it. Two references in
`{{cookiecutter.project_slug}}/AGENTS.md` (maintainer decision 2026-07-08:
remove both):

- Lines 5-6, the first Command Workflow bullet (delete the whole bullet):

  ```markdown
  - If the `rtk` CLI is available, prefix shell commands with `rtk`
    (token-optimizing proxy); otherwise run commands directly.
  ```

- Line 163, a trailing sentence inside the "Run relevant checks before
  completion:" bullet in the Testing section (delete only this line; keep
  the command sub-list above it intact):

  ```markdown
    Prefix these with `rtk` when it is available.
  ```

The ROOT `AGENTS.md` also mentions rtk — that copy guides work on the
template repo itself and is deliberately KEPT (out of scope).

## Commands you will need

| Purpose | Command | Expected on success |
|---------|---------|---------------------|
| Bake | `uvx cookiecutter . -o /tmp/verify-004/<case> --no-input <knobs>` | project generated |
| Compose config (in bake) | `cp .env.example .env && docker compose -f .docker/compose/prod.yaml -f .docker/compose/ci-services.yaml --env-file=.env config` | valid YAML, exit 0 |
| Lint (in bake) | `uvx ruff@0.15.16 format --check . && uvx ruff@0.15.16 check .` | exit 0 |
| Django checks (in bake, needs deps) | `uv sync --locked && DJANGO_ENV=ci SECRET_KEY=mock-secret-key ALLOWED_HOSTS=localhost CACHE_URL=locmemcache:// uv run python manage.py check` | `System check identified no issues` (or only known warnings) |
| Root checks | `uvx pre-commit run --all-files` | all hooks pass |

## Scope

**In scope** (the only files you should modify):
- `{{cookiecutter.project_slug}}/.docker/compose/ci-services.yaml`
- `{{cookiecutter.project_slug}}/src/config/settings/components/apps.py`
- `{{cookiecutter.project_slug}}/pyproject.toml` (comment only, item B)
- `{{cookiecutter.project_slug}}/README.md` (item C guards only)
- `{{cookiecutter.project_slug}}/AGENTS.md` (item D guards + item F deletions only)
- `hooks/post_gen_project.py` (item E scrub)
- Deletions: `{{cookiecutter.project_slug}}/.ruff_cache/`,
  `{{cookiecutter.project_slug}}/tests/__pycache__/` (untracked — plain `rm -rf`)

**Out of scope** (do NOT touch, even though they look related):
- `{{cookiecutter.project_slug}}/.docker/compose/prod.yaml` — dropping
  `depends_on` for external topologies there is CORRECT; the fix is CI-overlay
  only. (Plan 003 edits prod.yaml; stay out of its way.)
- `{{cookiecutter.project_slug}}/.github/workflows/docker-checks.yaml` — it is
  `_copy_without_render`; no Jinja allowed, and no change needed.
- Root `README.md`/`AGENTS.md` — in particular, the root AGENTS.md's own
  `rtk` guidance stays (item F removes it only from the generated copy).

## Git workflow

- Branch: `advisor/004-consistency-sweep`
- One commit per item (A–F), conventional-commit style, e.g.
  `fix: gate the CI smoke api on stand-in service health`,
  `fix: install the anymail app for resend bakes`,
  `docs: guard celery and example-api references in generated docs`,
  `docs: drop maintainer-specific rtk guidance from generated projects`,
  `chore: scrub cache artifacts from bakes`.
- Do NOT push or open a PR unless the operator instructed it.

## Steps

### Step 1 (A): Restore startup gating in the CI overlay

In `ci-services.yaml`, inside the `{% else %}` branch (external services
exist), add an `api` service entry that re-establishes `depends_on` for
whichever stand-ins render:

```yaml
services:
  api:
    depends_on:
{%- if cookiecutter.postgres == "external" %}
      postgres:
        condition: service_healthy
{%- endif %}
{%- if cookiecutter.redis == "external" %}
      redis:
        condition: service_healthy
{%- endif %}
```

Keep services alphabetized (`api` before `postgres`/`redis`). Compose merges
this over prod.yaml's api service additively.

**Verify**:
```
uvx cookiecutter . -o /tmp/verify-004/external --no-input postgres=external redis=external use_traefik=no
cd /tmp/verify-004/external/my-project && cp .env.example .env
printf 'REDIS_PASSWORD=mock-redis-password\n' >> .env
docker compose -f .docker/compose/prod.yaml -f .docker/compose/ci-services.yaml --env-file=.env config | grep -B1 -A3 'depends_on'
```
→ rendered config shows api `depends_on` postgres and redis with
`condition: service_healthy`. Also bake `postgres=external` alone (redis
compose) and confirm only postgres appears in the overlay's depends_on and
`config` still validates (prod.yaml already provides redis gating there).
Also bake default and confirm `ci-services.yaml` still renders `services: {}`.

### Step 2 (B): Add the anymail app + fix the deptry comment

In `apps.py`, third-party block, before `"axes"`:

```python
    # Third-party
{%- if cookiecutter.email_provider == "resend" %}
    "anymail",
{%- endif %}
    "axes",
```

In `pyproject.toml`, update the DEP002 comment for `django-anymail` to:
`# Loaded via INSTALLED_APPS and the EMAIL_BACKEND dotted path.`

**Verify**:
```
uvx cookiecutter . -o /tmp/verify-004/resend --no-input
grep -n '"anymail"' /tmp/verify-004/resend/my-project/src/config/settings/components/apps.py
uvx cookiecutter . -o /tmp/verify-004/smtp --no-input email_provider=smtp
grep -c 'anymail' /tmp/verify-004/smtp/my-project/src/config/settings/components/apps.py
```
→ first grep: 1 match; second: 0 matches. Then in the resend bake:
`uv sync --locked` + the Django `check` command from the table → no new
issues. If `manage.py check` needs more env than the table shows, mirror the
env from `pyproject.toml [tool.pytest.ini_options] env` in the bake.

### Step 3 (C): Guard the CELERY_BROKER_URL prose

Apply inline guards at both README sites so `CELERY_BROKER_URL` is mentioned
only when `use_celery != "none"`, e.g.:

```
Keep `REDIS_PASSWORD` in sync with the credentials embedded in
`CACHE_URL`{% if cookiecutter.use_celery != "none" %} and `CELERY_BROKER_URL`{% endif %}.
```

**Verify**:
```
uvx cookiecutter . -o /tmp/verify-004/nocelery --no-input use_celery=none
grep -c 'CELERY_BROKER_URL' /tmp/verify-004/nocelery/my-project/README.md
grep -c 'CELERY_BROKER_URL' /tmp/verify-004/nocelery/my-project/.env.example
```
→ both `0`. And in the default bake, the README still mentions it (grep ≥ 1).

### Step 4 (D): Guard the AGENTS.md references

Apply the guards described in Current state (NotesController bullet;
`utils.py` mention).

**Verify**:
```
uvx cookiecutter . -o /tmp/verify-004/noexample --no-input
grep -c 'NotesController\|`utils.py`' /tmp/verify-004/noexample/my-project/AGENTS.md
```
→ `0`, while `grep -c 'internal_api'` on the same file → ≥ 1 (the probe
statement survived). In an example bake (`use_example_api=yes`), both
references render (grep ≥ 1 each). Run markdownlint on both bakes (inside the
bake, after `git add AGENTS.md`):
`uv run pre-commit run markdownlint --files AGENTS.md` → pass.

### Step 5 (E): Delete artifacts + add hook scrub

```
rm -rf '{{cookiecutter.project_slug}}/.ruff_cache' '{{cookiecutter.project_slug}}/tests/__pycache__'
```
Then add the scrub loops to `hooks/post_gen_project.py` `main()` as excerpted
in Current state.

**Verify**:
```
uvx cookiecutter . -o /tmp/verify-004/clean --no-input
find /tmp/verify-004/clean/my-project -name '__pycache__' -o -name '.ruff_cache' | wc -l
```
→ `0`. (The bake succeeding IS the hook test — `hooks/` is excluded from root
pre-commit and contains Jinja, so `py_compile` on the template file itself
will not work.)

### Step 6 (F): Remove the rtk lines from the generated AGENTS.md

In `{{cookiecutter.project_slug}}/AGENTS.md`, delete the two references
excerpted in Current state item F: the whole two-line bullet at lines 5-6,
and the single trailing line `  Prefix these with `rtk` when it is
available.` (~line 163; line numbers shift by -2 after the first deletion).
Do not touch the command sub-list the trailing line follows, and do not touch
the root `AGENTS.md`.

**Verify**:
```
grep -c 'rtk' '{{cookiecutter.project_slug}}/AGENTS.md'
grep -c 'rtk' AGENTS.md
uvx cookiecutter . -o /tmp/verify-004/nortk --no-input
grep -c 'rtk' /tmp/verify-004/nortk/my-project/AGENTS.md
```
→ `0` for the template project file and the bake; ≥ 1 for the root file
(unchanged). Then markdownlint on the baked file (inside the bake, after
`git add AGENTS.md`): `uv run pre-commit run markdownlint --files AGENTS.md`
→ pass (guards against a list left malformed by the deletion).

## Test plan

No new Python tests. Every item's regression guard is a render assertion
listed in its step, all of which the CI bake matrix re-executes implicitly
(pre-commit + pytest per bake). Item A's end-to-end guard is the
`external-backing` smoke variant in root ci.yaml on push.

## Done criteria

Machine-checkable. ALL must hold:

- [ ] Step 1–6 verification greps/commands all produce the stated outputs
- [ ] Default bake: `uvx ruff@0.15.16 format --check . && uvx ruff@0.15.16 check .` → exit 0 (no formatting collateral from hook edits)
- [ ] `git status --short` shows changes ONLY to in-scope files (plus the two deletions)
- [ ] Root `uvx pre-commit run --all-files` passes
- [ ] `plans/README.md` status row updated

## STOP conditions

Stop and report back (do not improvise) if:

- Any excerpt in Current state doesn't match the live file (drift — plans
  001/003 touch neighboring files/regions, and this repo has concurrent
  sessions).
- The compose `config` merge in Step 1 errors or produces a `depends_on` on a
  service that doesn't exist in that combo.
- anymail's `manage.py check` reports check errors with the pinned versions —
  report them; do not silence checks.
- The AGENTS.md restructure in Step 4 would require rewriting more than the
  two bullets — the goal is guards, not a docs rewrite.

## Maintenance notes

- Item A: if a future knob adds another external stand-in service, the
  overlay must gain the matching `depends_on` entry — the overlay is now the
  single place that owns CI startup ordering for external topologies.
- Item C/D are symptoms of a class (knob-guarded features with unguarded
  prose). Reviewer: when any new knob lands, grep the generated README and
  AGENTS.md of an all-off bake for the feature's identifiers.
- Item E's hook scrub also protects users who bake from a git clone with
  their own stale caches.
