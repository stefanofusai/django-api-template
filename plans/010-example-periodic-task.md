# Plan 010: Ship an example periodic task for the beat scheduler

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving to the
> next step. If anything in the "STOP conditions" section occurs, stop and
> report — do not improvise. When done, update the status row for this plan
> in `plans/README.md` — unless a reviewer dispatched you and told you they
> maintain the index.
>
> **Drift check (run first)**:
> `git diff --stat d333a73..HEAD -- '{{cookiecutter.project_slug}}/src/apps/core/tasks.py' '{{cookiecutter.project_slug}}/tests/unit/core/tasks_test.py' '{{cookiecutter.project_slug}}/src/config/settings/components/celery.py' hooks/post_gen_project.py .github/workflows/ci.yaml '{{cookiecutter.project_slug}}/README.md'`
> Plan 003 legitimately edits `tasks_test.py` (sender assertion) —
> integrate. On other unexplained mismatches with the excerpts below,
> STOP.

## Status

- **Priority**: P3
- **Effort**: M
- **Risk**: MED — restructures the celery/email file-removal matrix in
  the post-gen hook
- **Depends on**: 003 (hard — same files); 001 (ordering — tests on
  Postgres)
- **Category**: direction
- **Planned at**: commit `d333a73`, 2026-07-05

## Why this matters

The default bake (`use_celery=worker+beat`) runs a dedicated always-on
scheduler process, wires `django_celery_beat` with `DatabaseScheduler`,
and documents "manage schedules in Django Admin" — yet ships zero
periodic tasks and no code example of the pattern. The scheduler idles
with nothing to schedule, and the code-defined-schedule path (the one
most teams start with) is undocumented. Ship one genuinely useful,
idempotent periodic task — clearing expired sessions, real housekeeping
every Django site needs — demonstrating `@shared_task` +
`CELERY_BEAT_SCHEDULE`, including how django-celery-beat syncs
code-defined entries into the database scheduler.

A structural fix rides along: today `hooks/post_gen_project.py` removes
`tasks.py`/`tasks_test.py` whenever `use_celery == "none"` **or**
`email_provider == "none"` — coupling the whole task module to email.
Once a non-email task exists, the module must survive email-less celery
bakes, so the removal condition changes to celery-only and the
email-specific pieces become Jinja-gated inside the files.

## Current state

Cookiecutter template. Generated project under the literal
`{{cookiecutter.project_slug}}/` directory. Knobs: `use_celery` ∈
`worker+beat` | `worker` | `none`; `email_provider` ∈ `resend` | `smtp`
| `none`.

- `{{cookiecutter.project_slug}}/src/apps/core/tasks.py` — full content
  (render-plain today; removal handled by the hook):

  ```python
  from celery import shared_task
  from django.core.mail import send_mail


  @shared_task
  def send_email(*, message: str, recipient_list: list[str], subject: str) -> None:
      send_mail(
          from_email=None, message=message, recipient_list=recipient_list, subject=subject
      )
  ```

- `hooks/post_gen_project.py:25-53` — the relevant `REMOVED_PATHS`
  entries:

  ```python
  *(
      ["src/apps/core/tasks.py", "tests/unit/core/tasks_test.py"]
      if USE_CELERY == "none" or EMAIL_PROVIDER == "none"
      else []
  ),
  ```

- `{{cookiecutter.project_slug}}/src/config/settings/components/celery.py`
  — alphabetized `CELERY_*` settings; `CELERY_BEAT_SCHEDULER` is gated
  `{%- if cookiecutter.use_celery == "worker+beat" %}`; this file is
  removed entirely when `use_celery == "none"`. django-celery-beat's
  `DatabaseScheduler` installs entries from the `CELERY_BEAT_SCHEDULE`
  setting into its database tables on startup (`update_from_dict`), so
  code-defined entries appear in admin.

- `{{cookiecutter.project_slug}}/src/config/settings/environments/ci.py`
  — eager tasks in tests:
  `CELERY_TASK_ALWAYS_EAGER = True`, `CELERY_TASK_EAGER_PROPAGATES = True`
  (gated on celery).

- `{{cookiecutter.project_slug}}/tests/unit/core/tasks_test.py` — one
  test (`send_email` via `.delay(...)`, asserts `mail.outbox`); plan 003
  adds a `from_email` assertion.

- `{{cookiecutter.project_slug}}/README.md:166-171` — the beat paragraph:

  > Periodic task schedules are managed in Django Admin through
  > django-celery-beat's `DatabaseScheduler`. Run exactly one
  > `celery-beat` instance for a deployment. The `celery-beat` service
  > has no healthcheck and relies on the Compose restart policy.

- `.github/workflows/ci.yaml` `bake` job matrix — no case covers
  `use_celery != "none"` with `email_provider=none` (the combination
  this plan makes newly meaningful).

- `django.contrib.sessions` is in `INSTALLED_APPS`
  (`components/apps.py`), DB-backed sessions (default engine), so
  expired-session rows really accumulate.

