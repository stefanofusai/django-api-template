# Plan 013 Design: `api_auth` knob for non-browser API auth

## Recommendation

Add a narrow opt-in `api_auth` knob for the example API, with two choices:

```json
"api_auth": ["session", "token"]
```

Default to `session` to preserve today's rendered behavior:
`use_example_api=yes` keeps the notes router on Django session auth and
`use_example_api=no` keeps `/api/v1/` empty. When `api_auth=token` and
`use_example_api=yes`, render a no-dependency opaque bearer-token example using
`ninja.security.HttpBearer`, a DB-backed token model, and tests that issue a
real token and send `Authorization: Bearer ...`.

Do not make JWT or API-key auth the default worked example. JWT currently adds
dependency and compatibility risk, while API keys are a different
service-to-service story. Both can be documented as future extensions after the
maintainer accepts whether auth belongs in the template at all.

## Drift Check

Required command:

```bash
git diff --stat ae42991..HEAD -- "{{cookiecutter.project_slug}}/src/apps/notes/routes.py" "{{cookiecutter.project_slug}}/src/config/settings/components/authentication.py" "{{cookiecutter.project_slug}}/pyproject.toml"
```

Output was empty. The spike plan's "Current state" still matches the live code:

- `apps/notes/routes.py` uses `django_auth` on the notes router.
- `authentication.py` has the custom `core.User`, password hashers, and no token
  model or JWT dependency.
- `pyproject.toml` depends on `django-ninja==1.6.2` and has no auth-token or JWT
  package.

## Mechanism Comparison

| Mechanism | Dependency weight | Statelessness | Revocation | Custom-user fit | Recommendation |
|-----------|-------------------|---------------|------------|-----------------|----------------|
| Opaque DB token with `HttpBearer` | No new package; uses Django + Ninja already pinned | Stateful DB lookup per request | Straightforward: delete or disable token row | Direct FK to `core.User`; can set `request.user` for existing notes ownership checks | Use as the default token example |
| JWT via `django-ninja-jwt` | Adds `django-ninja-jwt`, `django-ninja-extra`, `pydantic-settings`, `pyjwt` | Stateless access tokens; refresh-token state optional | Harder unless blacklist/rotation is added | Works with Django users, but introduces controller/settings surface | Do not default to this now |
| `APIKeyHeader` API keys | No new package if hand-rolled | Stateful if hashed in DB | Straightforward if DB-backed | Better for service identities than end-user notes ownership | Future service-to-service option |

Current package check for JWT:

- PyPI lists `django-ninja-jwt` latest as `5.4.4`, released January 22, 2026:
  <https://pypi.org/project/django-ninja-jwt/>
- Its PyPI metadata declares `requires_python >=3.7`, but classifiers stop at
  Python 3.12 and Django 4.1. It does not declare Django 6 or Python 3.14
  support.
- Its requirements include `Django>=2.1`, `django-ninja-extra>=0.30.5`,
  `pydantic-settings>=2.0.0`, and `pyjwt`.
- Its docs show the default controller path using `NinjaExtraAPI`:
  <https://eadwincode.github.io/django-ninja-jwt/>
- Django 6 itself supports Python 3.12, 3.13, and 3.14:
  <https://docs.djangoproject.com/en/6.0/releases/6.0/>

That is not a hard proof that JWT cannot work, but it is enough uncertainty for
this template's pinned, verified dependency posture. The no-dependency
`HttpBearer` path avoids the compatibility wall.

## Design Questions

### 1. Which mechanism?

Use `HttpBearer` plus an opaque DB-backed token. Store only a SHA-256 digest,
return the raw token once at issue time, and resolve the request with a single
indexed lookup:

```python
api_token = Token.objects.select_related("user").get(digest=Token.hash(token))
request.user = api_token.user
return api_token.user
```

This keeps the example small, revocable, and aligned with the existing
ownership checks (`owner=request.user`). It also keeps OpenAPI's bearer security
scheme in Ninja's native path.

### 2. Knob shape and default

Recommended `cookiecutter.json` addition:

```json
"api_auth": ["session", "token"]
```

Recommended prompt:

```json
"api_auth": {
    "__prompt__": "Authentication used by the example notes API",
    "session": "Django session auth with CSRF, matching today's behavior",
    "token": "Opaque bearer tokens for non-browser clients"
}
```

Default `session` avoids changing existing generated projects and is clearer
than `none`, because the current notes example is authenticated today.

