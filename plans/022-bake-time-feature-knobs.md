# Plan 022: Add bake-time feature knobs (celery, email provider, sentry, S3 media, traefik)

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving to the
> next step. If anything in the "STOP conditions" section occurs, stop and
> report — do not improvise. When done, update the status row for this plan
> in `plans/README.md` — unless a reviewer dispatched you and told you they
> maintain the index.
>
> **Drift check (run first)**: this plan was written at commit `33d77ee`
> **with plan 018's changes still uncommitted in the working tree** (Traefik
> in `prod.yaml`, `TRAEFIK_*` vars in `.env.example`, Production README
> rewrite, compose-smoke traefik probes in `.github/workflows/ci.yaml`). All
> "Current state" excerpts below reflect that working-tree state, not the
> `b7200cf` blobs. Before starting:
>
> 1. Confirm plan 018's changes have been **committed** (`git status` clean
>    for `{{cookiecutter.project_slug}}/.docker/compose/prod.yaml`,
>    `{{cookiecutter.project_slug}}/.env.example`,
>    `{{cookiecutter.project_slug}}/README.md`, `.github/workflows/ci.yaml`).
>    If they are still uncommitted or were reverted, STOP.
> 2. Confirm `prod.yaml` contains a `traefik:` service and `.env.example`
>    contains `TRAEFIK_ACME_EMAIL` / `TRAEFIK_DOMAIN`. If not, STOP.
> 3. Spot-check the excerpts in "Current state" against the live files. Two
>    kinds of drift are EXPECTED: plan 020 restructuring `.env.example`
>    into commented blocks (see the note in Step 3), and plan 019 adding
>    comment lines near excerpted code (comment-only additions — the code
>    lines themselves must still match). Any other mismatch is a STOP.

## Status

- **Priority**: P1
- **Effort**: L
- **Risk**: MED
- **Depends on**: plan 018 committed (hard); plan 020 preferred first (soft —
  see `.env.example` note); must run **before** plan 021
- **Category**: direction / dx
- **Planned at**: commit `33d77ee` + plan-018 working tree, 2026-07-05
  (the index may show 018 as DONE while its diff is still uncommitted —
  the working-tree check below is the authoritative gate)

## Why this matters

This repository is going public as an open-source cookiecutter template. The
entire value proposition of cookiecutter over "clone and delete stuff" is
bake-time configurability, and today the template has none: every baked
project gets Celery worker + beat, Resend email, Sentry, S3 media storage,
and a Traefik ingress whether it needs them or not. A user who wants a small
synchronous API must hand-strip ~15 files. This plan adds five knobs to
`cookiecutter.json` so each generated project contains only what it uses —
with **defaults that reproduce today's output byte-for-byte**, so existing
users and CI see no change.

Maintainer decisions already made (do not re-litigate):

- Knob set: `use_celery` (worker+beat / worker / none), `email_provider`
  (resend / smtp / none), `use_sentry` (yes/no), `use_s3_media` (yes/no),
  `use_traefik` (yes/no), and — folded in on 2026-07-05 — `traefik_tls`
  (letsencrypt / external). A license knob was considered and deferred to
  plan 021. **No CORS or throttling knobs — permanently rejected.**
- When Sentry is included, it stays **boot-required in prod**
  (`ImproperlyConfigured` without `SENTRY_DSN`). The knob removes Sentry
  entirely; it must NOT turn it into an env-gated no-op.
- Traefik stays the **default**; `use_traefik=no` is an opt-out for
  bring-your-own-ingress users, not a reversal of plan 018.
- `traefik_tls=external` means: Traefik still terminates TLS on 443, but
  from a **static, operator-provided PEM cert/key pair** instead of running
  ACME. It is deliberately provider-agnostic — the pair can come from
  Cloudflare Origin CA (the documented worked example, ~15-year validity),
  a purchased cert, a corporate CA, or another ACME client run elsewhere.
  Everything downstream (websecure entrypoint, forwarded-proto handling,
  Django security settings) is identical between the two modes. A
  plain-HTTP-origin mode (Cloudflare "Flexible") was **rejected**:
  plaintext origin traffic plus a forwarded-header trust problem that
  would cause redirect loops. `traefik_tls` is **ignored** when
  `use_traefik=no` (no cross-validation in pre_gen — document it instead).

## Current state

This is a cookiecutter template repo. Project code lives under the literal
directory `{{cookiecutter.project_slug}}/` (quote it in shell). Files inside
it contain Jinja placeholders that must stay valid. `cookiecutter.json`:

```json
{
    "project_name": "My Project",
    "project_slug": "{{ cookiecutter.project_name.lower().replace(' ', '-').replace('_', '-') }}",
    "description": "A Django Ninja API service.",
    "author_name": "Stefano Fusai",
    "author_email": "stefanofusai@gmail.com",
    "github_username": "stefanofusai",
    "_copy_without_render": [
        ".github/workflows/*",
        ".agents/*"
    ]
}
```

Facts you need (all verified during planning):

- **Root pre-commit excludes the template dir** — `.pre-commit-config.yaml`
  line 1: `exclude: ^(\{\{cookiecutter\.project_slug\}\}/|plans/)`. Jinja
  inside template files does not break root lint. The **rendered** output is
  what must pass lint: the root CI bakes projects and runs the baked
  project's own `pre-commit run --all-files`.
- Root pre-commit DOES lint `hooks/post_gen_project.py` as plain Python
  (`check-ast`, `ruff-check`, `ruff-format` with
  `files: ^hooks/post_gen_project\.py$`). `hooks/pre_gen_project.py` already
  contains Jinja (`{{ cookiecutter.author_email | tojson }}`) and is
  therefore NOT listed in those hooks. Step 2 adds Jinja to post_gen, so it
  must be dropped from those three `files:` patterns too.
- Baked `.github/workflows/*` are **copied without render**
  (`_copy_without_render`), so no Jinja may be added there. The baked
  `tests.yaml` currently hardcodes prod dummy env vars (`RESEND_API_KEY`,
  `SENTRY_DSN`, `AWS_STORAGE_BUCKET_NAME`) in its "Run deploy checks" step —
  those become wrong when the corresponding knob is off. Step 4 moves that
  step's body into a new **rendered** script
  `{{cookiecutter.project_slug}}/.github/scripts/deploy-check.sh` (the
  pattern only excludes `workflows/*`, so `scripts/` renders normally —
  `dependabot.yaml` in the same `.github/` dir already renders Jinja today).
- The Celery app is wired in three places beyond its own files:
  `src/config/__init__.py:5-7` (`from .celery import app as celery_app` +
  `__all__`), `src/config/settings/__init__.py:22`
  (`"components/celery.py",` in the include list), and
  `src/config/settings/components/sentry.py:3,24`
  (`CeleryIntegration(monitor_beat_tasks=True)`).
- `src/apps/core/tasks.py` contains exactly one task, `send_email`
  (a `@shared_task` wrapping `django.core.mail.send_mail`), tested by
  `tests/unit/core/tasks_test.py`. It is Celery-and-email coupled: it must
  exist only when `use_celery != "none"` **and** `email_provider != "none"`.
- `pyproject.toml` `[tool.pytest.ini_options]` `addopts` enforces
  `--cov-fail-under=100`; every knob combination must still reach 100%.
- The post-gen hook runs `git init` and `uv lock` in the baked project and
  prints next steps. `uv.lock` is generated per-bake (never stored in the
  template), so dependency-set variations per knob need no lock handling.
