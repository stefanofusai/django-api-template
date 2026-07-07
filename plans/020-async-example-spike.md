# Plan 020: Design spike — wire the example API to the task queue so the enqueue-from-request pattern is demonstrated and covered

> **Executor instructions**: This is a **design/spike plan**. Deliverable is (1)
> a written recommendation and (2) a throwaway proof-of-concept in a scratch bake
> — NOT a feature merged into the committed template. Enumerate the maintainer
> decisions and STOP. Update this plan's status row in `plans/README.md` when the
> proposal is written.
>
> **Drift check (run first)**:
> `git diff --stat ae42991..HEAD -- "{{cookiecutter.project_slug}}/src/apps/notes/routes.py" "{{cookiecutter.project_slug}}/src/apps/core/tasks.py" "{{cookiecutter.project_slug}}/tests/core/unit/tasks_test.py" "{{cookiecutter.project_slug}}/README.md"`
> On a mismatch with "Current state", note it in the proposal.
>
> **Naming caution**: your deliverable is a NEW file,
> `plans/020-async-example-DESIGN.md`. Do not overwrite this plan file
> (`plans/020-async-example-spike.md`).

## Status

- **Priority**: P3 (spike)
- **Effort**: M
- **Risk**: LOW (no committed files change)
- **Depends on**: none
- **Category**: direction
- **Planned at**: commit `ae42991`, 2026-07-07

## Repository context (read before anything else)

This is a **Cookiecutter template** (source under `{{cookiecutter.project_slug}}/`,
**quote it in shell**; rendered except `.github/workflows/*` and `.agents/*`).
100% coverage on `src/`. Verification means baking:
`uvx cookiecutter . --no-input -o /tmp/bake …`; baked tests need `postgres:18.4`.

Respect the template's minimalism: the example exists "demonstrating the
model-to-tests vertical slice." This spike asks whether to extend that slice to
the *async* dimension — a maintainer taste call, so the deliverable is a
grounded recommendation the maintainer accepts or rejects.

## Why this matters

The template ships both halves of an async workflow but never connects them:

- `src/apps/notes/routes.py` — an authenticated CRUD slice (`create_note`,
  `list_notes`, …), the template's showcase feature.
- `src/apps/core/tasks.py` — a ready `send_email` Celery task. Two gates stack:
  the *file* ships only when `use_celery != "none"` (the post-gen hook deletes
  it otherwise), and `send_email` *within* it is additionally wrapped in
  `{%- if cookiecutter.email_provider != "none" %}`.
- `{{cookiecutter.project_slug}}/README.md` even documents
  `apps.core.tasks.send_email.delay(...)` — but **nothing in shipped code ever
  calls `.delay()`**. `clear_expired_sessions` runs only via beat;
  `tasks_test.py` calls `.delay()` in a test, but no *request handler* enqueues
  anything.

For a template whose stated purpose includes Celery, the single highest-value
task-queue pattern — enqueue-a-task-from-an-endpoint — is left as prose. A worked
example (one notes endpoint that enqueues `send_email`) would make it
copy-pasteable and give the request→enqueue path real coverage. The catch is
knob composition (below), which is exactly why this is a spike, not a direct
build.

## Current state (facts the proposal must build on)

- `send_email` exists only when `email_provider != "none"`
  (`tasks.py`: `{%- if cookiecutter.email_provider != "none" %}` guards it). So an
  enqueue-from-endpoint example that calls `send_email` requires
  **`use_example_api=yes` AND `use_celery != "none"` AND `email_provider != "none"`**
  — a 3-way Jinja gate.
- `send_email` signature: `send_email(*, message, recipient_list, subject)`
  (keyword-only), `from_email=None` (uses `DEFAULT_FROM_EMAIL`).
- `tasks_test.py` already proves the eager `.delay()` path for both tasks (it
  uses `faker`, asserts `mail.outbox`), and runs under `CELERY_TASK_ALWAYS_EAGER`.
  A request→enqueue test would assert `len(mail.outbox) == 1` after hitting the
  endpoint (eager execution runs the task inline).
- `notes/routes.py` uses `django_auth` and scopes to `owner=request.user`; the
  authenticated test client is `authenticated_v1_api_client`
  (`tests/conftest.py` + `tests/utils.py`).
- `tests/notes/integration/notes_test.py` is the structural pattern for a new
  endpoint test.

## The design questions this spike must answer

1. **What is the example action?** Options: a `POST /notes/{id}/share` (or
   `/notify`) endpoint that enqueues `send_email` with the note's content to a
   supplied address; or enqueuing on `create_note`. Pick the one that best
   *teaches the pattern* with least surface. Keep ownership checks
   (`owner=request.user`).
2. **Knob gate & degradation.** The endpoint requires notes+celery+email. When
   any is absent, the endpoint must not render (and the notes router/tests must
   stay valid). Define the exact Jinja gate and confirm the notes slice still
   bakes cleanly in every combination of `use_example_api` × `use_celery` ×
   `email_provider`.
3. **CI matrix.** Which new bake case(s) exercise the endpoint (needs all three
   knobs on) and which confirm the notes slice is intact when they are off?
4. **Coverage.** The endpoint adds `src/` lines that must be 100% covered — under
   which bakes does the test run, and how is coverage kept at 100% in the bakes
   where the endpoint does NOT ship (the test file must be guarded too)?