- Baked AGENTS.md task rule: "Celery results are opt-in per task …
  tasks are at-least-once (`acks_late` + `reject_on_worker_lost`), so
  keep them idempotent." `clearsessions` is idempotent. Style: public
  functions alphabetized (`clear_expired_sessions` before `send_email`).

## Commands you will need

| Purpose | Command | Expected on success |
|---------|---------|---------------------|
| Bake default | `uvx cookiecutter . --no-input -o /tmp/plan010` | both tasks present |
| Bake worker, no email | `uvx cookiecutter . --no-input -o /tmp/plan010wne use_celery=worker email_provider=none` | tasks.py present, NO send_email |
| Bake no celery | `uvx cookiecutter . --no-input -o /tmp/plan010nc use_celery=none` | NO tasks.py |
| Suite | `uv sync --locked && uv run pytest` (Postgres per plan 001) | pass, 100% cov |
| Baked pre-commit | `git add -A && uv run pre-commit run --all-files` | exit 0 |
| Root pre-commit | `pre-commit run --all-files` | exit 0 |

## Scope

**In scope**:

- `{{cookiecutter.project_slug}}/src/apps/core/tasks.py`
- `{{cookiecutter.project_slug}}/tests/unit/core/tasks_test.py`
- `{{cookiecutter.project_slug}}/src/config/settings/components/celery.py`
- `hooks/post_gen_project.py` (the one `REMOVED_PATHS` condition)
- `.github/workflows/ci.yaml` (one new bake matrix case)
- `{{cookiecutter.project_slug}}/README.md` (beat paragraph)

**Out of scope** (do NOT touch):

- Compose files, celery worker/beat scripts.
- The email sending path (plan 003 owns the sender).
- Any new dependency.

## Git workflow

- Work directly on `main`; do not create or switch to a plan branch unless the
  operator explicitly asks.
- Do NOT commit, push, or open a PR unless the operator explicitly instructs it.
- If asked to commit, use a conventional commit such as
  `feat: add clear_expired_sessions periodic task example`.

## Steps

### Step 1: Restructure tasks.py with knob gating

New content (note alphabetical function order and gated email pieces):

```python
{%- if cookiecutter.email_provider != "none" %}
from celery import shared_task
from django.core.mail import send_mail
from django.core.management import call_command
{%- else %}
from celery import shared_task
from django.core.management import call_command
{%- endif %}


@shared_task
def clear_expired_sessions() -> None:
    call_command("clearsessions")
{%- if cookiecutter.email_provider != "none" %}


@shared_task
def send_email(*, message: str, recipient_list: list[str], subject: str) -> None:
    send_mail(
        from_email=None, message=message, recipient_list=recipient_list, subject=subject
    )
{%- endif %}
```

(Adjust the Jinja so BOTH rendered variants are Ruff-clean — import
blocks sorted, exactly two blank lines between defs, trailing newline.)

**Verify**: bake default and worker-no-email variants; `cat` both
rendered `tasks.py`; run `uvx ruff check --select ALL --ignore
COM812,D1,D203,D212,E501,FIX001,FIX002,TC001,TC003,TD001,TD002,TD003`
on each (mirrors the project config) or rely on Step 6's baked
pre-commit.

### Step 2: Loosen the hook removal condition

In `hooks/post_gen_project.py`, change:

```python
*(
    ["src/apps/core/tasks.py", "tests/unit/core/tasks_test.py"]
    if USE_CELERY == "none" or EMAIL_PROVIDER == "none"
    else []
),
```

to:

```python
*(
    ["src/apps/core/tasks.py", "tests/unit/core/tasks_test.py"]
    if USE_CELERY == "none"
    else []
),
```

(`EMAIL_PROVIDER` stays used by other entries? Check: at planning time
it is used ONLY by this entry — if so, also remove the now-unused
`EMAIL_PROVIDER` constant, or keep it if any other entry references it.
Verify with grep before deciding.)

**Verify**: the three bake variants in the commands table produce:
default → tasks.py with both tasks; worker-no-email → tasks.py with only
`clear_expired_sessions`; no-celery → no tasks.py, no tasks_test.py.

### Step 3: Schedule it (worker+beat only)

In `components/celery.py`, add alphabetically (after
`CELERY_BEAT_SCHEDULER`, gated the same way):

```python
{%- if cookiecutter.use_celery == "worker+beat" %}
CELERY_BEAT_SCHEDULER = "django_celery_beat.schedulers:DatabaseScheduler"
# DatabaseScheduler copies this dict into its database tables on beat
# startup; the admin then owns the live schedule (edits there persist,
# but the entry reappears if deleted while this setting still defines it).
CELERY_BEAT_SCHEDULE = {
    "clear-expired-sessions": {
        "schedule": crontab(hour=3, minute=0),
        "task": "apps.core.tasks.clear_expired_sessions",
    },
}
{%- endif %}
```

