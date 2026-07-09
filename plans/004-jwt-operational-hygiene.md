# Plan 004: JWT operational hygiene — schedule `flushexpiredtokens`, pin deactivated-user lockout with a test, document the Schemathesis exclusion

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving to the
> next step. If anything in the "STOP conditions" section occurs, stop and
> report — do not improvise. When done, update the status row for this plan
> in `plans/README.md` — unless a reviewer dispatched you and told you they
> maintain the index.
>
> **Drift check (run first)**:
> `git diff --stat e0ec725..HEAD -- '{{cookiecutter.project_slug}}/src/apps/core/tasks.py' '{{cookiecutter.project_slug}}/src/config/settings/components/celery.py' '{{cookiecutter.project_slug}}/tests/core/unit/tasks_test.py' '{{cookiecutter.project_slug}}/tests/api/integration/jwt_test.py' '{{cookiecutter.project_slug}}/tests/api/integration/schema_test.py' '{{cookiecutter.project_slug}}/README.md'`
> If any in-scope file changed since this plan was written, compare the
> "Current state" excerpts against the live code before proceeding; on a
> mismatch, treat it as a STOP condition.

## Status

- **Priority**: P2
- **Effort**: M (three small independent parts)
- **Risk**: LOW
- **Depends on**: none
- **Category**: bug / tests
- **Planned at**: commit `e0ec725`, 2026-07-09

## Why this matters

This repository is a cookiecutter template. When baked with
`use_example_api=yes api_auth=jwt`, the generated project uses
django-ninja-jwt with `ROTATE_REFRESH_TOKENS=True` +
`BLACKLIST_AFTER_ROTATION=True` and the `ninja_jwt.token_blacklist` app.
Three gaps in that new surface:

1. **Unbounded blacklist tables.** Every token-pair issuance writes an
   `OutstandingToken` row; every rotation/blacklist writes a
   `BlacklistedToken` row. Rows are never purged, even after expiry. The
   library ships a `flushexpiredtokens` management command for exactly this,
   but nothing in the template schedules or documents it — on real login
   volume both tables grow forever. The template already has the precedent:
   a `clear-expired-sessions` beat task doing the same job for sessions.
2. **Unpinned deactivation lockout.** `JWTAuth` re-checks `user.is_active`
   per request (verified against ninja_jwt 5.4.4 source), but no test pins
   it: `jwt_test.py` covers deactivation *before* obtaining a pair, not a
   live access token whose user is deactivated *afterwards*. A dependency
   bump changing that behavior would be a silent authz regression. Two
   independent audit passes flagged this same gap.
3. **Undocumented contract-gate exclusion.** The Schemathesis contract tests
   deliberately skip `/api/v1/token/*` (library-owned operations), but the
   skip helper has no comment — a reader cannot distinguish deliberate
   exclusion from oversight.

## Current state

All paths below are inside `{{cookiecutter.project_slug}}/` and contain Jinja
conditionals — always quote the directory in shell commands, and keep Jinja
valid (the file must render correctly for EVERY knob combination, including
ones where a given block disappears).

- Knob facts: JWT machinery exists only when
  `cookiecutter.use_example_api == "yes" and cookiecutter.api_auth == "jwt"`
  (see `src/config/settings/components/apps.py:30-33`, which gates
  `"ninja_jwt"` and `"ninja_jwt.token_blacklist"` on exactly that pair).
  `src/apps/core/tasks.py` and `tests/core/unit/tasks_test.py` are removed by
  the post-gen hook when `use_celery == "none"`
  (`hooks/post_gen_project.py:77`). The beat schedule exists only when
  `use_celery == "worker+beat"`.

- `src/config/settings/components/jwt.py` (whole file, minus header):

  ```python
  NINJA_JWT = {
      "ACCESS_TOKEN_LIFETIME": timedelta(minutes=15),
      "BLACKLIST_AFTER_ROTATION": True,
      "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
      "ROTATE_REFRESH_TOKENS": True,
      "SIGNING_KEY": SECRET_KEY,  # noqa: F821  # ty: ignore[unresolved-reference]
      "UPDATE_LAST_LOGIN": True,
  }
  ```