- Baked compose smoke conventions: prod healthchecks use
  `start_period`/`start_interval`; the api service publishes **no ports**
  (Traefik routes to it), which is why `FORWARDED_ALLOW_IPS: "*"` is safe.
- Repo style rules that apply here (from root `AGENTS.md`): alphabetize list
  items when order is not semantic (env vars, compose volumes, dependency
  lines, matrix entries); extended YAML block style; no empty *optional*
  values in `.env.example` (optional vars are commented examples; *required*
  vars may be empty like `RESEND_API_KEY=`); keep Docker images pinned.

Key current-state excerpts (working tree, 2026-07-05):

`src/config/__init__.py` (entire file):

```python
import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

from .celery import app as celery_app

__all__ = ("celery_app",)
```

`src/config/settings/__init__.py:14-32` — the include list ends with
`f"environments/{DJANGO_ENV}.py"`, followed by:

```python
if DJANGO_ENV == "prod":  # pragma: no cover
    settings_files.append("components/sentry.py")
```

`src/config/settings/components/apps.py:11-15` (third-party block):

```python
    # Third-party
    "django_celery_beat",
    "django_celery_results",
    "django_structlog",
    "extra_checks",
```

`pyproject.toml:13-31` dependencies (the knob-affected lines):

```toml
    "celery[redis]==5.6.3",
    "django-anymail[resend]==15.0",
    "django-celery-beat==2.9.0",
    "django-celery-results==2.6.0",
    "django-storages[s3]==1.14.6",
    "django-structlog[celery]==10.1.0",
    "sentry-sdk==2.64.0",
```

(pins may have moved by execution time — Dependabot; keep whatever pin is
live, only wrap lines in conditionals.)

`src/config/settings/environments/ci.py` (entire file):

```python
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True
CELERY_TASK_STORE_EAGER_RESULT = True
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
STORAGES["default"] = {  # noqa: F821  # ty: ignore[unresolved-reference]
    "BACKEND": "django.core.files.storage.InMemoryStorage",
}
```

`src/config/settings/environments/prod.py` knob-affected lines: `9`
(`ANYMAIL = {"RESEND_API_KEY": env("RESEND_API_KEY")}`), `13`
(`EMAIL_BACKEND = "anymail.backends.resend.EmailBackend"`), `27-41`
(`STORAGES["default"]` → S3Storage block).

`src/config/settings/components/celery.py:4`:
`CELERY_BEAT_SCHEDULER = "django_celery_beat.schedulers:DatabaseScheduler"`
(the only beat-specific line in that file; line 23 is
`DJANGO_STRUCTLOG_CELERY_ENABLED = True`).

`src/config/settings/components/sentry.py:1-6` and `19-29`:

```python
import sentry_sdk
from django.core.exceptions import ImproperlyConfigured
from sentry_sdk.integrations.celery import CeleryIntegration
...
sentry_sdk.init(
    dsn=SENTRY_DSN,
    release=project_version,
    environment="prod",
    send_default_pii=False,
    integrations=[CeleryIntegration(monitor_beat_tasks=True)],
    ...
)
```

`.env.example` (working tree — flat, sorted, comments first):

```text
# AWS_ACCESS_KEY_ID=
# AWS_S3_CUSTOM_DOMAIN=
# AWS_S3_ENDPOINT_URL=
# AWS_S3_REGION_NAME=
# AWS_SECRET_ACCESS_KEY=
# CONN_MAX_AGE=
ALLOWED_HOSTS=localhost,127.0.0.1
AWS_STORAGE_BUCKET_NAME=
CACHE_URL=rediscache://redis:6379/0
CELERY_BROKER_URL=redis://redis:6379/1
CELERY_WORKER_CONCURRENCY=2
CELERY_WORKER_MAX_TASKS_PER_CHILD=100
CSRF_TRUSTED_ORIGINS=https://example.com,https://www.example.com
DATABASE_URL=postgres://...@postgres:5432/...
DJANGO_ENV=dev
GUNICORN_GRACEFUL_TIMEOUT=30
GUNICORN_TIMEOUT=60
GUNICORN_WORKERS=5
LOG_LEVEL=INFO
POSTGRES_DB=... POSTGRES_PASSWORD=... POSTGRES_USER=...   (3 lines)
RESEND_API_KEY=
SECRET_KEY=django-insecure-change-me-in-production
SENTRY_DSN=
SENTRY_ENABLE_LOGS=False
SENTRY_PROFILE_SESSION_SAMPLE_RATE=1.0
SENTRY_TRACES_SAMPLE_RATE=1.0
TRAEFIK_ACME_EMAIL={{ cookiecutter.author_email }}
TRAEFIK_DOMAIN=example.com
```

`.docker/Dockerfile:30-39` (collectstatic RUN with dummy env, one var per
backslash-continued line): `AWS_STORAGE_BUCKET_NAME=$(uuidgen)`,
`RESEND_API_KEY=$(uuidgen)`,
`SENTRY_DSN=https://$(uuidgen | tr -d -)@sentry.example.com/1` are the
knob-affected lines.

`.docker/compose/prod.yaml` services: `api` (with 8 `traefik.*` labels, no
`ports:`), `celery-beat`, `celery-worker`, `postgres`, `redis`, `traefik`;
top-level volumes `postgres_data`, `redis_data`, `traefik_data`. `api` has
`environment: DJANGO_ENV: prod` and `FORWARDED_ALLOW_IPS: "*"`. The
`traefik_tls`-affected lines: the `traefik` service `command` starts with
three `--certificatesresolvers.letsencrypt.acme.*` flags (email from
`${TRAEFIK_ACME_EMAIL}`, httpchallenge on `web`, storage
`/letsencrypt/acme.json`), the api labels include
`traefik.http.routers.api-websecure.tls.certresolver=letsencrypt`, and the
`traefik` service mounts `traefik_data:/letsencrypt` (ACME state).
`.docker/compose/dev.yaml` services: `api` (ports `8000:8000`),
`celery-beat`, `celery-worker`, `postgres`, `redis`; volumes `media_data`,
`postgres_data`, `redis_data`; app services bind-mount `manage.py`, `src`,
and `media_data:/app/media`.

`.github/workflows/tests.yaml` (baked, unrendered) "Run deploy checks" step
sets these dummies inline before
`python manage.py check --deploy --fail-level=WARNING --tag=security`:
`ALLOWED_HOSTS`, `AWS_STORAGE_BUCKET_NAME`, `CACHE_URL`,
`CSRF_TRUSTED_ORIGINS`, `DATABASE_URL`, `DJANGO_ENV=prod`,
`RESEND_API_KEY`, `SECRET_KEY`, `SENTRY_DSN`.

Root `.github/workflows/ci.yaml` jobs: `bake` (matrix of 3 project names →
pytest + pre-commit on the baked project), `bake-invalid` (3 rejection
cases), `docker-build`, `docker-compose-smoke` (bakes default, seds
`SECRET_KEY`/`AWS_STORAGE_BUCKET_NAME`/`SENTRY_DSN`/`RESEND_API_KEY` into
`.env`, patches `pre_start` for the runner, boots prod compose, probes
health/ready in-container and through traefik, asserts `celery-beat`
running), `pre-commit`.

## Commands you will need

Run from the repo root unless stated. This machine prefixes shell commands
with `rtk` automatically via hook; type the plain command.