with a gated `from celery.schedules import crontab` import at the top
(imports precede the `from config.settings import env` line per isort
order — celery is third-party like django; check Ruff's isort output).

**Verify**: bake default → renders both settings; bake
`use_celery=worker` → neither `CELERY_BEAT_*` present; bake
`use_celery=none` → file absent.

### Step 4: Test the task

Extend `tests/unit/core/tasks_test.py` (keep functions alphabetized —
the new test comes first; `pytestmark = pytest.mark.django_db` needed
now):

```python
def test_clear_expired_sessions_deletes_expired_rows_when_dispatched_eagerly() -> None:
    expired = Session.objects.create(
        expire_date=timezone.now() - timedelta(days=1),
        session_data="expired",
        session_key="plan010expired",
    )
    live = Session.objects.create(
        expire_date=timezone.now() + timedelta(days=1),
        session_data="live",
        session_key="plan010live",
    )

    clear_expired_sessions.delay()

    assert not Session.objects.filter(pk=expired.pk).exists()
    assert Session.objects.filter(pk=live.pk).exists()
```

Direct `Session.objects.create` is acceptable here despite the
factory-first rule: expiry timestamps ARE the behavior under test and
`Session` is a third-party model with no registered factory — add a
one-line comment saying so (the AGENTS comment policy allows constraint
comments). Imports: `datetime.timedelta`,
`django.contrib.sessions.models.Session`, `django.utils.timezone`,
`apps.core.tasks.clear_expired_sessions`.

The existing `send_email` test gets wrapped in
`{% if cookiecutter.email_provider != "none" %}…{% endif %}` (with its
imports gated too — `django.core.mail`, faker typing import). Check
rendered whitespace in both states.

**Verify**: default bake `uv run pytest tests/unit/core -v` → both pass;
worker-no-email bake → only the sessions test exists and passes; full
suites pass at 100% coverage in both.

### Step 5: CI matrix case + README

- `.github/workflows/ci.yaml` `bake` matrix, alphabetical case name:

  ```yaml
            - case: worker-no-email
              project_name: My Project
              extra-args: use_celery=worker email_provider=none
              slug: my-project
  ```

- Baked README beat paragraph: extend with 1-2 sentences — the project
  ships `clear_expired_sessions` scheduled daily at 03:00 UTC via
  `CELERY_BEAT_SCHEDULE`; DatabaseScheduler copies code-defined entries
  into the database on beat startup, after which Django Admin owns the
  live schedule.

**Verify**: actionlint on `ci.yaml`; bake default → README paragraph
renders; bake `use_celery=worker` → no beat paragraph (existing gating
unchanged).

### Step 6: Full verification

All four bakes (default, worker, worker-no-email, none): suite +
`git add -A && uv run pre-commit run --all-files`; plan 002's
`migrations-check.sh` on default; root `pre-commit run --all-files`.

**Verify**: everything exits 0.

## Test plan

Step 4: one new eager-execution test with a positive and negative
assertion (expired deleted, live kept); existing send_email test
preserved (and knob-gated). Pattern: current `tasks_test.py`.

## Done criteria

- [ ] Four bake variants render/remove `tasks.py`, `tasks_test.py`,
      `celery.py` exactly as the matrix in Step 2/3 describes
- [ ] Default bake: `CELERY_BEAT_SCHEDULE` present; worker bake: absent
- [ ] Suites pass at 100% coverage on default AND worker-no-email bakes
- [ ] `worker-no-email` case added to CI matrix; actionlint green
- [ ] README beat paragraph documents the example + sync semantics
- [ ] Root + baked pre-commit exit 0; `git status` clean outside scope
- [ ] `plans/README.md` status row updated

## STOP conditions

- `EMAIL_PROVIDER` is used by other `REMOVED_PATHS` entries than the one
  excerpted (drift) — re-derive the removal matrix before editing.
- The eager `.delay()` path does not execute `call_command` under CI
  settings — report; do not switch to calling the function directly
  (the `.delay()` round-trip is part of what the test demonstrates).
- Rendered Ruff failures you cannot fix via Jinja whitespace within the
  four variants.
- django-celery-beat does NOT install the code-defined entry into the
  database on startup in the pinned version (check only if you can run
  beat locally; otherwise trust the documented behavior and note it) —
  if verified false, the README sentence and settings comment must
  change; report.

## Maintenance notes

- Anyone adding the next periodic task follows this exact shape: task in
  `apps/*/tasks.py`, entry in `CELERY_BEAT_SCHEDULE`, eager test.
- The 03:00 UTC crontab is a fixed operational constant by convention;
  make it env-tunable only if a real deployment need appears.
- If a future plan adds `SESSION_ENGINE` changes (e.g. cache-backed
  sessions), `clearsessions` becomes a no-op and this example should be
  swapped for different housekeeping.
- Reviewer focus: the four-variant render matrix and the hook condition
  change.
