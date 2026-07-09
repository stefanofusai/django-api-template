# Plan 021: Replace the custom token auth knob with django-ninja-jwt

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving to the
> next step. If anything in the "STOP conditions" section occurs, stop and
> report -- do not improvise. This plan modifies the GENERATED project, so all
> real verification happens inside a bake; never edit a baked tree and call it
> done -- edits go to the template under `{{cookiecutter.project_slug}}/`
> (Jinja), root template files, or `hooks/` as specified. When done, update the
> status row for this plan in `plans/README.md` -- unless a reviewer dispatched
> you and told you they maintain the index.
>
> **Drift check (run first)**:
> `git diff --stat faa9278..HEAD -- cookiecutter.json README.md .github/workflows/ci.yaml scripts/check_generated_format.py hooks/post_gen_project.py '{{cookiecutter.project_slug}}/README.md' '{{cookiecutter.project_slug}}/AGENTS.md' '{{cookiecutter.project_slug}}/pyproject.toml' '{{cookiecutter.project_slug}}/src/apps/api' '{{cookiecutter.project_slug}}/src/apps/core' '{{cookiecutter.project_slug}}/src/apps/notes' '{{cookiecutter.project_slug}}/src/config/settings' '{{cookiecutter.project_slug}}/tests'`
> If any in-scope file changed since this plan was written, compare the
> "Current state" excerpts against the live code before proceeding; on a
> mismatch, treat it as a STOP condition.

## Status

- **Priority**: P2
- **Effort**: L
- **Risk**: MED
- **Depends on**: none; supersedes plans/006-token-lifecycle-endpoints.md and
  the Token-specific part of plans/020-user-token-uuid-pk-and-migration-squash.md
- **Category**: tech-debt / auth
- **Planned at**: commit `faa9278`, 2026-07-09

## Why this matters

The `api_auth=token` mode has grown from a small example auth class into a
bespoke personal-access-token subsystem: `Token` model, migrations, hashed
secret format, expiry, revocation, `last_used_at`, admin minting, lifecycle
endpoints, factories, fixtures, schemas, and many knob-gated tests. That is
security-sensitive code for a starter template to own indefinitely.

Replace that custom mode with a `jwt` mode backed by
`django-ninja-jwt==5.4.4` (latest PyPI release found during planning on
2026-07-09). The generated template should offer only `api_auth=session` and
`api_auth=jwt`; JWT means access/refresh login tokens via the library, not
named long-lived PATs. Long-lived machine tokens are intentionally out of
scope unless a downstream project asks for them.

## Current state

This repo is a **cookiecutter template**. Files under
`{{cookiecutter.project_slug}}/` contain Jinja and cannot be run directly.
Verification means baking projects with the relevant knobs and running their
checks there. Always single-quote paths containing
`{{cookiecutter.project_slug}}` in shell commands.

### Current knob and prompt

`cookiecutter.json` currently offers the old custom mode:

```json
"api_auth": ["session", "token"],
...
"api_auth": {
    "__prompt__": "Authentication used by the example notes API",
    "session": "Django session auth with CSRF",
    "token": "Opaque bearer tokens for non-browser clients"
},
```

Root `README.md` repeats the same meaning in the Variables table:

```markdown
| `api_auth` | `session` | Authentication used by the example notes API: `session` (Django session auth with CSRF) or `token` (opaque bearer tokens); only takes effect when `use_example_api=yes`. |
```

### Current custom token surface to remove

The current rendered token path is guarded by
`use_example_api=yes AND api_auth=token` and includes all of the following:

- `{{cookiecutter.project_slug}}/src/apps/api/auth.py` defines
  `BearerTokenAuth(HttpBearer)` and reads `Token` rows by digest/prefix.
- `{{cookiecutter.project_slug}}/src/apps/api/exceptions.py` defines
  `InvalidTokenError`, used only by the custom token auth path.
- `{{cookiecutter.project_slug}}/src/apps/core/models.py` conditionally imports
  `hashlib`, `secrets`, `datetime`, and `timezone`; defines token constants;
  and defines `Token(CreatedAtModel)` with `expires_at`, `last_used_at`,
  `revoked_at`, `user`, `digest`, `name`, and `prefix`.