| Purpose | Command | Expected on success |
|---|---|---|
| Bake default | `uvx cookiecutter . --no-input -o /tmp/knobs/default` | exit 0; creates `/tmp/knobs/default/my-project` |
| Bake a variant | `uvx cookiecutter . --no-input -o /tmp/knobs/<name> <knob>=<value> ...` | exit 0 |
| Baked tests | `uv run pytest` (inside baked project) | all pass, coverage 100% |
| Baked lint | `git add -A && uv run pre-commit run --all-files` (inside baked project) | exit 0 |
| Root lint | `uv run pre-commit run --all-files` (repo root; or `uvx pre-commit run --all-files`) | exit 0 |
| Default-bake invariance | `diff -r --exclude=.git --exclude=uv.lock /tmp/knobs/baseline/my-project /tmp/knobs/default/my-project` | no output, exit 0 |
| Leftover-Jinja gate | `grep -rn "cookiecutter\|{%-" /tmp/knobs/<name>/<slug> --exclude-dir=.git` | no matches (exit 1) |

The **default-bake invariance gate** is the backbone of this plan: with all
knobs at defaults the rendered output must be byte-identical to the
pre-plan output (`uv.lock` excluded — it is regenerated per bake and only
needs to exist). Bake the baseline BEFORE your first edit (Step 0).

## Scope

**In scope** (the only files you may modify/create/delete):

- `cookiecutter.json`
- `hooks/post_gen_project.py`
- `.pre-commit-config.yaml` (root — only the three `files:` lines for
  post_gen)
- `.github/workflows/ci.yaml` (root)
- `README.md` (root — Variables table, What You Get)
- Everything under `{{cookiecutter.project_slug}}/` EXCEPT
  `.github/workflows/*`... which you may edit ONLY as described in Step 4
  (replacing the deploy-check step body with a script call — still no Jinja
  there), `skills-lock.json`, and `.ruff_cache/`
- `plans/README.md` (status row)

**Out of scope** (do NOT touch):

- `hooks/pre_gen_project.py` — cookiecutter validates choice variables
  natively; no new validation is needed (Step 0 verifies this).
- `{{cookiecutter.project_slug}}/.agents/*` and `skills-lock.json`.
- `plans/0*.md` other than this plan.
- Any new knob beyond the six listed (no license knob — plan 021's; no
  CORS/throttling — permanently rejected; no plain-HTTP-origin TLS mode —
  rejected, see decisions).
- Postgres/Redis/gunicorn/docs/admin surfaces — not knobs; Redis stays
  unconditionally (it backs the cache and `/api/ready` regardless of
  Celery).

## Git workflow

- Branch: `advisor/022-bake-time-feature-knobs` off `main`.
- Conventional commits, one per step or logical unit, e.g.
  `feat: add bake-time feature knobs to cookiecutter context` (matches
  existing history: `feat: gate api docs behind staff`,
  `ci: smoke test baked prod compose stack`).
- Do NOT push or open a PR unless the operator instructed it.

## Jinja conventions for this plan

- Knob tests: `{% if cookiecutter.use_celery != "none" %}`,
  `{% if cookiecutter.email_provider == "resend" %}`,
  `{% if cookiecutter.use_sentry == "yes" %}`, etc. Values are plain
  strings — never rely on Jinja truthiness.
- For conditional **lines/blocks**, put each tag on its own line with a
  leading whitespace-strip marker and nothing else on that line:

  ```text
  line A
  {%- if cookiecutter.use_celery != "none" %}
  line B
  {%- endif %}
  line C
  ```

  renders as `A\nB\nC` when true and `A\nC` when false. Use `{%- elif %}` /
  `{%- else %}` the same way. Do NOT use trailing `-%}` markers — the
  leading-marker-only pattern above is what keeps the default bake
  byte-identical. The invariance gate will catch any whitespace mistake.
- Whole files that only exist for a knob are handled by **post-gen
  deletion** (Step 2), not by emptying them with Jinja.

## Steps

### Step 0: Baseline and preconditions

1. Run the drift check from the header (plan 018 committed; excerpts match).
2. Bake the baseline: `uvx cookiecutter . --no-input -o /tmp/knobs/baseline`
   → `/tmp/knobs/baseline/my-project` exists.
3. Verify cookiecutter's native choice validation (this plan relies on it):
   temporarily confirm with the current template that an unknown variable is
   an error and, after Step 1, that an invalid choice value fails. (Nothing
   to change here; awareness only.)

**Verify**: baseline bake exits 0; `cd /tmp/knobs/baseline/my-project && uv sync --locked && uv run pytest` → all pass, 100% coverage.

### Step 1: Define the knobs in `cookiecutter.json`

Insert after `"github_username"` and before `_copy_without_render` (choice
variables default to their FIRST element — order below is load-bearing):

```json
    "use_celery": ["worker+beat", "worker", "none"],
    "email_provider": ["resend", "smtp", "none"],
    "use_sentry": ["yes", "no"],
    "use_s3_media": ["yes", "no"],
    "use_traefik": ["yes", "no"],
    "traefik_tls": ["letsencrypt", "external"],
```

**Verify**:
`uvx cookiecutter . --no-input -o /tmp/knobs/s1 && diff -r --exclude=.git --exclude=uv.lock /tmp/knobs/baseline/my-project /tmp/knobs/s1/my-project`
→ no output.
`uvx cookiecutter . --no-input -o /tmp/knobs/s1bad use_celery=bogus` →
non-zero exit with a "not a valid choice"-style error (this is what the new
CI rejection case in Step 9 asserts). If it exits 0, STOP — the choice-
validation assumption is false.

### Step 2: Conditional file deletion in the post-gen hook (+ root lint adjustment)

`hooks/post_gen_project.py` is currently plain Python. Add rendered knob
constants at the top (same `tojson` pattern as `pre_gen_project.py`) and a
deletion pass that runs BEFORE `git init`:

```python
from pathlib import Path

EMAIL_PROVIDER = {{ cookiecutter.email_provider | tojson }}
TRAEFIK_TLS = {{ cookiecutter.traefik_tls | tojson }}
USE_CELERY = {{ cookiecutter.use_celery | tojson }}
USE_S3_MEDIA = {{ cookiecutter.use_s3_media | tojson }}
USE_SENTRY = {{ cookiecutter.use_sentry | tojson }}
USE_TRAEFIK = {{ cookiecutter.use_traefik | tojson }}

REMOVED_PATHS = [
    *(
        [
            ".docker/scripts/celery-beat.sh",
            ".docker/scripts/celery-worker.sh",
            "src/config/celery.py",
            "src/config/settings/components/celery.py",
            "tests/unit/config/celery_test.py",
        ]
        if USE_CELERY == "none"
        else []
    ),
    *([".docker/scripts/celery-beat.sh"] if USE_CELERY == "worker" else []),
    *(
        ["src/apps/core/tasks.py", "tests/unit/core/tasks_test.py"]
        if USE_CELERY == "none" or EMAIL_PROVIDER == "none"
        else []
    ),
    *(
        ["src/config/settings/components/sentry.py"]
        if USE_SENTRY == "no"
        else []
    ),
    *(
        [".docker/traefik-dynamic.yaml"]
        if not (USE_TRAEFIK == "yes" and TRAEFIK_TLS == "external")
        else []
    ),
]
```

In `main()`, before the git-init block:

```python
    for removed_path in REMOVED_PATHS:
        Path(removed_path).unlink()
```

(`unlink()` without `missing_ok` — a missing file means the template and
hook have drifted apart, and the bake SHOULD fail loudly.)