### 3. Composition with `use_example_api`

| `use_example_api` | `api_auth` | Rendered `/api/v1/` behavior | CI coverage |
|-------------------|------------|-------------------------------|-------------|
| `no` | `session` | Empty v1 API, current behavior | Existing default/minimal bakes |
| `no` | `token` | Empty v1 API; token auth files should be removed or not rendered | Optional negative bake to ensure no stray token files |
| `yes` | `session` | Notes router uses `django_auth`, current behavior | Existing example bake |
| `yes` | `token` | Notes router uses bearer tokens; tests issue real tokens | New required bake case |

The prompt can say "example notes API" because this should not pretend to be a
full authentication product for every future endpoint. If the maintainer wants
token auth scaffolding even when `use_example_api=no`, that is a broader
product decision and should be answered before implementation.

### 4. Credential provisioning

Minimum viable scope: include a management command to mint tokens, not login or
registration endpoints.

Recommended command shape for the follow-up build plan:

```bash
uv run python manage.py create_api_token --user-email=person@example.com --name="CLI"
```

The command should print the raw token exactly once. This gives CLIs and
backend integrations a real provisioning path without pulling registration,
password reset, refresh tokens, or mobile login flows into this knob.

Open question: whether the maintainer wants a token-issue endpoint. That endpoint
is useful for mobile/user clients, but it implies password credential exchange,
rate limits, lockout policy, and documentation beyond this template's current
minimalism.

### 5. Testing

Add a parallel real-token test helper rather than reusing Ninja's `user=`
injection:

```python
self.raw_token, self.token = Token.issue(name="test token", user=user)
return self._client.get(path, headers={"Authorization": f"Bearer {self.raw_token}"})
```

Required test coverage in a follow-up build:

- token issue stores a digest and never stores the raw token;
- valid bearer token reaches notes endpoints as the token owner;
- unknown bearer token returns `401`;
- anonymous request still returns `401`;
- ownership filtering remains unchanged;
- OpenAPI schema includes bearer auth for token mode.

Schemathesis can stay green in the first build because unauthenticated generated
requests validate the documented `401` responses. If plan 011 later adds an
authenticated contract pass, token mode should inject a bearer header instead of
session plus CSRF.

### 6. Dependencies and migrations

No new dependency for the recommended path.

The PoC placed `Token` in `apps.core` next to the custom user. That is the
smallest implementation, but the follow-up build should make a final choice:

- `apps.core.Token`: fewer files, direct proximity to `User`, but adds Jinja
  conditionals to `core/models.py`, `core/admin.py`, and `core` migrations.
- `apps.tokens.Token`: cleaner hook deletion (`REMOVED_DIRS`) and less Jinja in
  core, but one more app for a small example.

I recommend `apps.core.Token` only if `api_auth=token` is scoped to
`use_example_api=yes`; otherwise use a dedicated `apps.tokens` app so
`api_auth=token` can stand alone without crowding `core`.

## Follow-up Build Inventory

Committed template files a build plan would touch:

- `cookiecutter.json`: add `api_auth` and prompt text.
- `hooks/post_gen_project.py`: define `API_AUTH`; remove token-only files when
  not applicable.
- `{{cookiecutter.project_slug}}/src/apps/api/auth.py`: new bearer auth helper
  for token mode.
- `{{cookiecutter.project_slug}}/src/apps/notes/routes.py`: conditional import
  and `Router(auth=...)` selection.
- `{{cookiecutter.project_slug}}/src/apps/core/models.py`: conditional token
  model if the model stays in `core`.
- `{{cookiecutter.project_slug}}/src/apps/core/admin.py`: conditional token
  admin registration if the model stays in `core`.
- `{{cookiecutter.project_slug}}/src/apps/core/migrations/0002_token.py`: token
  migration, removed when not in token mode.
- `{{cookiecutter.project_slug}}/tests/utils.py`: conditional session vs bearer
  authenticated client helper.
- `{{cookiecutter.project_slug}}/tests/core/unit/models_test.py`: token model
  tests in token mode.
- `{{cookiecutter.project_slug}}/tests/notes/integration/notes_test.py`: unknown
  bearer-token failure test in token mode.
- `{{cookiecutter.project_slug}}/README.md`: document the knob and token issue
  flow.
- `{{cookiecutter.project_slug}}/AGENTS.md`: clarify that token mode is an
  example and future mutating endpoints still need explicit auth.