- `src/config/settings/components/celery.py` — the beat schedule:

  ```python
  {%- if cookiecutter.use_celery == "worker+beat" %}
  # DatabaseScheduler copies this dict into its database tables on beat
  # startup; the admin then owns the live schedule (edits there persist,
  # but the entry reappears if deleted while this setting still defines it).
  CELERY_BEAT_SCHEDULE = {
      "clear-expired-sessions": {
          "schedule": crontab(minute=0),
          "task": "apps.core.tasks.clear_expired_sessions",
      },
  }
  CELERY_BEAT_SCHEDULER = "django_celery_beat.schedulers:DatabaseScheduler"
  {%- endif %}
  ```

- `src/apps/core/tasks.py` — current tasks (Jinja gates on `email_provider`
  only):

  ```python
  @shared_task
  def clear_expired_sessions() -> None:
      call_command("clearsessions")
  ```

  (plus a `send_email` task when `email_provider != "none"`). Tasks appear in
  alphabetical order.

- `tests/core/unit/tasks_test.py` — pattern to model the new test on:
  creates expired + live `Session` rows directly (comment explains: third-
  party model, no registered factory, timestamps are the behavior under
  test), calls `clear_expired_sessions.delay()` (Celery eager mode in tests),
  asserts expired deleted / live kept.

- `tests/api/integration/jwt_test.py` — whole file wrapped in
  `{% if cookiecutter.use_example_api == "yes" and cookiecutter.api_auth == "jwt" %}`.
  Existing tests (alphabetized):
  `test_blacklisted_refresh_token_cannot_be_refreshed`,
  `test_inactive_user_cannot_obtain_token_pair`,
  `test_refresh_token_returns_new_access_token`,
  `test_token_pair_returns_access_and_refresh_tokens`,
  `test_token_pair_access_token_authenticates_notes_request`.
  The last one is the structural model for the new test:

  ```python
  def test_token_pair_access_token_authenticates_notes_request(
      user: User,
      valid_password: str,
      v1_api_client: TestClient,
  ) -> None:
      _set_password(user, valid_password)
      pair_response = v1_api_client.post(
          "/token/pair",
          json={"password": valid_password, "username": user.username},
      )

      response = v1_api_client.get(
          "/notes",
          headers={"Authorization": f"Bearer {pair_response.data['access']}"},
      )

      assert response.status_code == HTTPStatus.OK
  ```

  A `_set_password(user, password)` helper exists in the file's `# Utils`
  section.

- `tests/api/integration/schema_test.py` — the undocumented skip helper (end
  of file, inside the jwt Jinja guard):

  ```python
  # Utils


  def _is_third_party_jwt_operation(case: Case) -> bool:
      return case.path.startswith("/api/v1/token/")
  ```

- `README.md` — JWT endpoints are documented in the Usage section
  (~lines 244-247, inside `{%- if cookiecutter.api_auth == "jwt" %}`):

  ```
  JWT endpoints are available at `/api/v1/token/pair`,
  `/api/v1/token/refresh`, `/api/v1/token/verify`, and
  `/api/v1/token/blacklist`.
  ```

  Cron-example precedent for ops documentation: the postgres-backup block in
  the Production section shows a crontab line.

- Conventions (root `AGENTS.md`): alphabetize (tasks, dict keys, test
  functions); test naming `test_<subject>_<expected_behavior>_when_<condition>`;
  blank lines around control flow; never `from __future__ import annotations`;
  the generated project enforces 100% branch coverage.

## Commands you will need