- `{{cookiecutter.project_slug}}/src/apps/core/migrations/0002_token.py`
  creates `Token`; `0003_token_revoked_at.py` adds `revoked_at`.
- `{{cookiecutter.project_slug}}/src/apps/core/admin.py` conditionally
  registers `TokenAdmin` and mints raw tokens with `Token.issue()`.
- `{{cookiecutter.project_slug}}/src/apps/core/controllers.py` and
  `{{cookiecutter.project_slug}}/src/apps/core/schemas.py` implement
  `/tokens` create/list/revoke endpoints and schemas.
- `{{cookiecutter.project_slug}}/tests/factories.py`,
  `tests/conftest.py`, `tests/utils.py`, `tests/api/unit/auth_test.py`,
  `tests/core/unit/models_test.py`, `tests/core/integration/admin_test.py`,
  `tests/core/integration/conftest.py`, and
  `tests/core/integration/tokens_test.py` all contain token-specific
  factories, fixtures, helpers, or assertions.

The current `apps.api.auth` excerpt:

```python
class BearerTokenAuth(HttpBearer):
    def authenticate(self, request: HttpRequest, token: str) -> User:
        prefix = Token.prefix_from(token)
        ...
        if (
            stored_token is None
            or stored_token.is_expired
            or stored_token.is_revoked
            or not stored_token.user.is_active
        ):
            raise InvalidTokenError

        stored_token.mark_used()
        request.user = stored_token.user
        return stored_token.user
```

The current `apps.api.api` registers bespoke token endpoints:

```python
{% if cookiecutter.api_auth == "token" -%}
from apps.core.controllers import TokensController
{% endif -%}
...
v1_api.register_controllers(NotesController)
{%- if cookiecutter.api_auth == "token" %}
v1_api.register_controllers(TokensController)
{%- endif %}
```

The current notes controller switches between session auth and the custom
bearer-token auth:

```python
{% if cookiecutter.api_auth == "token" -%}
from apps.api.auth import bearer_token_auth
{% endif -%}
...
@api_controller(
    "/notes",
    auth={% if cookiecutter.api_auth == "token" %}bearer_token_auth{% else %}django_auth{% endif %},
    tags=["notes"],
)
```

### Current hook and matrix references to update

`hooks/post_gen_project.py` removes token-only files when the old mode is not
active:

```python
[
    "src/apps/api/auth.py",
    "src/apps/api/exceptions.py",
    "src/apps/core/controllers.py",
    "src/apps/core/migrations/0002_token.py",
    "src/apps/core/migrations/0003_token_revoked_at.py",
    "src/apps/core/schemas.py",
    "tests/api/unit/auth_test.py",
    "tests/core/integration/tokens_test.py",
]
if not (USE_EXAMPLE_API == "yes" and API_AUTH == "token")
else []
```

Root CI and root generated-format still bake token combos:

```yaml
- case: example-token-auth
  extra-args: use_example_api=yes api_auth=token
- case: example-token-auth-throttling
  extra-args: use_example_api=yes api_auth=token api_throttling=basic
```

```python
"maximal": [
    "use_example_api=yes",
    "api_auth=token",
    "api_throttling=basic",
    "use_cors=yes",
    "use_csp=yes",
],
```

### django-ninja-jwt facts from current docs

The current docs for `django-ninja-jwt` show:

- add `ninja_jwt` and optionally `ninja_jwt.token_blacklist` to
  `INSTALLED_APPS`;
- configure `NINJA_JWT` with token lifetimes, signing key, refresh rotation,
  and blacklist-after-rotation settings;
- use `JWTAuth()` to protect endpoints;
- register `NinjaJWTDefaultController` on a `NinjaExtraAPI` to expose
  `/token/pair`, `/token/refresh`, and `/token/verify`;
- register `TokenBlackListController` and install
  `ninja_jwt.token_blacklist` to expose `/token/blacklist`.

Reference docs:

- <https://eadwincode.github.io/django-ninja-jwt/>
- <https://pypi.org/project/django-ninja-jwt/> (`5.4.4`, released January
  2026, verified during planning)