- `.github/workflows/ci.yaml`: add a token-auth bake case.
- Root `README.md`: update feature/knob inventory if it lists choices.
- `plans/README.md`: add the follow-up build plan after maintainer decision.

Hook deletions for the `core`-model implementation:

```python
API_AUTH = {{ cookiecutter.api_auth | tojson }}

REMOVED_PATHS = [
    *(
        [
            "src/apps/api/auth.py",
            "src/apps/core/migrations/0002_token.py",
            "tests/api/unit/auth_test.py",
        ]
        if not (USE_EXAMPLE_API == "yes" and API_AUTH == "token")
        else []
    ),
]
```

The exact list depends on whether token tests live under `tests/api/unit/` or
existing model/notes tests use Jinja conditionals. If a dedicated app is chosen,
prefer `REMOVED_DIRS = ["src/apps/tokens", "tests/tokens"]` for non-token bakes.

## CI Matrix

Add one required root CI bake case:

```yaml
- case: example-token-auth
  args: >-
    use_example_api=yes
    api_auth=token
```

Keep cases sorted by `case:` with the existing matrix. The generated-project
checks for that bake should include:

```bash
docker compose -f .docker/compose/dev.yaml up -d --wait postgres
uv run pytest
uv run pre-commit run --all-files
docker compose -f .docker/compose/dev.yaml down -v
```

If `api_auth=token` is allowed with `use_example_api=no`, add a small negative
bake that asserts token-only files are absent or that the empty API still passes
pre-commit and tests.

## Proof Of Concept

Scratch paths:

- Baseline bake: `/tmp/bake-baseline/my-project`
- PoC bake: `/tmp/bake-poc/my-project`

Commands run:

```bash
uvx cookiecutter . --no-input -o /tmp/bake-poc use_example_api=yes
```

```bash
git add -A && ALLOWED_HOSTS=localhost,testserver CACHE_URL=locmemcache:// DATABASE_URL=postgres://postgres:postgres@localhost:5432/postgres DEFAULT_FROM_EMAIL=noreply@example.com DJANGO_ENV=ci SECRET_KEY=ci-secret-for-tests-0123456789-abcdefghijklmnopqrstuvwxyz uv run pre-commit run --all-files
```

Final pre-commit result: all hooks passed, including `ruff check`,
`ruff format`, `ty`, `uv-audit`, `uv-lock`, and pre-commit hook sync.

Required pytest command and output:

```bash
DATABASE_URL=postgres://postgres:postgres@localhost:5432/postgres uv run pytest
```

```text
============================= test session starts ==============================
platform linux -- Python 3.14.3, pytest-9.0.3, pluggy-1.6.0
django: version: 6.0.6, settings: config.settings (from ini)
testpaths: tests
24 workers [43 items]

...........................................                              [100%]
================================ tests coverage ================================
Name    Stmts   Miss Branch BrPart  Cover   Missing
---------------------------------------------------
TOTAL     373      0     12      0   100%

52 files skipped due to complete coverage.
Required test coverage of 100% reached. Total coverage: 100.00%
============================= 43 passed in 16.54s ==============================
```

Environment note: an existing `postgres:18.4` container was already bound to
`127.0.0.1:5432` with `my_project:my_project` credentials. To run the spike's
exact pytest DSN, I added/updated a `postgres` superuser role with password
`postgres` and ensured a `postgres` database exists inside that local dev
container.

## PoC File Diffs

The PoC changed these files relative to a fresh `use_example_api=yes` bake:

- `src/apps/api/auth.py` (new)
- `src/apps/core/admin.py`
- `src/apps/core/models.py`
- `src/apps/core/migrations/0002_token.py` (new)
- `src/apps/notes/routes.py`
- `tests/core/unit/models_test.py`
- `tests/notes/integration/notes_test.py`
- `tests/utils.py`

Important diff hunks:

```diff
diff --git a/src/apps/api/auth.py b/src/apps/api/auth.py
new file mode 100644
+from typing import TYPE_CHECKING
+
+from ninja.security import HttpBearer
+
+from apps.core.models import Token
+
+if TYPE_CHECKING:
+    from django.http import HttpRequest
+    from apps.core.models import User
+
+
+class TokenAuth(HttpBearer):
+    def authenticate(self, request: HttpRequest, token: str) -> User | None:
+        try:
+            api_token = Token.objects.select_related("user").get(
+                digest=Token.hash(token)
+            )
+        except Token.DoesNotExist:
+            return None
+
+        request.user = api_token.user
+        return api_token.user
+
+
+token_auth = TokenAuth()
```