| Purpose | Command | Expected on success |
|---------|---------|---------------------|
| Bake JWT+beat | `uvx cookiecutter . -o /tmp/verify-004 --no-input use_example_api=yes api_auth=jwt` (use_celery defaults to worker+beat) | exit 0 |
| Bake session variant | `uvx cookiecutter . -o /tmp/verify-004-session --no-input use_example_api=yes` | exit 0 |
| Bake minimal | `uvx cookiecutter . -o /tmp/verify-004-min --no-input use_celery=none` | exit 0 |
| Prepare baked env | `cd <bake>/my-project && cp .env.example .env && uv sync --locked` | exit 0 |
| Start test Postgres | `docker compose -f .docker/compose/dev.yaml --env-file=.env up -d --wait postgres` | exit 0 |
| Baked tests | `uv run pytest` | all pass, coverage gate holds |
| Baked lint | `uv run pre-commit run --all-files` | exit 0 |
| Root checks | `uvx pre-commit run --all-files` | exit 0 (its `generated-format` hook bakes several combos and ruff-checks them) |

## Scope

**In scope** (the only files you should modify):

- `{{cookiecutter.project_slug}}/src/apps/core/tasks.py`
- `{{cookiecutter.project_slug}}/src/config/settings/components/celery.py`
- `{{cookiecutter.project_slug}}/tests/core/unit/tasks_test.py`
- `{{cookiecutter.project_slug}}/tests/api/integration/jwt_test.py`
- `{{cookiecutter.project_slug}}/tests/api/integration/schema_test.py` (one comment only)
- `{{cookiecutter.project_slug}}/README.md`

**Out of scope** (do NOT touch, even though they look related):

- `src/config/settings/components/jwt.py` — lifetimes/rotation settings are
  deliberate; `SIGNING_KEY = SECRET_KEY` is the library default made explicit
  (previously adjudicated: not a finding).
- `hooks/post_gen_project.py` — no new files are created, so removal lists
  are unaffected.
- The Schemathesis skip *behavior* — the exclusion stays; only add the
  comment.

## Git workflow

- Branch: `advisor/004-jwt-operational-hygiene`
- Commit style: conventional commits; one commit per part is fine (e.g.
  `feat: schedule flushexpiredtokens for jwt bakes`,
  `test: pin jwt rejection of users deactivated after issuance`,
  `docs: mark schemathesis token-route exclusion deliberate`).
- Do NOT push or open a PR unless the operator instructed it.

## Steps

### Step 1: Add the `flush_expired_tokens` task

In `src/apps/core/tasks.py`, add a Jinja-gated task between
`clear_expired_sessions` and `send_email` (alphabetical order):

```python
{%- if cookiecutter.use_example_api == "yes" and cookiecutter.api_auth == "jwt" %}


@shared_task
def flush_expired_tokens() -> None:
    call_command("flushexpiredtokens")
{%- endif %}
```

Match the file's existing Jinja whitespace-control style (`{%- ... %}`) so
non-JWT renders keep clean spacing — check the rendered output in both the
JWT and session bakes before moving on.