## Commands you will need

| Purpose | Command | Expected on success |
|---------|---------|---------------------|
| Search old knob refs | `grep -rn 'api_auth.*token\\|api_auth=token\\|BearerTokenAuth\\|TokensController\\|TokenFactory\\|0002_token\\|0003_token_revoked_at' . --exclude-dir=.git` | no live source/docs refs except archived/superseded plan text |
| Bake JWT combo | `uvx cookiecutter . -o /tmp/verify-021-jwt --no-input use_example_api=yes api_auth=jwt` | project at `/tmp/verify-021-jwt/my-project` |
| Bake JWT throttling combo | `uvx cookiecutter . -o /tmp/verify-021-jwt-throttle --no-input use_example_api=yes api_auth=jwt api_throttling=basic` | project generated |
| Bake session combo | `uvx cookiecutter . -o /tmp/verify-021-session --no-input use_example_api=yes api_auth=session` | project generated |
| Bake no-example combo | `uvx cookiecutter . -o /tmp/verify-021-default --no-input` | project generated, no JWT dependency/app |
| Install deps (in each bake) | `uv sync --locked` | exit 0 |
| Start Postgres (in each bake that runs tests) | `cp .env.example .env && docker compose -f .docker/compose/dev.yaml --env-file=.env up -d --wait postgres` | postgres healthy |
| Migration completeness | `uv run manage.py makemigrations --check --dry-run` | exit 0, "No changes detected" |
| Migration linter | `uv run manage.py lintmigrations` | exit 0 |
| Full suite | `uv run pytest` | all pass, 100% coverage |
| Generated pre-commit | `uv run pre-commit run --all-files` | exit 0 |
| Root checks | `uvx pre-commit run --all-files` | exit 0 |
| Teardown | `docker compose -f .docker/compose/dev.yaml --env-file=.env down -v` | exit 0 |

Prefix commands with `rtk` when available.

## Scope

**In scope**:

- `cookiecutter.json` -- replace `token` with `jwt` and update prompt text.
- Root `README.md` -- update the Variables table and any feature/design text
  that describes opaque bearer tokens.
- `.github/workflows/ci.yaml` -- rename/update token bake cases to JWT.
- `scripts/check_generated_format.py` -- update the maximal combo to
  `api_auth=jwt`.
- `hooks/post_gen_project.py` -- replace token-only pruning with JWT-only
  pruning and remove paths for deleted token files.
- `{{cookiecutter.project_slug}}/pyproject.toml` -- add
  `django-ninja-jwt==5.4.4` under the `use_example_api=yes AND api_auth=jwt`
  condition; remove the token-only direct `pydantic` dependency unless another
  direct import remains; update deptry ignores if required.
- `{{cookiecutter.project_slug}}/src/config/settings/__init__.py` and a new
  `components/jwt.py` -- include `NINJA_JWT` only for JWT bakes.
- `{{cookiecutter.project_slug}}/src/config/settings/components/apps.py` --
  add `ninja_jwt` and `ninja_jwt.token_blacklist` only for JWT bakes.
- `{{cookiecutter.project_slug}}/src/apps/api/api.py` -- register
  `NinjaJWTDefaultController` and `TokenBlackListController` only for JWT
  bakes; delete `TokensController` imports/registration.
- `{{cookiecutter.project_slug}}/src/apps/api/auth.py` -- replace the custom
  auth class with a small `JWTAuth()` wrapper/export, or delete this file and
  import `JWTAuth` directly from notes; prefer keeping `jwt_auth` here for a
  stable local import point.
- `{{cookiecutter.project_slug}}/src/apps/notes/controllers.py` -- replace
  `api_auth == "token"` branches with `api_auth == "jwt"` branches using JWT
  auth.
- Delete obsolete token files:
  `src/apps/api/exceptions.py`, `src/apps/core/controllers.py`,
  `src/apps/core/schemas.py`,
  `src/apps/core/migrations/0002_token.py`,
  `src/apps/core/migrations/0003_token_revoked_at.py`,
  `tests/api/unit/auth_test.py`,
  `tests/core/integration/conftest.py`,
  `tests/core/integration/tokens_test.py`.