5. **Schemathesis.** The new route joins the contract test; confirm it stays
   green (it already handles the notes routes' auth responses).
6. **Minimalism check.** Is this worth adding at all, or does it over-grow the
   example? Present "keep it prose-only / document the pattern in a comment" as a
   valid outcome.

## Deliverables

1. **`plans/020-async-example-DESIGN.md`** (create): recommendation per question
   above, the exact endpoint + Jinja gate, the file inventory a build plan would
   touch (`routes.py`, `schemas.py`, a test, CI matrix, README), the coverage
   strategy across knob states, and an explicit "open questions for the
   maintainer" list.
2. **A throwaway PoC** in a scratch bake
   (`use_example_api=yes` default stack, and a second scratch bake with
   `use_celery=none` to prove the gate degrades cleanly): implement the endpoint
   + test, show `uv run pytest` passes at 100% in the enabled bake and the notes
   slice still passes in the disabled bake. Capture diffs in the DESIGN doc.

## Commands you will need

| Purpose | Command | Expected |
|---------|---------|----------|
| Bake PoC (all on) | `uvx cookiecutter . --no-input -o /tmp/bake-poc use_example_api=yes` | notes+celery+email present |
| Bake gate-off | `uvx cookiecutter . --no-input -o /tmp/bake-off use_example_api=yes use_celery=none email_provider=none` | notes present, no celery/email |
| PoC tests | `cd /tmp/bake-poc/my-project && DATABASE_URL=postgres://postgres:postgres@localhost:5432/postgres uv run pytest` | 100% cov, all pass |
| Gate-off tests | `cd /tmp/bake-off/my-project && DATABASE_URL=… uv run pytest` | 100% cov, notes slice intact, no dangling reference |
| PoC pre-commit | `cd /tmp/bake-poc/my-project && git add -A && uv run pre-commit run --all-files` | exit 0 |

## Scope

**In scope**:
- `plans/020-async-example-DESIGN.md` (create).
- A scratch PoC under `/tmp/` (NOT committed to the template).
- Updating this plan's status row in `plans/README.md`.

**Out of scope** (explicitly — this is a spike):
- Modifying any committed file under `{{cookiecutter.project_slug}}/` or
  `cookiecutter.json`. That is the follow-up build plan, written only after the
  maintainer accepts the design.
- Adding dependencies.

## Steps

### Step 1: Confirm the knob-composition matrix

Enumerate `use_example_api` × `use_celery` × `email_provider` and mark where the
enqueue endpoint ships vs. where only the base notes slice ships. Confirm by
baking the corners (all-on; notes-but-no-celery; notes-but-no-email;
celery-but-no-notes). Record which combinations CI already covers (`ci.yaml`:
`example-api` is all-on; `minimal` is all-off).

**Verify**: DESIGN doc has the filled matrix and the exact Jinja gate string.

### Step 2: Build the minimal PoC

In `/tmp/bake-poc/my-project` (scratch): add the endpoint (with an input schema
if it takes a recipient), the Jinja gate, and a test that hits the endpoint as
`authenticated_v1_api_client` and asserts `mail.outbox` has one message
(eager execution). Keep faithful to conventions (ruff `ALL`, ownership scoping,
test naming, alphabetized functions). Then bake `/tmp/bake-off` and confirm the
notes slice still passes at 100% with the endpoint and its test absent.

**Verify**: PoC bake `uv run pytest` 100%; gate-off bake `uv run pytest` 100%;
PoC `git add -A && uv run pre-commit run --all-files` exit 0.

### Step 3: Write the proposal and STOP

Populate `plans/020-async-example-DESIGN.md` (recommendation, endpoint, gate,
file inventory, CI additions, coverage strategy, PoC diffs, open questions).
Report and STOP — the maintainer's answers feed a follow-up build plan.

## Done criteria

ALL must hold:

- [ ] `plans/020-async-example-DESIGN.md` exists and answers all six questions with a recommendation.
- [ ] A scratch PoC's `uv run pytest` passes at 100% (paste output into DESIGN), AND a gate-off scratch bake's notes slice passes at 100% with the endpoint absent.
- [ ] The DESIGN lists the exact Jinja gate, file inventory, and CI matrix additions a build plan needs.
- [ ] The DESIGN has an explicit "open questions for the maintainer" section, including the keep-it-minimal option.
- [ ] **No committed file under `{{cookiecutter.project_slug}}/` or `cookiecutter.json` modified** (`git status` shows only `plans/`).
- [ ] `plans/README.md` status row updated.

## STOP conditions

Stop and report (do not improvise) if:

- Keeping coverage at 100% across all knob combinations forces contorted test
  guards — report the combination that is hard; it informs the gate design.
- The enqueue endpoint cannot be added without changing `send_email`'s signature
  or the auth model — report; that widens scope beyond an "example."
- You find yourself wanting to edit the committed template — that is out of scope
  for a spike; STOP.

## Maintenance notes

- This spike's output is a decision aid; the implementation is a separate build
  plan written only after the maintainer chooses.
- Interacts with the rejected `/ready`-broker-probe finding: if this ships,
  request handlers will enqueue tasks, making the broker a request-path
  dependency — the maintainer may then want to revisit that readiness decision
  (noted in `plans/README.md`).
- Keep the recommendation honest about minimalism: "document the pattern in a
  comment instead of shipping an endpoint" is a valid outcome.