Note `USE_S3_MEDIA` is defined for symmetry but currently unused by
deletions (S3 is settings-only) — only define constants the hook actually
consumes if that bothers rendered-output lint (nothing lints the rendered
hook, so keeping it is fine too). `.docker/traefik-dynamic.yaml` is a new
template file created in Step 7; until that step lands, the deletion entry
will fail on non-external bakes — either add this REMOVED_PATHS entry
during Step 7, or create the file in this step. Prefer creating the file
now (its content is fixed, see Step 7.4) so the hook stays complete.

Because the file now contains Jinja, remove `hooks/post_gen_project.py`
from root `.pre-commit-config.yaml`: delete the three
`files: ^hooks/post_gen_project\.py$` lines together with their now-empty
hook entries' scoping — concretely, drop the `check-ast` entry's `files:`
restriction line *and* the entry itself... **Precisely**: delete these
three hook configurations' `files` lines AND the hooks themselves where the
hook exists only for that file:

- under `pre-commit-hooks`: remove the entire `- id: check-ast` entry (its
  only target was post_gen).
- under `ruff-pre-commit`: remove the entire `ruff-check` and `ruff-format`
  entries (their only targets were post_gen).

This mirrors how `pre_gen_project.py` (Jinja since plan 011) is already
excluded from Python linting. Record the trade-off in the commit message:
hook files are now exercised by the CI bake jobs instead of static lint.

**Verify**:
1. `uvx pre-commit run --all-files` (root) → exit 0.
2. Default bake → invariance gate passes (the only file deleted at
   defaults is `.docker/traefik-dynamic.yaml`, which does not exist in the
   baseline either, so the diff stays empty).
3. `uvx cookiecutter . --no-input -o /tmp/knobs/s2 use_celery=none email_provider=none use_sentry=no`
   → bake succeeds; then
   `ls /tmp/knobs/s2/my-project/src/config/celery.py` → No such file;
   `ls /tmp/knobs/s2/my-project/src/apps/core/tasks.py` → No such file;
   `ls /tmp/knobs/s2/my-project/src/config/settings/components/sentry.py` →
   No such file. (This bake's pytest will FAIL until Steps 3-5 land — that
   is expected; do not run it yet.)

### Step 3: `use_celery` knob — every touch point

Apply the line-conditional Jinja pattern. Conditions: `worker+beat` ≙
`cookiecutter.use_celery == "worker+beat"`; "celery on" ≙
`cookiecutter.use_celery != "none"`.

1. `src/config/__init__.py` — wrap lines 5-7 (import + `__all__`) in
   "celery on". When none, the file is just the `os` import and `setdefault`
   line.
2. `src/config/settings/__init__.py` — wrap `"components/celery.py",` in
   "celery on".
3. `src/config/settings/components/apps.py` — wrap `"django_celery_beat",`
   in worker+beat; wrap `"django_celery_results",` in "celery on".
4. `src/config/settings/components/celery.py` — wrap the
   `CELERY_BEAT_SCHEDULER` line in worker+beat. (Whole file is deleted when
   none — Step 2.)
5. `src/config/settings/environments/ci.py` — wrap the three
   `CELERY_TASK_*` lines in "celery on".
6. `pyproject.toml` dependencies — wrap `celery[redis]` and
   `django-celery-results` lines in "celery on"; `django-celery-beat` in
   worker+beat; replace the `django-structlog[celery]` line with a
   conditional pair:

   ```text
   {%- if cookiecutter.use_celery != "none" %}
       "django-structlog[celery]==10.1.0",
   {%- else %}
       "django-structlog==10.1.0",
   {%- endif %}
   ```

   (use the live pin, not necessarily `10.1.0`).
7. `.env.example` — wrap `CELERY_BROKER_URL`, `CELERY_WORKER_CONCURRENCY`,
   `CELERY_WORKER_MAX_TASKS_PER_CHILD` in "celery on". If plan 020 has
   restructured this file into blocks, put the conditionals around the same
   three vars wherever they now live and keep per-block alphabetical order.
8. `.docker/compose/dev.yaml` and `prod.yaml` — wrap the whole
   `celery-worker:` service in "celery on" and the whole `celery-beat:`
   service in worker+beat (each service block from its name key through its
   last line). Indentation: keep the `{%- if %}` tags at column 0 on their
   own lines.
9. `src/config/settings/components/sentry.py` — handled in Step 5 (the
   CeleryIntegration matrix); skip here.
10. Baked `README.md` and `AGENTS.md` — handled in Step 8.

Also note: `components/celery.py`'s `DJANGO_STRUCTLOG_CELERY_ENABLED = True`
needs no conditional (file exists only when celery is on).

**Verify** (three bakes):
1. Default → invariance gate.
2. `uvx cookiecutter . --no-input -o /tmp/knobs/worker use_celery=worker`
   → inside it: `uv sync --locked && uv run pytest` → pass, 100%;
   `git add -A && uv run pre-commit run --all-files` → exit 0;
   `grep -rn "celery_beat\|celery-beat\|BEAT_SCHEDULER" --include="*.py" --include="*.yaml" --include="*.toml" .`
   → no matches in `src/`, `pyproject.toml`, `.docker/`.
3. `uvx cookiecutter . --no-input -o /tmp/knobs/nocelery use_celery=none`
   → `uv sync --locked && uv run pytest` → pass, 100% (tasks.py and
   celery tests are gone via Step 2); leftover-Jinja gate passes;
   `grep -rni "celery" src/ pyproject.toml .docker/compose/` → no matches.
   (README still mentions Celery until Step 8 — grep only the paths above.)

### Step 4: `email_provider` knob

1. `src/config/settings/environments/prod.py`:

   ```text
   {%- if cookiecutter.email_provider == "resend" %}
   ANYMAIL = {"RESEND_API_KEY": env("RESEND_API_KEY")}
   {%- endif %}
   ```

   and for the backend line (keep the file's alphabetical constant order —
   the smtp `EMAIL_*` block sits where `EMAIL_BACKEND` sits today):

   ```text
   {%- if cookiecutter.email_provider == "resend" %}
   EMAIL_BACKEND = "anymail.backends.resend.EmailBackend"
   {%- elif cookiecutter.email_provider == "smtp" %}
   EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
   EMAIL_HOST = env("EMAIL_HOST")
   EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", default="")
   EMAIL_HOST_USER = env("EMAIL_HOST_USER", default="")
   EMAIL_PORT = env.int("EMAIL_PORT", default=587)
   EMAIL_USE_TLS = env.bool("EMAIL_USE_TLS", default=True)
   {%- endif %}
   ```

   `EMAIL_HOST` has no default — it is boot-required in prod for smtp,
   matching the `RESEND_API_KEY`/`SENTRY_DSN` required-var pattern. When
   `none`, prod gets no EMAIL_* override at all (the console backend from
   `components/email.py` stays, and nothing in the codebase sends mail).
2. `src/config/settings/environments/ci.py` — wrap the locmem
   `EMAIL_BACKEND` line in `email_provider != "none"`.
3. `components/email.py` — unchanged, unconditional (console backend is the
   safe dev default in every variant).
4. `pyproject.toml` — wrap the `django-anymail[resend]` line in
   `email_provider == "resend"`.
5. `.env.example` — wrap `RESEND_API_KEY=` in resend. Add an smtp block in
   alphabetical position (E before G):

   ```text
   {%- if cookiecutter.email_provider == "smtp" %}
   # EMAIL_HOST_PASSWORD=
   # EMAIL_HOST_USER=
   # EMAIL_PORT=
   # EMAIL_USE_TLS=
   EMAIL_HOST=
   {%- endif %}
   ```

   Commented lines go in the leading comment block with the other `#`
   entries (match how `# AWS_*` optional vars are handled); `EMAIL_HOST=`
   (required, empty) goes in the main list between `DJANGO_ENV` and
   `GUNICORN_GRACEFUL_TIMEOUT`.