- Clean token-specific blocks from `src/apps/core/models.py`,
  `src/apps/core/admin.py`, `tests/factories.py`, `tests/conftest.py`,
  `tests/utils.py`, `tests/core/unit/models_test.py`,
  `tests/core/integration/admin_test.py`,
  `tests/notes/unit/controllers_test.py`, generated `AGENTS.md`, and generated
  `README.md`.
- Add focused JWT integration tests, preferably
  `{{cookiecutter.project_slug}}/tests/api/integration/jwt_test.py`, covering
  pair, refresh, blacklist, inactive-user rejection, and a protected notes
  request with an access token.

**Out of scope**:

- Do not keep both `token` and `jwt` modes. The maintenance win comes from
  deleting the custom token subsystem.
- Do not reimplement named personal access tokens on top of JWT claims.
- Do not add registration/signup/password-reset flows; this plan only replaces
  the example API authentication mode.
- Do not change `api_auth=session` behavior except where shared test helpers
  must stay compatible.
- Do not complete plans 006 or 020 as written. They are superseded by this
  plan's direction.
- Do not edit `{{cookiecutter.project_slug}}/.agents/*`; those paths are
  `_copy_without_render` and unrelated.

## Git workflow

- Branch: `advisor/021-replace-token-auth-with-jwt`.
- Commit per logical unit is fine, but keep the tree green between commits if
  possible. Suggested split: knob/dependency/settings, auth/controller wiring,
  test/helper cleanup, docs/matrix updates.
- Message style: conventional commits, e.g.
  `refactor: replace custom token auth with django-ninja-jwt`.
- Do NOT push or open a PR unless the operator instructed it.

## Steps

### Step 1: Rename the knob from `token` to `jwt`

In `cookiecutter.json`, change:

```json
"api_auth": ["session", "token"]
```

to:

```json
"api_auth": ["session", "jwt"]
```

Update the prompt entry to describe JWT access/refresh tokens via
`django-ninja-jwt`. Then update root `README.md`, generated `README.md`, root
CI, and `scripts/check_generated_format.py` so every active bake/docs
reference uses `api_auth=jwt`, not `api_auth=token`.

**Verify**:

```shell
grep -rn 'api_auth=token\\|api_auth.*token' cookiecutter.json README.md .github/workflows/ci.yaml scripts/check_generated_format.py '{{cookiecutter.project_slug}}/README.md'
```

Expected: no matches except explanatory superseded text in `plans/`.

### Step 2: Add django-ninja-jwt dependency and settings

In `{{cookiecutter.project_slug}}/pyproject.toml`, add:

```toml
{%- if cookiecutter.use_example_api == "yes" and cookiecutter.api_auth == "jwt" %}
    "django-ninja-jwt==5.4.4",
{%- endif %}
```

Remove the old token-only direct `pydantic==...` dependency unless another
direct `from pydantic import ...` import remains in generated source. If deptry
flags `django-ninja-jwt` as unused because it is loaded through
`INSTALLED_APPS`, add a `DEP002` ignore comment matching the existing style.

In `settings/components/apps.py`, add under the Third-party block, guarded by
`use_example_api=yes AND api_auth=jwt`:

```python
    "ninja_jwt",
    "ninja_jwt.token_blacklist",
```

Create `settings/components/jwt.py` with fixed starter settings:

```python
from datetime import timedelta

NINJA_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=15),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": True,
    "SIGNING_KEY": SECRET_KEY,  # noqa: F821  # ty: ignore[unresolved-reference]
}
```

Add `"components/jwt.py"` to `settings_files` in
`settings/__init__.py`, guarded by the same JWT condition and after
`components/authentication.py`.

**Verify** in a JWT bake:

```shell
uvx cookiecutter . -o /tmp/verify-021-jwt --no-input use_example_api=yes api_auth=jwt
cd /tmp/verify-021-jwt/my-project
uv sync --locked
uv run python - <<'PY'
import django
from django.conf import settings
django.setup()
assert "ninja_jwt" in settings.INSTALLED_APPS
assert "ninja_jwt.token_blacklist" in settings.INSTALLED_APPS
assert settings.NINJA_JWT["BLACKLIST_AFTER_ROTATION"] is True
PY
```