**Verify**: bake both variants;
`grep -c flush_expired_tokens /tmp/verify-004/my-project/src/apps/core/tasks.py`
→ ≥ 1, and the same grep in the session bake → 0 matches (grep exits 1).
`uv run ruff format --check src/apps/core/tasks.py` inside the JWT bake →
clean (or rely on step 6's full sweep).

### Step 2: Add the beat schedule entry

In `src/config/settings/components/celery.py`, inside the existing
`CELERY_BEAT_SCHEDULE` dict (which only renders when
`use_celery == "worker+beat"`), add a Jinja-gated entry after
`clear-expired-sessions` (alphabetical key order):

```python
  {%- if cookiecutter.use_example_api == "yes" and cookiecutter.api_auth == "jwt" %}
      "flush-expired-tokens": {
          "schedule": crontab(hour=3, minute=0),
          "task": "apps.core.tasks.flush_expired_tokens",
      },
  {%- endif %}
```

(Daily at 03:00 — expiry granularity is days, hourly would be noise. Indent
to match the dict.)

**Verify**: in the JWT bake, `grep -A2 "flush-expired-tokens" src/config/settings/components/celery.py`
→ shows the entry; in the session bake the grep finds nothing and
`python -c "import ast; ast.parse(open('src/config/settings/components/celery.py').read())"`
is NOT applicable (settings components are exec'd with Jinja already
rendered — instead just confirm the rendered file has no dangling comma
syntax by running the baked test suite in step 6).

### Step 3: Test the flush task

In `tests/core/unit/tasks_test.py`, add (alphabetized between the session
test and `send_email` test) a Jinja-gated test mirroring the session-clearing
test's structure and its "third-party model, create rows directly" comment
style:

```python
{%- if cookiecutter.use_example_api == "yes" and cookiecutter.api_auth == "jwt" %}


def test_flush_expired_tokens_deletes_expired_rows_when_dispatched_eagerly() -> None:
    # OutstandingToken is a third-party model with no registered factory, and
    # expiry timestamps are the behavior under test, so create rows directly.
    expired = OutstandingToken.objects.create(
        expires_at=timezone.now() - timedelta(days=1),
        jti="plan004expired",
        token="expired",
    )
    live = OutstandingToken.objects.create(
        expires_at=timezone.now() + timedelta(days=1),
        jti="plan004live",
        token="live",
    )

    flush_expired_tokens.delay()

    assert not OutstandingToken.objects.filter(pk=expired.pk).exists()
    assert OutstandingToken.objects.filter(pk=live.pk).exists()
{%- endif %}
```

Add the matching Jinja-gated imports
(`from ninja_jwt.token_blacklist.models import OutstandingToken` and
`flush_expired_tokens` alongside the existing `clear_expired_sessions`
import) — the file's import block is already Jinja-branched; extend it
carefully so BOTH branches (email vs no-email) x (jwt vs session) render
valid, unused-import-free Python. This is the fiddliest part of the plan:
after editing, bake all four combinations that exist
(`email_provider` in {resend, none} x `api_auth` in {jwt, session}, with
`use_example_api=yes use_celery=worker+beat`) if in doubt — at minimum the
two bakes in this plan's command table — and ruff-check the rendered file.

**Verify**: JWT bake → `uv run pytest tests/core/unit/tasks_test.py` → all
pass (3 tasks tests when email enabled). Session bake → same command → the
flush test is absent, suite passes.

### Step 4: Pin post-issuance deactivation lockout

In `tests/api/integration/jwt_test.py`, add (alphabetized — it sorts first):

```python
def test_access_token_is_rejected_when_user_deactivated_after_issuance(
    user: User,
    valid_password: str,
    v1_api_client: TestClient,
) -> None:
    _set_password(user, valid_password)
    pair_response = v1_api_client.post(
        "/token/pair",
        json={"password": valid_password, "username": user.username},
    )

    user.is_active = False
    user.save(update_fields=("is_active",))

    response = v1_api_client.get(
        "/notes",
        headers={"Authorization": f"Bearer {pair_response.data['access']}"},
    )

    assert response.status_code == HTTPStatus.UNAUTHORIZED
```

**Verify**: JWT bake → `uv run pytest -k deactivated_after_issuance` → 1
passed. If it FAILS with 200, that is itself a significant security result —
STOP and report (do not change the assertion): it means the installed
ninja_jwt version does not re-check `is_active` per request.

### Step 5: Comment the Schemathesis exclusion

In `tests/api/integration/schema_test.py`, above
`_is_third_party_jwt_operation`, add:

```python
# Deliberate exclusion, not an oversight: /token/* operations are owned by
# django-ninja-jwt (schema and behavior come from the library), so the
# contract gate covers only first-party routes. jwt_test.py covers the
# token endpoints functionally.
```

**Verify**: `grep -n "Deliberate exclusion" '{{cookiecutter.project_slug}}/tests/api/integration/schema_test.py'` → 1 match.

### Step 6: Document the maintenance job in the generated README

In `README.md`'s Usage section, extend the existing JWT block (~lines
244-247, anchor on the "JWT endpoints are available at" sentence, not line
numbers). After the endpoints sentence, add — inside the existing
`api_auth == "jwt"` guard:

