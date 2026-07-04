# Plan 009: Email via django-anymail (Resend) with a project-owned async send task

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving to the
> next step. If anything in the "STOP conditions" section occurs, stop and
> report — do not improvise. When done, update the status row for this plan
> in `plans/README.md` — unless a reviewer dispatched you and told you they
> maintain the index.
>
> **Drift check (run first)**: `git diff --stat 924bfba..HEAD -- '{{cookiecutter.project_slug}}/pyproject.toml' '{{cookiecutter.project_slug}}/src/config/settings/' '{{cookiecutter.project_slug}}/src/apps/core/' '{{cookiecutter.project_slug}}/tests/' '{{cookiecutter.project_slug}}/.env.example' '{{cookiecutter.project_slug}}/.docker/Dockerfile' '{{cookiecutter.project_slug}}/.github/workflows/tests.yaml'`
> On any change, compare "Current state" excerpts against the live code; on a
> mismatch, treat it as a STOP condition. (Plans 002/007 legitimately touch
> prod.py, .env.example, Dockerfile, tests.yaml — expect those diffs.)

## Status

- **Priority**: P2
- **Effort**: M
- **Risk**: LOW–MED (adds a required prod env var, same blast pattern as Plan 007)
- **Depends on**: 007 recommended first (establishes the required-in-prod + dummy-values pattern this plan reuses); 001 (coverage of the new task module)
- **Category**: direction
- **Planned at**: commit `924bfba`, 2026-07-04

## Why this matters

The template has no email story: no `EMAIL_BACKEND` is configured anywhere,
so baked projects fall back to Django's SMTP default with unset credentials —
the first `send_mail` call in production fails or hangs. The maintainer chose
**django-anymail with the Resend ESP** for delivery and — after reviewing that
django-celery-email's last release is 3.0.0 from December 2019 (pre-Celery 5,
unmaintained) — decided AGAINST that dependency in favor of a small
**project-owned Celery task** that sends through whatever `EMAIL_BACKEND` is
active. Environments split cleanly: console backend in dev (see mail in
logs), locmem in ci (assert on `mail.outbox`), Anymail/Resend in prod with a
required `RESEND_API_KEY`.

## Important context: this is a cookiecutter template

- Project code lives under the literal `{{cookiecutter.project_slug}}/` dir —
  quote it in shell. Preserve Jinja placeholders verbatim.
- Verification = bake + run the baked suite (100% coverage — the new task
  module must be fully tested).

## Current state

- `grep -rn "EMAIL_BACKEND\|anymail" '{{cookiecutter.project_slug}}/src'` →
  no matches (no email config exists).
- Settings component layout: `src/config/settings/components/` one file per
  concern; `src/config/settings/__init__.py:14-27` lists the include order:

  ```python
  include(
      "components/core.py",
      "components/apps.py",
      "components/middleware.py",
      "components/authentication.py",
      "components/templates.py",
      "components/database.py",
      "components/cache.py",
      "components/celery.py",
      "components/logging.py",
      "components/storage.py",
      "components/checks.py",
      f"environments/{DJANGO_ENV}.py",
  )
  ```

- Environment overlays mutate only differences (AGENTS.md); `ci.py` and
  `prod.py` are the overlays to touch.
- `src/apps/core/` currently has `__init__.py`, `apps.py`, `models.py` — no
  `tasks.py`. Celery autodiscovery (`config/celery.py:6`,
  `app.autodiscover_tasks()`) finds `tasks` modules in INSTALLED_APPS —
  `apps.core` is installed, so `apps/core/tasks.py` is auto-discovered.