Expected: exit 0.

### Step 3: Replace custom auth wiring with JWTAuth

Replace `{{cookiecutter.project_slug}}/src/apps/api/auth.py` with a JWT-only
local auth instance:

```python
from ninja_jwt.authentication import JWTAuth

jwt_auth = JWTAuth()
```

Keep this file only when `use_example_api=yes AND api_auth=jwt`; otherwise
`hooks/post_gen_project.py` should remove it.

In `apps/notes/controllers.py`, change token guards to JWT guards and use
`jwt_auth`:

```python
{% if cookiecutter.api_auth == "jwt" -%}
from apps.api.auth import jwt_auth
{% endif -%}
...
auth={% if cookiecutter.api_auth == "jwt" %}jwt_auth{% else %}django_auth{% endif %},
```

In `apps/api/api.py`, delete all `TokensController` imports/registration and
register library controllers only for JWT bakes:

```python
{% if cookiecutter.api_auth == "jwt" -%}
from ninja_jwt.controller import NinjaJWTDefaultController, TokenBlackListController
{% endif -%}
...
{%- if cookiecutter.api_auth == "jwt" %}
v1_api.register_controllers(NinjaJWTDefaultController)
v1_api.register_controllers(TokenBlackListController)
{%- endif %}
v1_api.register_controllers(NotesController)
```

If the import path for `TokenBlackListController` differs in
`django-ninja-jwt==5.4.4`, STOP and report the actual import path from the
installed package instead of guessing.

**Verify** in a JWT bake:

```shell
uv run manage.py check
uv run python manage.py shell -c 'from apps.api.api import v1_api; schema = v1_api.get_openapi_schema(); assert "/token/pair" in schema["paths"]; assert "/token/refresh" in schema["paths"]; assert "/token/blacklist" in schema["paths"]'
```

Expected: `manage.py check` reports no issues, and all three JWT paths exist.

### Step 4: Delete the custom Token model and token lifecycle files

In `core/models.py`, remove all token-only imports, constants, and the
`Token` class. Keep `CreatedAtModel`, `CreatedAtUpdatedAtModel`, `UUIDModel`,
and `User` intact.

In `core/admin.py`, remove the token-only imports and `TokenAdmin`; leave only
`UserAdmin`.

Delete these template files:

```shell
rm '{{cookiecutter.project_slug}}/src/apps/api/exceptions.py'
rm '{{cookiecutter.project_slug}}/src/apps/core/controllers.py'
rm '{{cookiecutter.project_slug}}/src/apps/core/schemas.py'
rm '{{cookiecutter.project_slug}}/src/apps/core/migrations/0002_token.py'
rm '{{cookiecutter.project_slug}}/src/apps/core/migrations/0003_token_revoked_at.py'
rm '{{cookiecutter.project_slug}}/tests/api/unit/auth_test.py'
rm '{{cookiecutter.project_slug}}/tests/core/integration/conftest.py'
rm '{{cookiecutter.project_slug}}/tests/core/integration/tokens_test.py'
```

Update `hooks/post_gen_project.py`: remove all deleted-file paths from
`REMOVED_PATHS`. Add a JWT-only removal entry only for files that still exist
solely for JWT, such as `src/apps/api/auth.py` and the new JWT integration
test, using:

```python
if not (USE_EXAMPLE_API == "yes" and API_AUTH == "jwt")
```

**Verify**:

```shell
grep -rn 'class Token\\|TokenAdmin\\|TokensController\\|BearerTokenAuth\\|InvalidTokenError\\|0002_token\\|0003_token_revoked_at' '{{cookiecutter.project_slug}}' hooks/post_gen_project.py
```

Expected: no matches.

### Step 5: Rewrite factories, fixtures, and test helpers for JWT

In `tests/factories.py`, remove `TokenFactory` and `TEST_TOKEN_SECRET`. Keep
`UserFactory` and `NoteFactory`.

