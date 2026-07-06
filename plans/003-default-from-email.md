# Plan 003: Give production email a real sender address

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving to the
> next step. If anything in the "STOP conditions" section occurs, stop and
> report — do not improvise. When done, update the status row for this plan
> in `plans/README.md` — unless a reviewer dispatched you and told you they
> maintain the index.
>
> **Drift check (run first)**:
> `git diff --stat d333a73..HEAD -- '{{cookiecutter.project_slug}}/src/config/settings/components/email.py' '{{cookiecutter.project_slug}}/.env.example' '{{cookiecutter.project_slug}}/tests/unit/core/tasks_test.py' '{{cookiecutter.project_slug}}/README.md'`
> If any in-scope file changed since this plan was written, compare the
> "Current state" excerpts against the live code before proceeding; on a
> mismatch, treat it as a STOP condition.

## Status

- **Priority**: P1
- **Effort**: S
- **Risk**: LOW
- **Depends on**: none (serialize with any plan touching `.env.example`)
- **Category**: bug
- **Planned at**: commit `d333a73`, 2026-07-05

## Why this matters

`apps.core.tasks.send_email` calls `send_mail(from_email=None, ...)`,
which makes Django fall back to `DEFAULT_FROM_EMAIL` — and no settings
module sets it, so the sender is Django's default `webmaster@localhost`.
Resend (and most SMTP relays) reject mail from an unverified `localhost`
sender, so in a `resend`/`smtp` bake every production email fails at
runtime while dev (console) and CI (locmem) happily accept it. Worse,
the generated README already instructs users to "set `DEFAULT_FROM_EMAIL`
once the sending domain is known" — but nothing reads any such value from
the environment, so following the instruction does nothing. This plan
makes the documented knob real.

## Current state

Cookiecutter template; generated project under the literal directory
`{{cookiecutter.project_slug}}/` (quote in shell). Jinja conditionals in
these files must stay valid. Knob background: `email_provider` ∈
`resend` | `smtp` | `none`. When `email_provider == "none"` OR
`use_celery == "none"`, `hooks/post_gen_project.py` deletes
`src/apps/core/tasks.py` and `tests/unit/core/tasks_test.py` from the
baked output (see `REMOVED_PATHS` in that hook) — so those two files need
no Jinja gating for this change.

- `{{cookiecutter.project_slug}}/src/config/settings/components/email.py`
  — full current content (one line):

  ```python
  EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
  ```

- `{{cookiecutter.project_slug}}/src/config/settings/environments/prod.py:15-24`
  — swaps `EMAIL_BACKEND` to Anymail/Resend or SMTP per knob; never sets
  a sender.

- `{{cookiecutter.project_slug}}/src/apps/core/tasks.py` — full content:

  ```python
  from celery import shared_task
  from django.core.mail import send_mail


  @shared_task
  def send_email(*, message: str, recipient_list: list[str], subject: str) -> None:
      send_mail(
          from_email=None, message=message, recipient_list=recipient_list, subject=subject
      )
  ```

  `from_email=None` deliberately defers to `DEFAULT_FROM_EMAIL` — keep it
  that way; the fix is the setting, not the task.

- `grep -rn "DEFAULT_FROM_EMAIL\|SERVER_EMAIL" '{{cookiecutter.project_slug}}/src'`
  → no matches (verified at planning time).

- `{{cookiecutter.project_slug}}/.env.example:67-85` — the Email block
  exists only when `email_provider != "none"`; keys alphabetized within
  the block; own-line comments only; commented entries = optional
  overrides with safe code defaults (that convention is documented at the
  top of the file and in the baked `AGENTS.md`).

- `{{cookiecutter.project_slug}}/README.md:146-164` — the email paragraph
  (two provider branches). The resend branch currently says: "Set
  `RESEND_API_KEY` in production, set `DEFAULT_FROM_EMAIL` once the
  sending domain is known, and send …".

- `{{cookiecutter.project_slug}}/tests/unit/core/tasks_test.py` — asserts
  `body`, `subject`, `to` on `mail.outbox[0]` but not `from_email`.

- Repo conventions that apply: settings alphabetized per component; env
  vars only for secrets/topology/sizing (a sender address is deployment
  topology); `cookiecutter.domain_name` is a bare hostname (default
  `example.com`) already used to prefill `.env.example` values.

## Commands you will need

| Purpose | Command | Expected on success |
|---------|---------|---------------------|
| Bake (default = resend) | `uvx cookiecutter . --no-input -o /tmp/plan003` | baked |
| Bake (smtp) | `uvx cookiecutter . --no-input -o /tmp/plan003smtp email_provider=smtp` | baked |
| Bake (no email) | `uvx cookiecutter . --no-input -o /tmp/plan003none email_provider=none` | baked; no tasks.py |
| Baked tests | `uv sync --locked && uv run pytest` (Postgres per plan 001 if landed) | pass, 100% cov |
| Baked pre-commit | `git add -A && uv run pre-commit run --all-files` | exit 0 |
| Root pre-commit | `pre-commit run --all-files` | exit 0 |

## Scope

**In scope**:

- `{{cookiecutter.project_slug}}/src/config/settings/components/email.py`
- `{{cookiecutter.project_slug}}/.env.example` (Email block only)
- `{{cookiecutter.project_slug}}/tests/unit/core/tasks_test.py`
- `{{cookiecutter.project_slug}}/README.md` (email paragraph only)

