# Plan 002: Reject bearer tokens of deactivated users

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving to the
> next step. If anything in the "STOP conditions" section occurs, stop and
> report — do not improvise. When done, update the status row for this plan
> in `plans/README.md` — unless a reviewer dispatched you and told you they
> maintain the index.
>
> **Drift check (run first)**:
> `git diff --stat eee3978..HEAD -- '{{cookiecutter.project_slug}}/src/apps/api/auth.py' '{{cookiecutter.project_slug}}/tests/api/unit/auth_test.py'`
> If any in-scope file changed since this plan was written, compare the
> "Current state" excerpts against the live code before proceeding; on a
> mismatch, treat it as a STOP condition.

## Status

- **Priority**: P1
- **Effort**: S
- **Risk**: LOW
- **Depends on**: none (coordinate with plan 001 if executing concurrently —
  different files, no conflict expected)
- **Category**: security
- **Planned at**: commit `eee3978`, 2026-07-08

## Why this matters

Setting `is_active=False` on a Django user is the standard
offboarding/suspension action, and the template's session auth honors it
(`ModelBackend.user_can_authenticate` rejects inactive users, so they get
401). The bearer-token path does not: a deactivated user's existing tokens
keep authenticating and can read/create/update/delete their notes. Anyone
using this template with `api_auth=token` inherits a revocation gap where
"deactivate the user" silently fails to cut API access.

## Current state

This repo is a **cookiecutter template**; both in-scope files render only when
`use_example_api=yes AND api_auth=token` (any other combination has them
deleted by `hooks/post_gen_project.py`). The two in-scope files happen to be
Jinja-free plain Python, so you can edit them directly, but verification
still means baking. Always single-quote paths containing
`{{cookiecutter.project_slug}}` in shell commands.

`{{cookiecutter.project_slug}}/src/apps/api/auth.py` (entire current file):

```python
from typing import TYPE_CHECKING

from ninja.security import HttpBearer

from apps.api.exceptions import InvalidTokenError
from apps.core.models import Token, User

if TYPE_CHECKING:
    from django.http import HttpRequest


class BearerTokenAuth(HttpBearer):
    def authenticate(self, request: HttpRequest, token: str) -> User:
        prefix = Token.prefix_from(token)

        if prefix is None:
            raise InvalidTokenError

        stored_token = (
            Token.objects.select_related("user")
            .filter(digest=Token.hash(token), prefix=prefix)
            .first()
        )

        if stored_token is None or stored_token.is_expired():
            raise InvalidTokenError

        stored_token.mark_used()
        request.user = stored_token.user
        return stored_token.user


bearer_token_auth = BearerTokenAuth()
```

Notes:
- `select_related("user")` already loads the user, so checking `is_active`
  costs no extra query (this matters — the suite runs django-zeal, an N+1
  guard, and the repo treats query-count hygiene as a hard rule).
- `InvalidTokenError` (in `src/apps/api/exceptions.py`) produces a 401.
- Existing tests: `{{cookiecutter.project_slug}}/tests/api/unit/auth_test.py`
  has four tests; the structural pattern to copy is
  `test_authenticate_raises_401_when_token_is_expired` (lines 29-43): issue a
  token via `Token.issue(...)`, call
  `BearerTokenAuth().authenticate(mocker.Mock(), raw_token)`, assert
  `InvalidTokenError` with `exc_info.value.status_code == HTTPStatus.UNAUTHORIZED`.
  The `user` fixture comes from pytest-factoryboy's registered `UserFactory`
  (`tests/factories.py`); override fields with
  `@pytest.mark.parametrize("user__is_active", [False])` — the repo already
  uses this exact override style in
  `tests/core/integration/admin_test.py` (`user__is_staff`).

Repo conventions: alphabetize where order doesn't matter; blank lines around
control-flow branches; tests named `test_<unit>_<behavior>_when_<condition>`;
conventional commits.

## Commands you will need

| Purpose | Command | Expected on success |
|---------|---------|---------------------|
| Bake the combo | `uvx cookiecutter . -o /tmp/verify-002 --no-input use_example_api=yes api_auth=token` | project at `/tmp/verify-002/my-project` |
| Start Postgres (in bake) | `cp .env.example .env && docker compose -f .docker/compose/dev.yaml --env-file=.env up -d --wait postgres` | postgres healthy |
| Suite (in bake) | `uv sync --locked && uv run pytest` | all pass, 100% coverage |
| Targeted (in bake) | `uv run pytest tests/api/unit/auth_test.py --no-cov` | all pass incl. new test |
| Lint/format (in bake) | `uvx ruff@0.15.16 format --check . && uvx ruff@0.15.16 check .` | exit 0 |
| Teardown | `docker compose -f .docker/compose/dev.yaml --env-file=.env down -v` | exit 0 |

