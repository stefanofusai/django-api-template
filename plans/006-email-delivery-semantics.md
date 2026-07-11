# Plan 006: Give the email task explicit at-most-once delivery semantics

> **Executor instructions**: Run all gates and update the index. Stop rather
> than choosing a different delivery guarantee without maintainer approval.
>
> **Drift check (run first)**: `rtk git diff --stat 20ec7c5..HEAD -- '{{cookiecutter.project_slug}}/src/apps/core/tasks.py' '{{cookiecutter.project_slug}}/tests/core/unit/tasks_test.py' '{{cookiecutter.project_slug}}/README.md' '{{cookiecutter.project_slug}}/AGENTS.md'`

## Status

- **Priority**: P1
- **Effort**: S
- **Risk**: MED
- **Depends on**: none
- **Category**: bug
- **Planned at**: commit `20ec7c5`, 2026-07-10

## Why this matters

Global Celery settings acknowledge late and redeliver on worker loss. The
example `send_email` task performs an irreversible external side effect with
no idempotency key, so a worker can send a message, die before acknowledgement,
and send it again after redelivery. SMTP cannot provide exactly-once delivery;
the template must choose and document a truthful guarantee.

## Current state

- `components/celery.py:35-37` enables late acknowledgement and rejection on
  worker loss globally.
- `tasks.py:24-28` sends directly through Django email.
- The README recommends calling `send_email.delay(...)`.
- Generated guidance says tasks under the global policy must be idempotent.

## Commands you will need

| Purpose | Command | Expected |
|---|---|---|
| Focused tests | `rtk uv run pytest tests/core/unit/tasks_test.py -q` | pass |
| Full tests | `rtk uv run pytest` | pass, coverage 100% |

## Scope

**In scope**:
- `{{cookiecutter.project_slug}}/src/apps/core/tasks.py`
- `{{cookiecutter.project_slug}}/tests/core/unit/tasks_test.py`
- `{{cookiecutter.project_slug}}/README.md`
- `{{cookiecutter.project_slug}}/AGENTS.md`

**Out of scope**:
- Building a transactional outbox or storing message bodies/recipients.
- Claiming exactly-once SMTP delivery.
- Changing semantics of cleanup tasks.

## Git workflow

Do not commit or push unless explicitly requested.

## Steps

### Step 1: Pin the task-specific contract with a failing test

Assert the Celery task object overrides global settings with
`acks_late=False` and `reject_on_worker_lost=False`, while the existing eager
delivery test still sends one message.

**Verify**: the option assertions fail on current code.

### Step 2: Apply at-most-once task options

Set the two options on `@shared_task` for `send_email` only. This acknowledges
before execution, preventing broker redelivery after a partial send but
accepting possible message loss on worker/process failure.

**Verify**: focused tests pass; cleanup tasks retain global late-ack settings.

### Step 3: Document the tradeoff

State the helper is at-most-once and may lose a message during worker failure.
Recommend a project-specific transactional outbox plus a provider idempotency
key where business requirements need durable delivery. Align `AGENTS.md` so it
does not incorrectly classify this task under the global at-least-once rule.

**Verify**: markdownlint and full pre-commit pass.

### Step 4: Verify email-provider combinations

Bake Resend and SMTP worker projects and run task tests/full pytest.

**Verify**: both pass at 100% coverage.

## Test plan

Assert task options, one eager delivery, correct sender/recipient/body, and
unchanged late-ack behavior for an idempotent cleanup task.

## Done criteria

- [ ] Email cannot be broker-redelivered after worker loss.
- [ ] Documentation explicitly states at-most-once and possible loss.
- [ ] Resend and SMTP bakes pass.

## STOP conditions

- The maintainer requires at-least-once delivery; stop and request approval
  for a larger outbox/provider-idempotency design.
- Celery ignores per-task acknowledgement overrides in the pinned version.

## Maintenance notes

New side-effecting tasks must choose a delivery guarantee explicitly. Do not
copy these at-most-once options to database cleanup tasks.