6. `.docker/Dockerfile` collectstatic RUN — make the `RESEND_API_KEY=...`
   continuation line conditional on resend and add
   `EMAIL_HOST=smtp.example.com \` for smtp. Template it as:

   ```text
   RUN ALLOWED_HOSTS=localhost \
       AWS_STORAGE_BUCKET_NAME=$(uuidgen) \
       CACHE_URL=locmemcache:// \
       CSRF_TRUSTED_ORIGINS=https://localhost \
       DATABASE_URL=sqlite:///:memory: \
       DJANGO_ENV=prod \
   {%- if cookiecutter.email_provider == "smtp" %}
       EMAIL_HOST=smtp.example.com \
   {%- endif %}
   {%- if cookiecutter.email_provider == "resend" %}
       RESEND_API_KEY=$(uuidgen) \
   {%- endif %}
       SECRET_KEY=$(uuidgen)$(uuidgen) \
   ```

   (Sentry and AWS lines get the same treatment in Steps 5-6. Every
   non-final line keeps its trailing backslash; the tag lines carry none.)
7. **Deploy-check script** — create
   `{{cookiecutter.project_slug}}/.github/scripts/deploy-check.sh`
   (mode 755 — `chmod +x` it; cookiecutter preserves the executable bit,
   which is how `.docker/scripts/*.sh` work today):

   ```sh
   #!/bin/sh
   set -eu

   ALLOWED_HOSTS=localhost \
   {%- if cookiecutter.use_s3_media == "yes" %}
   AWS_STORAGE_BUCKET_NAME=$(uuidgen) \
   {%- endif %}
   CACHE_URL=locmemcache:// \
   CSRF_TRUSTED_ORIGINS=https://localhost \
   DATABASE_URL=sqlite:///:memory: \
   DJANGO_ENV=prod \
   {%- if cookiecutter.email_provider == "smtp" %}
   EMAIL_HOST=smtp.example.com \
   {%- endif %}
   {%- if cookiecutter.email_provider == "resend" %}
   RESEND_API_KEY=$(uuidgen) \
   {%- endif %}
   SECRET_KEY=$(uuidgen)$(uuidgen) \
   {%- if cookiecutter.use_sentry == "yes" %}
   SENTRY_DSN=https://$(uuidgen | tr -d -)@sentry.example.com/1 \
   {%- endif %}
   uv run --group=ci --locked --no-default-groups \
       python manage.py check --deploy --fail-level=WARNING --tag=security
   ```

   Then edit `{{cookiecutter.project_slug}}/.github/workflows/tests.yaml`
   (NO Jinja — it is copied without render): replace the entire multi-line
   `run:` block of "Run deploy checks" with:

   ```yaml
       - name: Run deploy checks
         run: ./.github/scripts/deploy-check.sh
   ```

   The baked project's pre-commit may lint shell scripts — model the script
   on `.docker/scripts/gunicorn.sh` style and let the baked
   `pre-commit run --all-files` verification catch any formatting hook
   complaints.
8. `tasks.py` / `tasks_test.py` deletion for `email_provider == "none"` is
   already wired in Step 2.

**Verify**:
1. Default → invariance gate **fails on exactly two files**:
   `.github/scripts/deploy-check.sh` (new) and
   `.github/workflows/tests.yaml` (step body swap). That is the ONLY
   intentional default-bake diff in this plan. Inspect it, then refresh the
   baseline: re-bake `/tmp/knobs/baseline` from the current tree, and use
   the refreshed baseline for every later invariance check.
2. In the fresh default bake: `uv run pytest` → pass;
   `git add -A && uv run pre-commit run --all-files` → exit 0; and run
   `./.github/scripts/deploy-check.sh` → exit 0 (this proves the moved
   deploy check still passes).
3. `uvx cookiecutter . --no-input -o /tmp/knobs/smtp email_provider=smtp` →
   pytest + pre-commit + `./.github/scripts/deploy-check.sh` all pass;
   `grep -rni "resend\|anymail" src/ pyproject.toml .env.example .docker/ .github/scripts/`
   → no matches.
4. `uvx cookiecutter . --no-input -o /tmp/knobs/noemail email_provider=none`
   → pytest passes (tasks test gone), 100% coverage;
   `grep -rni "resend\|anymail\|EMAIL_HOST" src/ pyproject.toml .env.example .docker/ .github/scripts/`
   → the only hits are the console/locmem backends... precisely: expect
   `components/email.py` (console) and NO `ci.py` locmem line, NO prod
   EMAIL lines.
5. Cross-term: `uvx cookiecutter . --no-input -o /tmp/knobs/xterm use_celery=none email_provider=resend`
   → pytest passes; `src/apps/core/tasks.py` absent; prod.py still has the
   ANYMAIL/resend lines (a project can send synchronously with
   `django.core.mail.send_mail`).

### Step 5: `use_sentry` knob

Condition: `cookiecutter.use_sentry == "yes"`; interacts with celery.

1. `src/config/settings/__init__.py` — wrap the whole
   `if DJANGO_ENV == "prod": ... append("components/sentry.py")` block in
   the sentry condition.
2. `src/config/settings/components/sentry.py` (file deleted when knob off —
   Step 2; these conditionals only shape the celery interaction):
   - import line:

     ```text
     {%- if cookiecutter.use_celery != "none" %}
     from sentry_sdk.integrations.celery import CeleryIntegration
     {%- endif %}
     ```

   - `integrations` kwarg inside `sentry_sdk.init(` (keep Sentry's
     documented kwarg order — the file's existing order):

     ```text
     {%- if cookiecutter.use_celery == "worker+beat" %}
         integrations=[CeleryIntegration(monitor_beat_tasks=True)],
     {%- elif cookiecutter.use_celery == "worker" %}
         integrations=[CeleryIntegration()],
     {%- endif %}
     ```

     When celery is none, no `integrations` kwarg is rendered (sentry-sdk's
     default auto-enabling is fine and there is nothing to configure).
3. `pyproject.toml` — wrap the `sentry-sdk` dependency line in sentry;
   also wrap the `"src/config/settings/components/sentry.py",` entry in
   `[tool.coverage.run] omit` in sentry (a stale omit path is harmless but
   untidy, and the invariance gate keeps the default identical).
4. `.env.example` — wrap the four `SENTRY_*` lines in sentry.
5. `.docker/Dockerfile` — wrap the `SENTRY_DSN=...` collectstatic line in
   sentry (same pattern as Step 4.6).
6. `.github/scripts/deploy-check.sh` — already conditional (Step 4.7).
7. The `use_sentry=yes` path must stay EXACTLY as strict as today:
   `sentry.py` still raises `ImproperlyConfigured` when `SENTRY_DSN` is
   empty in prod. Do not weaken this.

**Verify**:
1. Default → invariance gate (against refreshed baseline).
2. `uvx cookiecutter . --no-input -o /tmp/knobs/nosentry use_sentry=no` →
   pytest + pre-commit + deploy-check script pass;
   `grep -rni "sentry" src/ pyproject.toml .env.example .docker/ .github/scripts/`
   → no matches.
3. `uvx cookiecutter . --no-input -o /tmp/knobs/nosentry-nocelery use_sentry=yes use_celery=none`
   → bake OK and `grep -n "CeleryIntegration\|integrations=" src/config/settings/components/sentry.py`
   → no matches (init call has no integrations kwarg).

### Step 6: `use_s3_media` knob

Condition: `cookiecutter.use_s3_media == "yes"`.

1. `src/config/settings/environments/prod.py` — wrap the whole
   `STORAGES["default"] = {...S3Storage...}` block (lines 27-41 today) in
   s3. When off, prod media falls back to `components/storage.py`'s
   `FileSystemStorage` at `/app/media`. The whitenoise `staticfiles` block
   below it stays unconditional.
2. `pyproject.toml` — wrap the `django-storages[s3]` line in s3.
3. `.env.example` — wrap the five commented `# AWS_*` lines and the
   `AWS_STORAGE_BUCKET_NAME=` line in s3.
4. `.docker/Dockerfile` — wrap the `AWS_STORAGE_BUCKET_NAME=$(uuidgen)`
   collectstatic line in s3.
5. `.docker/compose/prod.yaml` — when s3 is OFF, prod needs the media
   volume dev already has: inside `{%- if cookiecutter.use_s3_media == "no" %}`,
   add `media_data:/app/media` to the `api` service (new `volumes:` key —
   `api` currently has none in prod) and to `celery-worker`'s service (only
   when that service is rendered, i.e. nest inside its "celery on" block —
   a `volumes:` list with `media_data:/app/media`), and add `media_data:`
   to the top-level `volumes:` in alphabetical position (before
   `postgres_data:`).
6. `.github/scripts/deploy-check.sh` — already conditional (Step 4.7).

**Verify**:
1. Default → invariance gate.
2. `uvx cookiecutter . --no-input -o /tmp/knobs/nos3 use_s3_media=no` →
   pytest + pre-commit + deploy-check pass;
   `grep -rni "aws\|django-storages\|S3Storage" src/ pyproject.toml .env.example .docker/ .github/scripts/`
   → no matches; `grep -n "media_data" .docker/compose/prod.yaml` → matches
   in api service, celery-worker service, and top-level volumes.
3. In the SAME nos3 bake, `docker compose -f .docker/compose/prod.yaml config`
   → exits 0 (compose file parses; ignore warnings about missing env
   values, or pre-create `.env` from `.env.example` first).

### Step 7: `use_traefik` + `traefik_tls` knobs

Conditions: `cookiecutter.use_traefik == "yes"`; within the traefik path,
`cookiecutter.traefik_tls == "letsencrypt"` vs `"external"`. Default
(yes + letsencrypt) output must be byte-identical to plan 018's committed
state. `traefik_tls` has no effect when `use_traefik=no` (all its
conditional sites live inside the traefik-only blocks; the dynamic-config
file is deleted by the Step 2 hook).

1. `.docker/compose/prod.yaml`:
   - Wrap the 8-line `labels:` block of the `api` service in traefik.
   - When traefik is OFF, the api service must be reachable: add (inside
     `{%- if cookiecutter.use_traefik == "no" %}`) to the `api` service:

     ```yaml
     ports:
       - "127.0.0.1:8000:8000"
     ```

     Loopback-only publishing: the operator's own ingress (nginx, caddy,
     cloud LB agent) proxies to it. Keep
     `FORWARDED_ALLOW_IPS: "*"` in BOTH variants — with a loopback bind the
     traffic reaching gunicorn comes from the docker-proxy's bridge address
     (not 127.0.0.1 from the container's viewpoint), so narrowing it breaks
     `SECURE_PROXY_SSL_HEADER` handling and causes redirect loops. The
     trust boundary is the loopback bind plus the operator's proxy
     overwriting `X-Forwarded-Proto` — Step 8 documents this contract.
   - Wrap the whole `traefik:` service in traefik.
   - Wrap `traefik_data:` (top-level volumes) in traefik.
2. `.env.example` — wrap `TRAEFIK_ACME_EMAIL` and `TRAEFIK_DOMAIN` in
   traefik.
3. Deploy story: docker-rollout only works because Traefik health-gates and
   drains between overlapping containers, and a published host port cannot
   overlap two containers. So when traefik is OFF, the baked README's
   deploy instructions must NOT mention `docker rollout` — Step 8 renders a
   plain `docker compose ... build / run migrations / up -d` flow with a
   brief-downtime warning instead. No compose changes needed for this
   beyond the ports block.
4. **`traefik_tls` sub-knob** (all sites below are inside the
   traefik-only blocks; condition
   `{%- if cookiecutter.traefik_tls == "letsencrypt" %}` /
   `{%- else %}`):
   - Create the new template file
     `{{cookiecutter.project_slug}}/.docker/traefik-dynamic.yaml` (static
     content, no Jinja; deleted by the Step 2 hook unless
     traefik+external):

     ```yaml
     tls:
       certificates:
         - certFile: /etc/traefik/certs/cert.pem
           keyFile: /etc/traefik/certs/key.pem
       stores:
         default:
           defaultCertificate:
             certFile: /etc/traefik/certs/cert.pem
             keyFile: /etc/traefik/certs/key.pem
     ```

   - `prod.yaml` `traefik` service `command`: the three
     `--certificatesresolvers.letsencrypt.acme.*` flags → letsencrypt
     branch; the external branch instead adds
     `--providers.file.filename=/etc/traefik/dynamic/traefik-dynamic.yaml`
     (keep the flag list alphabetized — it sorts after
     `--providers.docker.exposedbydefault`).
   - `prod.yaml` `traefik` service `volumes`: keep the docker.sock mount in
     both branches; `traefik_data:/letsencrypt` → letsencrypt branch; the
     external branch instead mounts (compose paths are relative to
     `.docker/compose/`):

     ```yaml
     - ../certs:/etc/traefik/certs:ro
     - ../traefik-dynamic.yaml:/etc/traefik/dynamic/traefik-dynamic.yaml:ro
     ```

   - `prod.yaml` top-level `traefik_data:` volume → letsencrypt only.
   - `prod.yaml` api label
     `traefik.http.routers.api-websecure.tls.certresolver=letsencrypt` →
     letsencrypt branch; external branch renders
     `traefik.http.routers.api-websecure.tls=true` instead (TLS enabled on
     the router, cert served from the file provider's default store).
   - `.env.example`: `TRAEFIK_ACME_EMAIL` line → letsencrypt only.
     `TRAEFIK_DOMAIN` stays in BOTH modes (the websecure router's Host
     rule uses it).
   - `.gitignore` (baked): append a conditional block (operators drop
     their PEM pair here; it must never be committed):

     ```text
     {%- if cookiecutter.use_traefik == "yes" and cookiecutter.traefik_tls == "external" %}

     # TLS origin certificate (operator-provided)
     .docker/certs/
     {%- endif %}
     ```

   - Documentation of the external flow (cert acquisition, file placement,
     Cloudflare specifics) is Step 8's job.

**Verify**:
1. Default → invariance gate.
2. `uvx cookiecutter . --no-input -o /tmp/knobs/notraefik use_traefik=no` →
   pre-commit passes;
   `grep -rni "traefik" .docker/ .env.example src/` → no matches;
   `grep -n "127.0.0.1:8000:8000" .docker/compose/prod.yaml` → one match;
   `ls .docker/traefik-dynamic.yaml` → No such file;
   `docker compose -f .docker/compose/prod.yaml config` → exit 0.
3. `uvx cookiecutter . --no-input -o /tmp/knobs/exttls traefik_tls=external`
   → pre-commit passes;
   `grep -rn "letsencrypt\|acme\|ACME" .docker/ .env.example` → no matches;
   `grep -n "providers.file.filename" .docker/compose/prod.yaml` → one
   match; `test -f .docker/traefik-dynamic.yaml` → exit 0;
   `grep -n ".docker/certs/" .gitignore` → one match;
   `mkdir -p .docker/certs && docker compose -f .docker/compose/prod.yaml config`
   → exit 0.
4. `uvx cookiecutter . --no-input -o /tmp/knobs/noconflict use_traefik=no traefik_tls=external`
   → bake succeeds, `ls .docker/traefik-dynamic.yaml` → No such file, and
   `grep -rni "traefik" .docker/ .env.example` → no matches (the sub-knob
   is inert without traefik).

### Step 8: Documentation — baked README/AGENTS.md, root README

Baked `{{cookiecutter.project_slug}}/README.md` (largest conditional
surface; work section by section against the live file):

- Intro tech list (lines 8-10): make "Redis, Celery, django-celery-beat,
  django-celery-results" and "django-storages" conditional fragments. Keep
  Redis always (cache). Simplest robust form: three variants of the
  sentence via `{%- if %}` blocks rather than inline expressions.
- Architecture bullets: "Celery app" mention in the `src/config/` line
  (celery on); prod overlay description "private S3-compatible storage"
  (s3).
- Quickstart: "When the API is healthy, the Celery services start" (celery
  on).
- Local Setup: `CELERY_*` bullet (celery on); the services list sentence
  ("starts `api`, `celery-beat`, `celery-worker`, `postgres`, and `redis`")
  needs per-variant rendering; the email paragraph (lines 92-95) has three
  variants — resend (current text), smtp ("production sends through your
  SMTP relay; set `EMAIL_HOST`... send with `django.core.mail.send_mail` or
  `apps.core.tasks.send_email.delay(...)`" — the `.delay` mention only when
  celery is on), none (drop the paragraph); the beat paragraph (lines
  97-100) only for worker+beat; `AWS_STORAGE_BUCKET_NAME` bullet (s3).
- Production: Traefik paragraphs (lines 142-152), `TRAEFIK_*` mentions, the
  docker-rollout install + deploy blocks (lines 172-196) → traefik only;
  when traefik is off, render instead a short "Bring your own ingress"
  paragraph: api listens on `127.0.0.1:8000`, your proxy MUST overwrite
  `X-Forwarded-Proto` from clients and forward `Host`; deploys are
  `git pull && docker compose --env-file .env -f .docker/compose/prod.yaml build && docker compose --env-file .env -f .docker/compose/prod.yaml run --rm --no-deps api /app/.docker/scripts/migrations.sh && docker compose --env-file .env -f .docker/compose/prod.yaml up -d`
  with a note that container replacement has brief downtime (rollout
  requires the bundled Traefik). Within the traefik=yes path, the TLS
  sentences split on `traefik_tls`: the Let's Encrypt/ACME sentences
  (`TRAEFIK_ACME_EMAIL`, automatic issuance and renewal) → letsencrypt
  branch; the external branch renders instead a paragraph saying: Traefik
  serves TLS from `.docker/certs/cert.pem` + `.docker/certs/key.pem`
  (gitignored — create the directory on the host and place any PEM
  cert/key pair there: a Cloudflare Origin CA certificate is the worked
  example — set the zone's SSL mode to "Full (strict)", validity up to 15
  years — but a purchased cert, corporate CA, or externally-managed ACME
  cert works identically); restart the `traefik` service after replacing
  the files; renewal is the operator's (or the issuing service's)
  responsibility. Sentry paragraph (lines 164-168) → sentry
  only. Redis broker sentences ("Cache and broker share one Redis instance
  on databases 0 and 1", acks_late note) → celery on; keep the cache-Redis
  sentences always. The `celery-worker`/`celery-beat` convergence sentence
  (line 195-196) → per celery variant.
- Testing: "eager Celery tasks" mention (celery on).

Baked `{{cookiecutter.project_slug}}/AGENTS.md`: line 10 ("and Celery
commands"), line 18 (tech list: Celery, django-storages), lines 56-62
(sentry_sdk.init guidance → sentry), line 67 (Celery results guidance →
celery on), line 110 (`celery -A config` rule → celery on). Wrap each in
the matching condition; keep everything else untouched.

Root `README.md`:

- "What You Get": change "Celery and Redis included by default" to a line
  describing the knob (e.g. "Optional Celery (worker, or worker + beat),
  chosen at bake time"); add/adjust bullets for optional email provider
  (Resend API / SMTP / none), optional Sentry, optional S3 media storage,
  optional Traefik ingress. Keep alphabetical bullet order.
- "Variables" table: add six rows (name, default, one-line description):
  `use_celery` default `worker+beat`, `email_provider` default `resend`,
  `use_sentry` default `yes`, `use_s3_media` default `yes`, `use_traefik`
  default `yes`, `traefik_tls` default `letsencrypt` ("`external` serves an
  operator-provided cert instead of running ACME — any PEM pair works,
  e.g. Cloudflare Origin CA; ignored when `use_traefik=no`"). Note under
  the table: defaults reproduce the historical full-stack output.

**Verify**:
1. Default → invariance gate (README/AGENTS.md conditionals must collapse
   to today's exact text).
2. Re-bake `/tmp/knobs/nocelery` (`use_celery=none`):
   `grep -rni "celery" /tmp/knobs/nocelery/my-project --exclude-dir=.git --exclude-dir=.agents`
   → no matches anywhere now (docs included).
3. Re-bake `/tmp/knobs/notraefik`: `grep -rni "traefik\|rollout" /tmp/knobs/notraefik/my-project --exclude-dir=.git --exclude-dir=.agents`
   → no matches; README contains "Bring your own ingress".
4. Root `uvx pre-commit run --all-files` → exit 0 (markdownlint on root
   README).

### Step 9: Root CI — exercise the knob matrix

Edit root `.github/workflows/ci.yaml`:

1. `bake` job matrix — add three entries (each entry needs the fields the
   job uses: a display name, `extra-args`, `slug`):
   - `minimal`: `extra-args: use_celery=none email_provider=none use_sentry=no use_s3_media=no use_traefik=no`, slug `my-project`
     (project_name defaults) — use a distinct `-o` dir per matrix entry or
     distinct project_name; the job already bakes into `/tmp/bake`, which is
     per-runner, so the default slug is fine.
   - `worker-only`: `extra-args: use_celery=worker`, slug `my-project`.
   - `smtp`: `extra-args: email_provider=smtp`, slug `my-project`.
   - `external-tls`: `extra-args: traefik_tls=external`, slug `my-project`.
   Rename the matrix key or entries as needed so names stay readable
   (`name: Bake ${{ matrix.project_name }}` today — add a `case` field if
   cleaner). Keep the existing three project-name entries unchanged.
2. `bake-invalid` job — add one case:
   `- case: bad-knob` / `extra-args: use_celery=bogus`.
3. `docker-compose-smoke` — convert to a two-entry matrix `variant:
   [default, minimal]`:
   - `default`: exactly today's steps (env-prep seds for `SECRET_KEY`,
     `AWS_STORAGE_BUCKET_NAME`, `SENTRY_DSN`, `RESEND_API_KEY`; traefik
     probes; `celery-beat` running assertion).
   - `minimal`: bake with the minimal extra-args; env-prep seds ONLY
     `SECRET_KEY`; keep the `pre_start` runner patch step (unchanged — the
     api service block still has `pre_start` in every variant); probe
     in-container `http://127.0.0.1:8000/api/health` and `/api/ready` as
     today, and replace the "Probe through traefik" step with host probes
     of `http://127.0.0.1:8000/api/health` and `/api/ready` (published
     loopback port); replace the `celery-beat` assertion with
     `test -z "$(docker compose --env-file .env -f .docker/compose/prod.yaml ps --status=exited -q)"`
     only.
   Implement the per-variant differences with `if:` conditions on steps or
   per-variant matrix fields (e.g. `extra-args`, `probe-url`) — actionlint
   must pass.
4. Do NOT touch the `docker-build` job (default bake covers it; minimal is
   built by the smoke variant's `--build`).

**Verify**:
1. Root `uvx pre-commit run --all-files` → exit 0 (actionlint,
   check-github-workflows, yamllint on ci.yaml).
2. Local rehearsal of the minimal smoke variant if Docker is available
   (optional but strongly preferred): from `/tmp/knobs/minimal-smoke` bake
   with minimal args, `cp .env.example .env`, sed SECRET_KEY, apply the
   same pre_start patch, `docker compose --env-file .env -f .docker/compose/prod.yaml up -d --build --wait --wait-timeout 300`,
   `curl -fsS http://127.0.0.1:8000/api/health`, then `down -v`. If Docker
   is unavailable in your environment, note it in the final report — CI
   will exercise it.

### Step 10: Full verification sweep + index update

Bake and fully verify every variant in one pass (fresh `-o` dirs):

| # | extra-args | pytest | pre-commit | deploy-check.sh | leftover-Jinja grep |
|---|---|---|---|---|---|
| 1 | (none — default) | ✔ | ✔ | ✔ | ✔ |
| 2 | `use_celery=none email_provider=none use_sentry=no use_s3_media=no use_traefik=no` | ✔ | ✔ | ✔ | ✔ |
| 3 | `use_celery=worker` | ✔ | ✔ | ✔ | ✔ |
| 4 | `email_provider=smtp` | ✔ | ✔ | ✔ | ✔ |
| 5 | `use_celery=none email_provider=resend` | ✔ | ✔ | ✔ | ✔ |
| 6 | `traefik_tls=external` | ✔ | ✔ | ✔ | ✔ |

For each: `uv sync --locked`, `uv run pytest` (100% coverage),
`git add -A && uv run pre-commit run --all-files`,
`./.github/scripts/deploy-check.sh`, and
`grep -rn "cookiecutter\|{%-" . --exclude-dir=.git --exclude-dir=.agents`
→ no matches. Variant 1 additionally passes the invariance gate against the
refreshed (post-Step-4) baseline. Variant 6 additionally passes
`mkdir -p .docker/certs && docker compose -f .docker/compose/prod.yaml config`
(exit 0) and the no-ACME grep from Step 7's verify.

Then update `plans/README.md`: set plan 022's status, and if you changed
anything the index's dependency notes contradict, fix the note.

## Test plan

No new tests inside the baked project — its suite already covers both sides
of every knob that has a testable runtime surface (celery eager tests and
tasks tests exist and are deleted with their features; deleted code needs no
tests; 100% coverage is enforced per variant). The template-level tests ARE
the CI additions of Step 9: three new bake lanes, one new negative bake, and
one new compose-smoke variant. The local sweep in Step 10 is the executor's
proof; CI re-proves it on every future PR.

## Done criteria

ALL must hold:

- [ ] `uvx cookiecutter . --no-input -o <dir>` output is byte-identical to
      the pre-plan baked output except `.github/scripts/deploy-check.sh`
      (new) and `.github/workflows/tests.yaml` (deploy-check step calls the
      script) — verified via the Step-10 invariance gate.
- [ ] All six Step-10 variants: pytest 100%, pre-commit clean,
      deploy-check.sh exit 0, no `cookiecutter`/`{%-` strings in output.
- [ ] `uvx cookiecutter . --no-input -o /tmp/x use_celery=bogus` fails with
      non-zero exit and creates no project directory.
- [ ] A `use_traefik=no traefik_tls=external` bake succeeds with zero
      traefik traces (the sub-knob is inert without traefik).
- [ ] Root `uvx pre-commit run --all-files` exits 0.
- [ ] Root `README.md` Variables table lists all 12 variables (6 old + 6
      knobs).
- [ ] `git status` shows no modifications outside the Scope list.
- [ ] `plans/README.md` status row for 022 updated.

## STOP conditions

Stop and report back (do not improvise) if:

- Plan 018's changes are not committed, or `prod.yaml` has no `traefik:`
  service (the drift-check preconditions).
- Cookiecutter does NOT reject an invalid choice value at Step 1 — the
  validation strategy assumption is false and pre_gen (out of scope) would
  need changes.
- The default-bake invariance gate fails on any file other than the two
  expected ones after Step 4, and you cannot attribute the diff to a
  whitespace-control mistake you can fix within two attempts.
- Any variant cannot reach 100% coverage without adding new source code or
  tests beyond the deletions/conditionals specified here.
- The baked project's pre-commit rejects `deploy-check.sh` for reasons that
  would require restructuring the script (not mere formatting).
- You find a `_copy_without_render` interaction not covered here (e.g. a
  workflows file that must differ per knob and cannot delegate to a
  rendered script).
- Executing this plan appears to require editing `hooks/pre_gen_project.py`
  or any `plans/0*.md`.

## Maintenance notes

- **Every future plan that adds a prod-required env var** must now thread it
  through FOUR conditional sites: `.env.example`, the Dockerfile
  collectstatic RUN, `.github/scripts/deploy-check.sh` (this replaces the
  old "tests.yaml env block" site), and the root ci.yaml smoke env-prep —
  choosing the right knob condition for each.
- **Plan 020** (env blocks): if it runs after this plan, its restructuring
  of `.env.example` must preserve the knob conditionals. Its dependency
  note in `plans/README.md` should be updated by whoever executes second.
- **Plan 021** (open-source readiness): documents the final knob surface in
  the front-door README; the Variables table added here gives it the
  structure. 021 also owns the license knob decision (deferred from this
  plan).
- **Reviewer focus**: (1) whitespace-control mistakes that survive only in
  non-default variants — CI's three new bake lanes are the guard, but eyes
  on the compose files' `{%- if %}` nesting are cheap insurance; (2) the
  `FORWARDED_ALLOW_IPS`/loopback reasoning in Step 7 — if the ports mapping
  is ever widened beyond `127.0.0.1`, the proxy-header trust story breaks;
  (3) post_gen_project.py is no longer statically linted at root — its
  correctness is now proven only by CI bakes.
- **Deferred**: a license knob (021); broader Anymail provider set
  (maintainer chose resend/smtp/none — revisit only on user demand);
  a `use_celery=worker` smoke variant in CI (bake lane exists, compose
  smoke does not — add if beat-less compose regressions ever occur); an
  external-TLS compose smoke (would need an openssl self-signed pair in
  `.docker/certs/` and an `curl --insecure https://localhost/api/health`
  probe — worthwhile if the external path ever regresses; the bake lane +
  `docker compose config` check are the current guards).
- Combination count is 3×3×2×2×2×2 = 144; CI exercises 7 bakes + 2 smokes.
  That is a deliberate cost/coverage tradeoff; the invariance gate plus
  per-knob greps keep the untested combinations low-risk (knobs are
  independent except the celery×email tasks.py cross-term — variant 5 —
  and traefik×traefik_tls, whose external sites all nest inside the
  traefik-only blocks — variant 6 plus the inert-combination bake).