## Scope

**In scope** (the only files you should modify):
- `{{cookiecutter.project_slug}}/src/apps/api/auth.py`
- `{{cookiecutter.project_slug}}/tests/api/unit/auth_test.py`

**Out of scope** (do NOT touch, even though they look related):
- `src/apps/core/models.py` (`Token.is_expired`) — expiry semantics are
  separate from user state; don't fold the check into the model.
- Session-auth or axes configuration — already correct.
- `src/apps/api/throttling.py` and its tests — unrelated.

## Git workflow

- Branch: `advisor/002-token-auth-inactive-users`
- Single commit, e.g. `fix: reject bearer tokens of inactive users`.
- Do NOT push or open a PR unless the operator instructed it.

## Steps

### Step 1: Add the is_active guard

In `auth.py`, extend the rejection condition:

```python
        if (
            stored_token is None
            or stored_token.is_expired()
            or not stored_token.user.is_active
        ):
            raise InvalidTokenError
```

(Formatting note: the three-clause condition exceeds 88 chars on one line, so
the wrapped form above is what `ruff format` produces — verify rather than
assume.)

**Verify**: in a fresh bake (see commands),
`uvx ruff@0.15.16 format --check . && uvx ruff@0.15.16 check .` → exit 0.

### Step 2: Add the regression test

In `tests/api/unit/auth_test.py`, add (positioned among the
`test_authenticate_raises_401_*` tests, matching the file's existing ordering
convention):

```python
@pytest.mark.parametrize("user__is_active", [False])
def test_authenticate_raises_401_when_user_is_inactive(
    mocker: MockerFixture,
    user: User,
) -> None:
    raw_token, _ = Token.issue(name="test token", user=user)
    auth = BearerTokenAuth()

    with pytest.raises(InvalidTokenError) as exc_info:
        auth.authenticate(mocker.Mock(), raw_token)

    assert exc_info.value.status_code == HTTPStatus.UNAUTHORIZED
```

**Verify**: in the bake, `uv run pytest tests/api/unit/auth_test.py --no-cov`
→ 5 tests pass.

### Step 3: Full-suite verification

**Verify**: in the bake with Postgres up, `uv run pytest` → all pass at 100%
coverage (the new branch in auth.py must be covered — the new test covers it;
if coverage reports a missed branch, the guard was written in a shape the
test doesn't reach: STOP).

## Test plan

- New test: `test_authenticate_raises_401_when_user_is_inactive` in
  `tests/api/unit/auth_test.py`, modeled on
  `test_authenticate_raises_401_when_token_is_expired` (same file, lines
  29-43). Covers: valid unexpired token + `is_active=False` → 401.
- Existing tests must keep passing unchanged (active-user paths).
- Verification: `uv run pytest` in the `use_example_api=yes api_auth=token`
  bake → all pass, 100% coverage.

## Done criteria

Machine-checkable. ALL must hold:

- [ ] Baked `uv run pytest` exits 0 at 100% coverage, including the new test
- [ ] Baked `uvx ruff@0.15.16 format --check .` and `check .` exit 0
- [ ] `grep -n "is_active" '{{cookiecutter.project_slug}}/src/apps/api/auth.py'`
      returns exactly one match inside the rejection condition
- [ ] `git status --short` shows changes ONLY to the two in-scope files
- [ ] `plans/README.md` status row updated

## STOP conditions

Stop and report back (do not improvise) if:

- `auth.py` no longer matches the excerpt (drifted).
- The full suite fails on a test OTHER than ones you added — likely plan 001's
  regressions if it hasn't landed yet; report which test failed. (A
  `ruff format` failure on `tests/core/integration/admin_test.py` or
  `tests/api/integration/throttling_test.py` in the baked pre-commit is plan
  001's known defect, not yours — note it and continue, but say so in your
  report.)
- django-zeal flags an N+1 anywhere after your change — the guard must not
  add queries; report the zeal output.

## Maintenance notes

- If token *lifecycle endpoints* land later (see plan 006), their
  list/revoke queries must apply the same `user.is_active` semantics.
- Reviewer: confirm the check reads `stored_token.user` (the select_related
  object), not a fresh `User` query.
- Deliberately NOT changed: expired-token and inactive-user rejections are
  indistinguishable to the client (both 401 `InvalidTokenError`) — that's
  correct; don't leak which condition failed.
