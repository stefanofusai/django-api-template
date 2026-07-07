# Plan 001: Add `api_auth=token` for the example API

> **For agentic workers:** REQUIRED SUB-SKILL: Use
> superpowers:subagent-driven-development (recommended) or
> superpowers:executing-plans to implement this plan task-by-task. Steps use
> checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an opt-in opaque bearer-token auth mode for the generated example
notes API while preserving the current session-auth default.

**Architecture:** Add `api_auth = ["session", "token"]`. In token mode and only
when `use_example_api=yes`, render a small DB-backed `Token` model, a Ninja
`HttpBearer` auth helper, token-aware tests, docs, and a CI bake case. Empty API
projects stay clean and do not receive token models.

**Tech Stack:** Cookiecutter, Django 6, Django Ninja `HttpBearer`, Django ORM,
pytest, uv, pre-commit.

---

## Status

- **Priority**: P1
- **Effort**: L
- **Risk**: MED
- **Depends on**: none
- **Category**: direction
- **Planned at**: commit `9d129c1`, 2026-07-08

## Drift Check

Run first:

```shell
git diff --stat 9d129c1..HEAD -- cookiecutter.json hooks/post_gen_project.py "{{cookiecutter.project_slug}}/src/apps/notes/routes.py" "{{cookiecutter.project_slug}}/src/apps/core/models.py" "{{cookiecutter.project_slug}}/tests/utils.py" "{{cookiecutter.project_slug}}/pyproject.toml"
```

If any file changed, compare the current state below with the live code. Stop if
the plan no longer matches.

## Current State

- `cookiecutter.json` has no `api_auth` variable.
- `{{cookiecutter.project_slug}}/src/apps/notes/routes.py` uses
  `Router(auth=django_auth, tags=["notes"])`.
- `{{cookiecutter.project_slug}}/tests/utils.py` authenticates by passing
  `user=` to Ninja's `TestClient`.
- `{{cookiecutter.project_slug}}/src/apps/core/models.py` contains `User` and no
  token model.
- `hooks/post_gen_project.py` removes notes files when `USE_EXAMPLE_API == "no"`.

## Scope

**In scope**:
- `cookiecutter.json`
- `hooks/post_gen_project.py`
- `.github/workflows/ci.yaml`
- `README.md`
- `{{cookiecutter.project_slug}}/README.md`
- `{{cookiecutter.project_slug}}/AGENTS.md`
- `{{cookiecutter.project_slug}}/src/apps/api/auth.py` (create)
- `{{cookiecutter.project_slug}}/src/apps/core/admin.py`
- `{{cookiecutter.project_slug}}/src/apps/core/models.py`
- `{{cookiecutter.project_slug}}/src/apps/core/migrations/0002_token.py` (create)
- `{{cookiecutter.project_slug}}/src/apps/notes/routes.py`
- `{{cookiecutter.project_slug}}/tests/api/unit/auth_test.py` (create)
- `{{cookiecutter.project_slug}}/tests/core/unit/models_test.py`
- `{{cookiecutter.project_slug}}/tests/notes/integration/notes_test.py`
- `{{cookiecutter.project_slug}}/tests/utils.py`

**Out of scope**:
- JWT, refresh tokens, login, registration, password reset, API-key service
  identities, or token auth for empty `/api/v1/` projects.
- Auth changes for `internal_api`, `/api/health`, or `/api/ready`.

## Steps

### Task 1: Add the Cookiecutter knob

- [ ] Add `api_auth` to `cookiecutter.json` with default `session`:

```json
"api_auth": ["session", "token"]
```

- [ ] Add prompt text:

```json
"api_auth": {
    "__prompt__": "Authentication used by the example notes API",
    "session": "Django session auth with CSRF, matching today's behavior",
    "token": "Opaque bearer tokens for non-browser clients"
}
```

- [ ] Verify:

```shell
rtk uvx cookiecutter . -o /tmp/bake-auth-default --no-input
```

Expected: exit 0, generated project has no token files.

### Task 2: Render a token model only in example token mode

- [ ] In `src/apps/core/models.py`, add imports under the token gate:

```python
{%- if cookiecutter.use_example_api == "yes" and cookiecutter.api_auth == "token" %}
import hashlib
import secrets
{%- endif %}
```

- [ ] Add this model after `User` under the same gate:

```python
class Token(models.Model):
    digest = models.CharField(_("digest"), max_length=64, unique=True)
    name = models.CharField(_("name"), max_length=100)
    user = models.ForeignKey(
        User,
        db_index=True,
        on_delete=models.CASCADE,
        related_name="tokens",
        verbose_name=_("user"),
    )

    class Meta:
        ordering = ["name"]
        verbose_name = _("token")
        verbose_name_plural = _("tokens")

    def __str__(self) -> str:
        return self.name

    @classmethod
    def issue(cls, *, name: str, user: User) -> tuple[str, Token]:
        raw_token = secrets.token_urlsafe(32)
        token = cls.objects.create(
            digest=cls.hash(raw_token),
            name=name,
            user=user,
        )
        return raw_token, token

    @staticmethod
    def hash(raw_token: str) -> str:
        return hashlib.sha256(raw_token.encode()).hexdigest()
```