In `tests/conftest.py`, remove token fixtures (`raw_token`, `auth_raw_token`,
`token_auth_headers`, `revoked_token`) and `TokenFactory` registrations. Add a
JWT-header fixture guarded by `use_example_api=yes AND api_auth=jwt`:

```python
from ninja_jwt.tokens import RefreshToken
...
@pytest.fixture
def jwt_auth_headers(user: User) -> dict[str, str]:
    refresh = RefreshToken.for_user(user)
    return {"Authorization": f"Bearer {refresh.access_token}"}
```

Update `authenticated_v1_api_client` and `tests/utils.py` so JWT bakes pass
headers, while session bakes keep passing `user=...` to the Ninja test client.

In `tests/notes/unit/controllers_test.py`, replace `raw_token` with JWT
headers for the JWT branch. If a test needs a token for `note.owner`, create
it with `RefreshToken.for_user(note.owner)` in that test or through a helper
fixture; do not reintroduce `Token` model fixtures.

In `tests/core/unit/models_test.py` and
`tests/core/integration/admin_test.py`, delete token-specific tests and keep
the `User`/admin tests.

**Verify** in session and JWT bakes:

```shell
uv run pytest tests/core tests/notes --no-cov
```

Expected: all pass in both bakes.

### Step 6: Add JWT endpoint integration tests

Create `{{cookiecutter.project_slug}}/tests/api/integration/jwt_test.py`,
guarded so it exists only for `use_example_api=yes AND api_auth=jwt`. Cover:

1. `POST /token/pair` with a user's username/password returns `200` and both
   `access` and `refresh`.
2. `GET /notes` with `Authorization: Bearer <access>` returns `200`.
3. `POST /token/refresh` with the refresh token returns `200` and a new
   `access`.
4. `POST /token/blacklist` with the refresh token returns `200`.
5. Refreshing a blacklisted refresh token is rejected.
6. An inactive user cannot obtain a token pair.

Set a real password in the test with `user.set_password("correct-password")`
and `user.save(update_fields=("password",))`; do not rely on `UserFactory`
having a password.

Use existing integration-test style: `HTTPStatus`, `v1_api_client`, factory
fixtures, and direct `response.data` assertions.

**Verify**:

```shell
uv run pytest tests/api/integration/jwt_test.py tests/notes --no-cov
```

Expected: all pass.

### Step 7: Update generated docs and AGENTS guidance

In generated `README.md`, replace the old
`bearer-token-authenticated` wording with JWT wording and mention the
available `/token/pair`, `/token/refresh`, `/token/verify`, and
`/token/blacklist` endpoints in the example API docs section.

In generated `AGENTS.md`, remove token-model-specific guidance about
`Token.is_expired`, `Token.is_revoked`, `Token.mark_used()`,
`BearerTokenAuth`, and `InvalidTokenError`. Add one short JWT-specific rule:
the example JWT mode uses `django-ninja-jwt`, `apps.api.auth.jwt_auth`, and
the library controllers; do not add custom credential storage unless a project
explicitly needs personal access tokens.

**Verify**:

```shell
grep -rn 'BearerTokenAuth\\|InvalidTokenError\\|Token\\.is_expired\\|Token\\.is_revoked\\|Token.mark_used\\|bearer-token-authenticated' '{{cookiecutter.project_slug}}/README.md' '{{cookiecutter.project_slug}}/AGENTS.md'
```

Expected: no matches.

### Step 8: Full bake-matrix verification

Run the full checks for at least these four rendered combinations:

1. default: `uvx cookiecutter . -o /tmp/verify-021-default --no-input`
2. session example: `uvx cookiecutter . -o /tmp/verify-021-session --no-input use_example_api=yes api_auth=session`
3. JWT example: `uvx cookiecutter . -o /tmp/verify-021-jwt --no-input use_example_api=yes api_auth=jwt`
4. JWT + throttling maximal: `uvx cookiecutter . -o /tmp/verify-021-jwt-throttle --no-input use_example_api=yes api_auth=jwt api_throttling=basic use_cors=yes use_csp=yes`

In each bake, run:

```shell
uv sync --locked
cp .env.example .env
docker compose -f .docker/compose/dev.yaml --env-file=.env up -d --wait postgres
uv run manage.py makemigrations --check --dry-run
uv run manage.py lintmigrations
uv run pytest
uv run pre-commit run --all-files
docker compose -f .docker/compose/dev.yaml --env-file=.env down -v
```

Finally run root pre-commit:

```shell
uvx pre-commit run --all-files
```

**Verify**: all commands exit 0.

## Test plan

New tests:

- `tests/api/integration/jwt_test.py` for token pair, refresh, blacklist,
  inactive-user rejection, and using an access token against `/notes`.

Updated tests:

- `tests/notes/**` should keep all existing session and authenticated behavior,
  switching only the JWT branch's auth header production.
- `tests/core/unit/models_test.py` should keep `User` coverage after token
  tests are deleted.
- `tests/core/integration/admin_test.py` should keep user/admin coverage after
  `TokenAdmin` tests are deleted.

Verification is the rendered full suite at 100% coverage in session and JWT
bakes plus generated pre-commit.

## Done criteria

- [ ] `cookiecutter.json` offers `api_auth=["session", "jwt"]`; no active
      template docs or commands mention `api_auth=token`.
- [ ] `django-ninja-jwt==5.4.4` is gated into JWT example bakes, and
      `ninja_jwt` plus `ninja_jwt.token_blacklist` are installed apps only
      there.
- [ ] `NINJA_JWT` is configured with 15-minute access tokens, 7-day refresh
      tokens, refresh rotation, blacklist-after-rotation, and
      `SIGNING_KEY=SECRET_KEY`.
- [ ] `Token`, `TokenAdmin`, `BearerTokenAuth`, `TokensController`,
      token schemas, token migrations, token factories, and token lifecycle
      tests are gone.
- [ ] JWT bakes expose `/token/pair`, `/token/refresh`, `/token/verify`, and
      `/token/blacklist`.
- [ ] Session, JWT, JWT+throttling, and default bakes pass
      `makemigrations --check --dry-run`, `lintmigrations`, `pytest` at 100%
      coverage, and generated `pre-commit`.
- [ ] Root `uvx pre-commit run --all-files` exits 0.
- [ ] `plans/README.md` status row updated; plans 006 and 020 remain marked
      superseded/rejected unless the maintainer explicitly revives a User-only
      UUID plan later.

## STOP conditions

Stop and report back if:

- `django-ninja-jwt==5.4.4` does not install or import cleanly with the
  template's Django 6.0.6, Django Ninja 1.6.2, Django Ninja Extra 0.31.5, or
  Python 3.14 stack.
- `TokenBlackListController` is not importable from the documented controller
  module, or registering it does not expose `/token/blacklist`.
- `NinjaJWTDefaultController` or `TokenBlackListController` emits nondeterministic
  operation ids that would break plan 017's OpenAPI drift gate; report the
  rendered schema and decide whether a small local subclass is required before
  proceeding.
- Removing `Token` requires touching unrelated app behavior outside the
  in-scope files.
- Any bake still renders a dangling import of `Token`, `BearerTokenAuth`,
  `InvalidTokenError`, `TokenFactory`, `raw_token`, or `api_auth == "token"`.
- A verification failure appears to be a library compatibility bug rather than
  a template wiring mistake.

## Maintenance notes

- This plan intentionally changes semantics: `jwt` is access/refresh
  login-token auth, not named long-lived personal access tokens. Access-token
  revocation remains bounded by the access-token lifetime; refresh-token
  rotation/blacklisting handles logout and refresh-token reuse.
- If a downstream project later needs GitHub-style named PATs, write a new
  plan for that project. Do not quietly rebuild the deleted custom token model
  inside this template.
- Plan 017 (OpenAPI drift gate) must account for JWT routes when it lands
  after this plan. Verify the committed `openapi-v1.json` includes stable
  operation ids for `/token/*`.
- Plan 020 should not be executed as written after this plan. If the maintainer
  still wants UUID primary keys for `User` and a notes migration squash, write
  a new User-only migration-squash plan that does not mention `Token`.