**Out of scope** (do NOT touch):

- `src/apps/core/tasks.py` — `from_email=None` is correct.
- `SERVER_EMAIL` / `ADMINS` error-mail plumbing — the template's error
  channel is Sentry; deliberately not configured (record only).
- `prod.py` — backend selection stays where it is.

## Git workflow

- Work directly on `main`; do not create or switch to a plan branch unless the
  operator explicitly asks.
- Do NOT commit, push, or open a PR unless the operator explicitly instructs it.
- If asked to commit, use a conventional commit such as
  `fix: configure DEFAULT_FROM_EMAIL for production senders`.

## Steps

### Step 1: Set DEFAULT_FROM_EMAIL in the email component

Replace `email.py` content with (alphabetical order; env import needed;
the setting is gated because a `none` bake sends no product email and
should keep Django's default untouched):

```python
{%- if cookiecutter.email_provider != "none" %}
from config.settings import env

{% endif -%}
{%- if cookiecutter.email_provider != "none" %}
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default="noreply@{{ cookiecutter.domain_name }}")
{% endif -%}
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
```

Exact Jinja layout is up to you, but the rendered results must be:

- provider `resend`/`smtp`:

  ```python
  from config.settings import env

  DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default="noreply@example.com")
  EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
  ```

- provider `none`: the single `EMAIL_BACKEND` line, no import.

Check rendered whitespace on ALL THREE provider bakes (Jinja `{%- %}`
trimming is the usual trap); Ruff runs on the rendered file via the baked
pre-commit and will catch unused imports or blank-line issues.

**Verify**: bake all three providers; `cat` the rendered `email.py` in
each and compare to the shapes above.

### Step 2: Document the optional override in `.env.example`

Inside the existing `{%- if cookiecutter.email_provider != "none" %}`
Email block, add alphabetically (before `EMAIL_HOST`/`RESEND_API_KEY`,
since `D` < `E` < `R`) as a commented optional override:

```text
# Optional sender address for outgoing mail.
# DEFAULT_FROM_EMAIL=noreply@{{ cookiecutter.domain_name }}
```

**Verify**: bake resend + smtp; the entry renders in both; bake `none`;
the entry (and block) is absent.

### Step 3: Make the task test pin the sender

In `tasks_test.py`, add to the existing test's assertions (import
`from django.conf import settings`):

```python
assert mail.outbox[0].from_email == settings.DEFAULT_FROM_EMAIL
```

Keep assertion order matching the existing style (alphabetical by
attribute: body, from_email, subject, to).

**Verify**: baked (default) `uv run pytest` → passes. Then temporarily
edit the baked `tasks.py` to `from_email="wrong@example.com"` and rerun
→ that test fails (proves the assertion bites); revert the baked edit.

### Step 4: Align the README

In the baked README's email paragraph, both provider branches: change
"set `DEFAULT_FROM_EMAIL` once the sending domain is known" to say the
default sender is `noreply@<domain_name>` and `DEFAULT_FROM_EMAIL` in the
environment overrides it (Resend branch: note the sender domain must be
verified in Resend; SMTP branch: note the relay must permit the sender).

**Verify**: bake resend + smtp; read the rendered paragraph in both.

### Step 5: Full verification

All three provider bakes: `uv sync --locked`, `uv run pytest` (where
tests exist), `git add -A && uv run pre-commit run --all-files`. Root:
`pre-commit run --all-files`.

**Verify**: all exit 0; the `none` bake contains no
`DEFAULT_FROM_EMAIL` anywhere (`grep -rn DEFAULT_FROM_EMAIL` → empty).

## Test plan

- Extended: `tests/unit/core/tasks_test.py` — sender assertion (Step 3),
  including the one-off mutation check proving it can fail.
- No new files. Coverage stays 100% (the new settings line executes at
  import).

## Done criteria

- [ ] Rendered `email.py` matches the shapes in Step 1 for all three
      `email_provider` values
- [ ] `.env.example` shows the commented `DEFAULT_FROM_EMAIL` line for
      resend/smtp bakes only
- [ ] Baked default suite passes with the new `from_email` assertion
- [ ] Baked pre-commit and root pre-commit exit 0
- [ ] `git status` clean outside the in-scope list
- [ ] `plans/README.md` status row updated

## STOP conditions

- Rendered `email.py` for any provider has Ruff/whitespace errors you
  cannot fix by adjusting Jinja trim markers within the file.
- `tasks_test.py` turns out to be Jinja-conditional or absent in the
  default bake (contradicts "Current state") — re-check the hook logic
  and report.
- You find an existing sender configuration mechanism this plan would
  duplicate.

## Maintenance notes

- Plan 010 restructures `tasks.py`/`tasks_test.py` gating (periodic task
  example) — run this plan first; 010's drift check expects the sender
  assertion to exist.
- `SERVER_EMAIL` (Django error mails) was considered and deliberately
  skipped: `ADMINS` is unset and Sentry owns error reporting. If someone
  later adds `ADMINS`, they must also set `SERVER_EMAIL`.
- Reviewer: check the three rendered `email.py` variants in the PR — Jinja
  whitespace bugs are the likely failure mode here.