- [ ] Add matching admin registration in `src/apps/core/admin.py`.
- [ ] Create `src/apps/core/migrations/0002_token.py`.
- [ ] Add model tests proving `issue()` returns a raw token, stores only the
      digest, and `__str__` returns the token name.
- [ ] Verify inside a token bake:

```shell
rtk uv run pytest --no-cov tests/core/unit/models_test.py
rtk uv run python manage.py makemigrations --check --dry-run
```

Expected: tests pass and no migration changes are detected.

### Task 3: Add Ninja bearer auth

- [ ] Create `src/apps/api/auth.py` under the same token gate. Implement a
      `BearerTokenAuth(HttpBearer)` class that hashes the presented token,
      loads `Token.objects.select_related("user")`, assigns `request.user`, and
      returns the user.
- [ ] Unknown tokens must raise `ninja.errors.HttpError(401, "Invalid token")`.
- [ ] Add `tests/api/unit/auth_test.py` covering valid token and invalid token.
- [ ] Verify:

```shell
rtk uv run pytest --no-cov tests/api/unit/auth_test.py
```

Expected: token auth tests pass.

### Task 4: Switch notes auth by mode

- [ ] In `src/apps/notes/routes.py`, keep `django_auth` for session mode.
- [ ] In token mode, import the bearer auth instance and mount:

```python
router = Router(auth=bearer_token_auth, tags=["notes"])
```

- [ ] In session mode, keep:

```python
router = Router(auth=django_auth, tags=["notes"])
```

- [ ] Verify:

```shell
rtk uv run pytest --no-cov tests/notes/integration/notes_test.py
```

Expected: notes tests pass in session and token bakes.

### Task 5: Update authenticated test helpers

- [ ] In `tests/utils.py`, keep the current `AuthenticatedTestClient` for
      session mode.
- [ ] In token mode, create tokens via `Token.issue(name="test token", user=user)`
      and send `Authorization: Bearer <raw_token>` headers from every helper
      method.
- [ ] Keep fixture names unchanged in `tests/conftest.py`.
- [ ] Verify full generated tests in token mode:

```shell
rtk uv run pytest
```

Expected: exit 0 with 100% coverage.

### Task 6: Clean token-only files outside token mode

- [ ] In `hooks/post_gen_project.py`, add `API_AUTH`.
- [ ] Add token-only cleanup when not
      `USE_EXAMPLE_API == "yes" and API_AUTH == "token"`:

```python
[
    "src/apps/api/auth.py",
    "src/apps/core/migrations/0002_token.py",
    "tests/api/unit/auth_test.py",
]
```

- [ ] Verify default and session-example bakes have no token-only files.

### Task 7: Document and add CI coverage

- [ ] Update root and generated README variable tables.
- [ ] Update generated `AGENTS.md` to say token mode is an example auth mode and
      future mutating endpoints still need explicit auth.
- [ ] Add CI bake case, sorted by `case`:

```yaml
- case: example-token-auth
  project_name: My Project
  extra-args: use_example_api=yes api_auth=token
  slug: my-project
```

- [ ] Verify root checks:

```shell
rtk pre-commit run --all-files
```

Expected: exit 0.

## Test Plan

- Default bake: no token files, pre-commit passes, tests pass.
- `use_example_api=yes`: session auth behavior unchanged.
- `use_example_api=yes api_auth=token`: token model, auth helper, notes tests,
  pre-commit, migration check, and full tests pass.

## Done Criteria

- [ ] `api_auth` is documented and defaults to `session`.
- [ ] Token code renders only for `use_example_api=yes api_auth=token`.
- [ ] Raw tokens are never stored.
- [ ] Notes routes work in session and token modes.
- [ ] CI includes an `example-token-auth` bake.
- [ ] Root `rtk pre-commit run --all-files` passes.
- [ ] Generated pre-commit and full pytest pass for default, session-example,
      and token-example bakes.

## STOP Conditions

- Token auth requires adding a third-party dependency.
- Empty `/api/v1/` bakes need token files to pass checks.
- The implementation requires protecting internal probes.
- The model cannot satisfy `django-extra-checks` without broad exceptions.

## Maintenance Notes

Plan 003 relies on this auth mode for user/token throttle identity. Keep login
and credential provisioning endpoints out of this plan; a management command can
be a later small add-on if operators need it.