- When `use_celery == "worker+beat"` (nested Jinja `{% if %}`): one sentence
  noting that refresh-token rotation blacklists old tokens and a scheduled
  `flush-expired-tokens` beat task purges expired rows daily.
- Otherwise (`{% else %}`): the same first clause, plus that operators should
  run `python manage.py flushexpiredtokens` periodically (e.g. host cron or
  a scheduled job) to keep the `token_blacklist` tables bounded.

Remember the JWT block only renders when `use_example_api == "yes"` too —
check what the existing guard around those lines is and nest consistently.

**Verify**: JWT+beat bake README mentions `flush-expired-tokens`; a
`use_example_api=yes api_auth=jwt use_celery=none` bake README mentions
`flushexpiredtokens` cron guidance; the session bake README mentions neither.

### Step 7: Full verification sweep

Run the full baked test suite (with Postgres up) in the JWT bake and the
session bake; run baked `uv run pre-commit run --all-files` in the JWT bake;
run root `uvx pre-commit run --all-files`.

**Verify**: all exit 0; coverage gate (100% branch) holds in both bakes —
the new task is exercised by its test, so no coverage omission is needed.

## Test plan

- `test_flush_expired_tokens_deletes_expired_rows_when_dispatched_eagerly`
  (step 3) — modeled on the session-clearing test in the same file.
- `test_access_token_is_rejected_when_user_deactivated_after_issuance`
  (step 4) — modeled on
  `test_token_pair_access_token_authenticates_notes_request`.
- Verification: `uv run pytest` in JWT and session bakes → all pass; the two
  new tests exist only in JWT bakes.

## Done criteria

Machine-checkable. ALL must hold:

- [ ] JWT bake: `grep -c flush_expired_tokens src/apps/core/tasks.py` ≥ 1; session bake: 0
- [ ] JWT bake: `grep -c "flush-expired-tokens" src/config/settings/components/celery.py` = 1
- [ ] JWT bake: `uv run pytest -k "flush_expired_tokens or deactivated_after_issuance"` → 2 passed
- [ ] Session bake: `uv run pytest` → all pass (no jwt leakage)
- [ ] `grep -n "Deliberate exclusion" '{{cookiecutter.project_slug}}/tests/api/integration/schema_test.py'` → 1 match
- [ ] README verifications from step 6 hold in all three bakes
- [ ] Baked `uv run pre-commit run --all-files` (JWT bake) and root `uvx pre-commit run --all-files` → exit 0
- [ ] `git status` shows no modified files outside the in-scope list
- [ ] `plans/README.md` status row updated

## STOP conditions

Stop and report back (do not improvise) if:

- Step 4's new test observes HTTPStatus.OK — report as a security finding,
  do not weaken the assertion.
- `OutstandingToken.objects.create(...)` in step 3 requires fields beyond
  `expires_at`/`jti`/`token` (e.g. a non-null `created_at` or `user`) — check
  the installed `ninja_jwt/token_blacklist/models.py` and report the actual
  required fields rather than guessing defaults.
- Rendered `tasks_test.py` has unused imports or syntax errors in ANY knob
  combination you bake — Jinja import-block edits are the known hazard here.
- `flushexpiredtokens` is not an available management command in the JWT bake
  (`uv run python manage.py help | grep flush`) — the library layout changed.

## Maintenance notes

- If `api_auth` gains a third value or JWT becomes available without the
  example API, every `use_example_api == "yes" and api_auth == "jwt"` guard
  added here must be revisited (grep for `flush_expired_tokens`).
- Reviewer should scrutinize: Jinja whitespace control in `tasks.py`/
  `tasks_test.py` renders (blank-line count between defs) and the README
  nesting of celery-mode guards inside the jwt guard.
- Deferred: covering `/token/*` with the Schemathesis gate (adjudicated:
  library-owned, deliberately excluded); axes lockout assertion on
  `/token/pair` (the wiring is verified correct in ninja_jwt source; add a
  test only if axes or ninja_jwt is bumped across a major version).