- Celery policy (from `components/celery.py` + Plan 006's documented reading):
  results opt-in (`CELERY_TASK_IGNORE_RESULT=True`), at-least-once delivery
  (`acks_late` + `reject_on_worker_lost`) → the send task must be
  JSON-serializable and tolerably idempotent (a rare duplicate email on
  worker loss is the accepted tradeoff — document, don't over-engineer).
- Required-in-prod env-var pattern (Plan 007): required read in `prod.py`,
  empty-value line in `.env.example`, dummy values in the Dockerfile
  collectstatic `RUN` env list and the `tests.yaml` deploy-check env list
  (both alphabetized).
- django-anymail latest release verified on PyPI at planning time: **15.0**
  (2026-04-18), supports the Resend ESP via the `resend` extra. Per AGENTS.md
  pin the latest release at execution time.
- Test conventions: eager Celery in ci (`ci.py`), tests under
  `tests/unit/<package>/`, names `test_<subject>_<expected>_when_<condition>`,
  100% coverage.

## Commands you will need

| Purpose | Command | Expected on success |
|---------|---------|---------------------|
| Bake | `uvx cookiecutter . --no-input -o $BAKE` | exit 0 |
| Tests | `cd $BAKE/my-project && uv run pytest` | all pass, 100% |
| Hooks | `cd $BAKE/my-project && git add -A && uv run pre-commit run --all-files` | all pass |
| Prod boot check (inside bake) | Step 5 commands | as stated |

## Scope

**In scope**:
- `{{cookiecutter.project_slug}}/pyproject.toml` (one dependency)
- `{{cookiecutter.project_slug}}/src/config/settings/components/email.py` (create)
- `{{cookiecutter.project_slug}}/src/config/settings/__init__.py` (include list)
- `{{cookiecutter.project_slug}}/src/config/settings/environments/ci.py`
- `{{cookiecutter.project_slug}}/src/config/settings/environments/prod.py`
- `{{cookiecutter.project_slug}}/src/apps/core/tasks.py` (create)
- `{{cookiecutter.project_slug}}/tests/unit/core/__init__.py` (create)
- `{{cookiecutter.project_slug}}/tests/unit/core/tasks_test.py` (create)
- `{{cookiecutter.project_slug}}/.env.example`
- `{{cookiecutter.project_slug}}/.docker/Dockerfile`
- `{{cookiecutter.project_slug}}/.github/workflows/tests.yaml`
- `{{cookiecutter.project_slug}}/README.md`

**Out of scope**:
- django-celery-email — explicitly rejected (unmaintained since 2019).
- `DEFAULT_FROM_EMAIL` configuration — left at Django's default; projects set
  it when they know their domain (note it in README).
- HTML templates, attachments support in the task, per-message ESP options —
  the task is deliberately minimal; extend per project.
- Anymail webhooks (delivery/bounce tracking) — separate feature.

## Git workflow

- Branch: `advisor/009-email-anymail-resend`
- Conventional commit, e.g. `feat: add email via anymail resend with async send task`
- Do NOT push or open a PR unless the operator instructed it.

## Steps

### Step 1: Dependency

`pyproject.toml` `[project].dependencies`: add (alphabetical — after
`django[argon2]`, before `django-celery-beat`/`django-celery-results`):

```toml
"django-anymail[resend]==15.0",
```

(Bump to the latest release if PyPI shows newer; keep exact pin.)

Main dependencies (not prod group) for the same reason as sentry-sdk: prod
settings referencing `anymail.backends...` are loaded by the CI deploy check;
the backend module must import everywhere prod settings can load. Anymail's
core is light (requests + urllib3).

### Step 2: The email settings component

Create `src/config/settings/components/email.py`:

```python
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
```

Add `"components/email.py",` to the `include()` list in
`settings/__init__.py` — after `"components/database.py",` and before
`"components/cache.py",`? No: the include list is ordered by responsibility,
not alphabetically — insert after `"components/celery.py",` so the file
grouping stays cache→celery→email→logging. (Any position before the
environment overlay works mechanically; pick this one for tidy grouping.)

Overlays:
- `ci.py`: add

  ```python
  EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
  ```

- `prod.py`: add (with the file's suppression pattern NOT needed — these are
  new names, not cross-component mutations):

  ```python
  ANYMAIL = {"RESEND_API_KEY": env("RESEND_API_KEY")}
  EMAIL_BACKEND = "anymail.backends.resend.EmailBackend"
  ```

  `env("RESEND_API_KEY")` with no default = required in prod (raises
  `ImproperlyConfigured` when missing). Keep the file's constants
  alphabetized (ANYMAIL near the top with the other new additions per current
  file state).

### Step 3: The send task

Create `src/apps/core/tasks.py`:

```python
from celery import shared_task
from django.core.mail import send_mail


@shared_task
def send_email(
    *,
    message: str,
    recipient_list: list[str],
    subject: str,
) -> None:
    send_mail(
        from_email=None,
        message=message,
        recipient_list=recipient_list,
        subject=subject,
    )
```

Design notes baked into the shape: kwargs-only (JSON-serializable by
construction, alphabetized per AGENTS.md), `from_email=None` defers to
`DEFAULT_FROM_EMAIL`, no result opt-in (fire-and-forget per the documented
result policy). Delivery is at-least-once — a duplicate send on worker loss
is accepted.

### Step 4: Tests

Create `tests/unit/core/__init__.py` (empty) and
`tests/unit/core/tasks_test.py`:

```python
from django.core import mail

from apps.core.tasks import send_email


def test_send_email_delivers_message_when_dispatched_eagerly() -> None:
    send_email.delay(
        message="body",
        recipient_list=["to@example.com"],
        subject="subject",
    )

    assert len(mail.outbox) == 1
    assert mail.outbox[0].body == "body"
    assert mail.outbox[0].subject == "subject"
    assert mail.outbox[0].to == ["to@example.com"]
```

(`.delay()` executes inline under ci's eager mode against the locmem backend;
`mail.outbox` is reset per test by Django's test plumbing via pytest-django.)

**Verify**: bake → `uv run pytest tests/unit/core/tasks_test.py` → passes;
full `uv run pytest` → 100% (tasks.py fully covered).

### Step 5: Required-in-prod wiring (mirror Plan 007's pattern)

1. `.env.example`: add `RESEND_API_KEY=` in byte-sorted position (after
   `POSTGRES_USER=...`, before `SECRET_KEY=...`).
2. Dockerfile collectstatic `RUN` env list: add `RESEND_API_KEY=$(uuidgen) \`
   in alphabetical position (after `DJANGO_ENV=prod`, before `SECRET_KEY=`).
3. `tests.yaml` deploy-check env block: add `RESEND_API_KEY=ci-dummy \` in
   alphabetical position.
4. If Plan 013's smoke-test workflow exists, add `RESEND_API_KEY=dummy` to its
   generated `.env`.

Prod boot checks inside a bake (base env as in Plan 007 Step 5, including a
valid `SENTRY_DSN` if 007 landed):
- WITHOUT `RESEND_API_KEY` → `uv run python manage.py check` → fails with
  `ImproperlyConfigured` naming RESEND_API_KEY.
- With `RESEND_API_KEY=dummy` → exits 0.

### Step 6: README

Add an "Email" note (Local Setup or the Production section): dev prints mail
to the console; tests use locmem; production sends through Resend via Anymail
and requires `RESEND_API_KEY`; set `DEFAULT_FROM_EMAIL` once your domain is
known; send asynchronously with `apps.core.tasks.send_email.delay(...)`.

### Step 7: Full verification loop

**Verify**: fresh bake → `uv run pytest` → all pass, 100%;
`git add -A && uv run pre-commit run --all-files` → all pass; Step 5 boot
checks behave as stated.

## Test plan

- `tests/unit/core/tasks_test.py` as in Step 4 (eager dispatch → locmem
  outbox). Pattern: existing unit tests + AGENTS.md naming.
- Prod backend wiring is verified by the deploy check (imports the anymail
  backend path via settings load) and the Step 5 boot checks.

## Done criteria

- [ ] `grep -n "django-anymail" '{{cookiecutter.project_slug}}/pyproject.toml'` → one exact-pinned entry with the resend extra
- [ ] `components/email.py` exists and is in the include() list
- [ ] ci overlay uses locmem; prod overlay uses anymail + required RESEND_API_KEY
- [ ] `grep -c RESEND_API_KEY` across `.env.example`, `Dockerfile`, `tests.yaml` → present in all three
- [ ] Baked project: `uv run pytest` → all pass, 100%
- [ ] Baked project: `uv run pre-commit run --all-files` → all pass
- [ ] Step 5 boot checks: fail without key, pass with dummy
- [ ] No files outside the in-scope list modified (`git status`)
- [ ] `plans/README.md` status row updated

## STOP conditions

- The pinned anymail version does not support Django 6 or the resolver fails —
  report; do not fall back to raw SMTP config silently.
- The anymail Resend backend import path
  (`anymail.backends.resend.EmailBackend`) differs on the pinned version —
  check anymail's docs for the exact path and report the discrepancy if the
  documented one diverges from this plan.
- You are tempted to add django-celery-email after all — explicitly rejected;
  stop.

## Maintenance notes

- If a project needs attachments/HTML mail, extend `send_email` (or add a
  sibling task) keeping kwargs JSON-serializable — never pass `EmailMessage`
  objects through the broker.
- Anymail raises `AnymailAPIError` on ESP failures; with `acks_late` the task
  retries only if the worker dies — deliberate. If retry-on-API-error is
  wanted later, add `autoretry_for=(AnymailAPIError,)` with backoff and keep
  idempotency in mind.
- Swapping ESPs later = change the extra, the backend path, and the API-key
  setting name; the task and call sites don't change.