```diff
diff --git a/src/apps/core/models.py b/src/apps/core/models.py
+import hashlib
+import secrets
 import uuid
 
+from django.conf import settings
 from django.contrib.auth.models import AbstractUser
 from django.db import models
 from django.utils.translation import gettext_lazy as _
@@
 class UUIDModel(models.Model):
@@
     class Meta:
         abstract = True
+
+
+class Token(UUIDModel, CreatedAtModel):
+    digest = models.CharField(_("digest"), max_length=64, unique=True)
+    name = models.CharField(_("name"), max_length=100)
+    user = models.ForeignKey(
+        settings.AUTH_USER_MODEL,
+        db_index=True,
+        on_delete=models.CASCADE,
+        related_name="api_tokens",
+        verbose_name=_("user"),
+    )
+
+    class Meta:
+        ordering = ("name",)
+        verbose_name = _("API token")
+        verbose_name_plural = _("API tokens")
+
+    def __str__(self) -> str:
+        return self.name
+
+    @classmethod
+    def issue(cls, *, name: str, user: User) -> tuple[str, Token]:
+        raw_token = secrets.token_urlsafe(32)
+        token = cls.objects.create(
+            digest=cls.hash(raw_token),
+            name=name,
+            user=user,
+        )
+        return raw_token, token
+
+    @staticmethod
+    def hash(raw_token: str) -> str:
+        return hashlib.sha256(raw_token.encode()).hexdigest()
```

```diff
diff --git a/src/apps/notes/routes.py b/src/apps/notes/routes.py
-from ninja.security import django_auth
-
+from apps.api.auth import token_auth
 from apps.api.pagination import BoundedLimitOffsetPagination
@@
-router = Router(auth=django_auth, tags=["notes"])
+router = Router(auth=token_auth, tags=["notes"])
```

```diff
diff --git a/tests/utils.py b/tests/utils.py
 from typing import TYPE_CHECKING
 
+from apps.core.models import Token
+
@@
 class AuthenticatedTestClient:
     def __init__(self, client: TestClient, user: User) -> None:
         self._client = client
+        self.raw_token, self.token = Token.issue(name="test token", user=user)
         self.user = user
 
     def delete(self, path: str) -> NinjaResponse:
-        return self._client.delete(path, user=self.user)
+        return self._client.delete(path, headers=self._headers())
@@
-        return self._client.get(path, query_params=query_params, user=self.user)
+        return self._client.get(
+            path, headers=self._headers(), query_params=query_params
+        )
@@
-        return self._client.post(path, json=json, user=self.user)
+        return self._client.post(path, headers=self._headers(), json=json)
@@
-        return self._client.put(path, json=json, user=self.user)
+        return self._client.put(path, headers=self._headers(), json=json)
+
+    def _headers(self) -> dict[str, str]:
+        return {"Authorization": f"Bearer {self.raw_token}"}
```

```diff
diff --git a/tests/notes/integration/notes_test.py b/tests/notes/integration/notes_test.py
@@
 def test_list_notes_returns_401_when_anonymous(v1_api_client: TestClient) -> None:
     response = v1_api_client.get("/notes")
 
     assert response.status_code == HTTPStatus.UNAUTHORIZED
 
 
+def test_list_notes_returns_401_when_token_is_unknown(
+    v1_api_client: TestClient,
+) -> None:
+    response = v1_api_client.get(
+        "/notes", headers={"Authorization": "Bearer unknown-token"}
+    )
+
+    assert response.status_code == HTTPStatus.UNAUTHORIZED
```

## Open Questions For The Maintainer

1. Should the template ship this as an opt-in worked example, or remain
   auth-agnostic and only document patterns?
2. Should the knob be named `api_auth` or the more precise
   `example_api_auth`?
3. If `api_auth=token` and `use_example_api=no`, should token scaffolding still
   render, or should the choice be ignored/rejected?
4. Should token provisioning be management-command only for the first build, or
   should a password-based token-issue endpoint be included?
5. Should the token model live in `apps.core` beside `User`, or in a dedicated
   app that can be cleanly removed for non-token bakes?
6. Should API-key service credentials be a later separate knob, or explicitly
   out of scope?

## STOP Point

This spike should stop here. The next step is a maintainer decision on the open
questions above, followed by a separate build plan. No committed template source
under `{{cookiecutter.project_slug}}/` should be changed by this spike.
