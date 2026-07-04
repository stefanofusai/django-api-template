# Plan 003: Ship a custom user model (apps.users) and seed tests/factories.py

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving to the
> next step. If anything in the "STOP conditions" section occurs, stop and
> report — do not improvise. When done, update the status row for this plan
> in `plans/README.md` — unless a reviewer dispatched you and told you they
> maintain the index.
>
> **Drift check (run first)**: `git diff --stat 924bfba..HEAD -- '{{cookiecutter.project_slug}}/src/' '{{cookiecutter.project_slug}}/tests/' '{{cookiecutter.project_slug}}/AGENTS.md'`
> If any in-scope file changed since this plan was written, compare the
> "Current state" excerpts against the live code before proceeding; on a
> mismatch, treat it as a STOP condition.

## Status

- **Priority**: P1
- **Effort**: M
- **Risk**: LOW (the template has shipped no migrations yet, so this is the one moment swapping the user model is free)
- **Depends on**: 001 (recommended — honest coverage of the new app)
- **Category**: tech-debt / architecture
- **Planned at**: commit `924bfba`, 2026-07-04

## Why this matters

The template uses Django's default `auth.User`. Django's own documentation
says to set a custom user model **before the first migration** — swapping
later is one of the most painful migrations in Django. A template is exactly
the place to absorb this decision: every baked project inherits either the fix
or the trap. This plan adds `apps.users.User(AbstractUser)` (no extra fields —
the value is the swap point itself), registers it in the admin, and seeds
`tests/factories.py` with a `UserFactory`. That last part also repairs an
existing inconsistency: `AGENTS.md:69` instructs "Register factories in
`tests/factories.py`" and the pre-commit `name-tests-test` hook already
excludes that file, but it doesn't exist, and `factory-boy`/`pytest-factoryboy`
are installed yet unused.

## Important context: this is a cookiecutter template

- Project code lives under the literal directory
  `{{cookiecutter.project_slug}}/` — always quote it in shell commands.
- Files may contain Jinja placeholders (`{{ cookiecutter.* }}`) — preserve
  them verbatim. The new files in this plan need none.
- Verification happens by baking a project and running its suite.

## Current state

- No `users` app exists; `AUTH_USER_MODEL` is unset anywhere:
  `grep -rn "AUTH_USER_MODEL" '{{cookiecutter.project_slug}}/src'` → no matches.
- `{{cookiecutter.project_slug}}/src/config/settings/components/apps.py`:

  ```python
  INSTALLED_APPS = [
      # Admin theme must precede django.contrib.admin.
      "unfold",
      # Django
      "django.contrib.admin",
      ...
      # Project
      "apps.api",
      "apps.core",
  ]
  ```

- `{{cookiecutter.project_slug}}/src/config/settings/components/authentication.py`
  holds `AUTH_PASSWORD_VALIDATORS` and `PASSWORD_HASHERS` (Argon2 first).
- App configs follow this pattern (`src/apps/core/apps.py`):

  ```python
  from django.apps import AppConfig


  class CoreConfig(AppConfig):
      name = "apps.core"
  ```

  (`src/apps/api/apps.py` also sets `label = "api"`.)
- `django-extra-checks` is active (`components/checks.py`) and enforces per
  AGENTS.md: "models need `__str__`, `Meta.ordering`, admin registration,
  gettext verbose/help text, explicit FK `related_name` and `db_index`,
  choice constraints". `AbstractUser` provides `__str__` (returns username)
  and gettext-wrapped field metadata; you must supply `Meta.ordering` and
  admin registration.
- Admin theme is `django-unfold==0.96.0` (INSTALLED_APPS `"unfold"` before
  `django.contrib.admin`). Unfold styles third-party model admins properly
  only when they subclass `unfold.admin.ModelAdmin`; unfold also ships
  `unfold.forms` with `AdminPasswordChangeForm`, `UserChangeForm`,
  `UserCreationForm` for user admins (verify importability in Step 4).
- Tests: pytest-factoryboy is installed (`pyproject.toml` ci/dev groups);
  `tests/conftest.py` currently has no factory registrations. AGENTS.md
  testing rules: "Use pytest-factoryboy model fixtures directly", "Avoid
  direct `Model.objects.create(...)`", test names
  `test_<subject>_<expected_behavior>_when_<condition>`, tests alphabetized
  within files.
- Coverage gate (after Plan 001): `--cov=src`, 100% enforced — every line of
  the new app must be executed by tests (admin.py loads via Django's admin
  autodiscovery during any test that touches `config.urls`, e.g. the
  schemathesis test importing `config.wsgi`).

## Commands you will need

| Purpose | Command | Expected on success |
|---------|---------|---------------------|
| Bake | `uvx cookiecutter . --no-input -o $BAKE` | exit 0 |
| Tests | `cd $BAKE/my-project && uv run pytest` | all pass, 100% |
| Hooks | `cd $BAKE/my-project && git add -A && uv run pre-commit run --all-files` | all pass |
| Make migration (inside bake) | `uv run python manage.py makemigrations users` | writes `src/apps/users/migrations/0001_initial.py` |
| System checks (inside bake) | `uv run python manage.py check` | `System check identified no issues` |

## Scope

**In scope** (template files; create unless noted):
- `{{cookiecutter.project_slug}}/src/apps/users/__init__.py`
- `{{cookiecutter.project_slug}}/src/apps/users/admin.py`
- `{{cookiecutter.project_slug}}/src/apps/users/apps.py`
- `{{cookiecutter.project_slug}}/src/apps/users/migrations/__init__.py`
- `{{cookiecutter.project_slug}}/src/apps/users/migrations/0001_initial.py`
- `{{cookiecutter.project_slug}}/src/apps/users/models.py`
- `{{cookiecutter.project_slug}}/src/config/settings/components/apps.py` (edit)
- `{{cookiecutter.project_slug}}/src/config/settings/components/authentication.py` (edit)
- `{{cookiecutter.project_slug}}/tests/factories.py`
- `{{cookiecutter.project_slug}}/tests/conftest.py` (edit)
- `{{cookiecutter.project_slug}}/tests/unit/users/__init__.py`
- `{{cookiecutter.project_slug}}/tests/unit/users/models_test.py`
- `{{cookiecutter.project_slug}}/AGENTS.md` (one-line edit, Step 7)

**Out of scope**:
- Adding profile fields, email-as-username, or any auth endpoints — the swap
  point is the deliverable, not an auth feature.
- `apps.core` abstract models — do not make `User` inherit them (AbstractUser
  already has its own id semantics; mixing UUID pks into the auth model is a
  bigger decision the maintainer has not made).

## Git workflow

- Branch: `advisor/003-custom-user-model`
- Conventional commit, e.g. `feat: add custom user model and seed test factories`
- Do NOT push or open a PR unless the operator instructed it.

## Steps

### Step 1: Create the app skeleton

`src/apps/users/__init__.py` — empty.
`src/apps/users/apps.py`:

```python
from django.apps import AppConfig


class UsersConfig(AppConfig):
    label = "users"
    name = "apps.users"
```

`src/apps/users/migrations/__init__.py` — empty.

### Step 2: The model

`src/apps/users/models.py`:

```python
from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    class Meta:
        ordering = ["username"]
        verbose_name = AbstractUser.Meta.verbose_name
        verbose_name_plural = AbstractUser.Meta.verbose_name_plural
```

(`Meta.ordering` satisfies the `model-meta-attribute` extra-check; carrying
over the gettext verbose names keeps `AbstractUser.Meta` semantics. If
`extra_checks` still complains at Step 5, its message names the missing
attribute — add exactly that and re-run.)

### Step 3: Settings wiring

- `components/apps.py`: add `"apps.users"` to the Project section
  (alphabetical: `apps.api`, `apps.core`, `apps.users`).
- `components/authentication.py`: add at the top (module scope, before the
  existing constants — constants are otherwise alphabetical per AGENTS.md):

  ```python
  AUTH_USER_MODEL = "users.User"
  ```

### Step 4: Admin registration (unfold-aware)

`src/apps/users/admin.py` — try the unfold-native pattern first:

```python
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from unfold.admin import ModelAdmin
from unfold.forms import AdminPasswordChangeForm, UserChangeForm, UserCreationForm

from .models import User


@admin.register(User)
class UserAdmin(DjangoUserAdmin, ModelAdmin):
    add_form = UserCreationForm
    change_password_form = AdminPasswordChangeForm
    form = UserChangeForm
```

Check importability first inside a bake:
`uv run python -c "from unfold.forms import AdminPasswordChangeForm, UserChangeForm, UserCreationForm"`.
If that import fails on the pinned unfold version, fall back to plain
`@admin.register(User)` + `class UserAdmin(DjangoUserAdmin, ModelAdmin)`
without the form overrides; if `unfold.admin.ModelAdmin` itself conflicts with
`DjangoUserAdmin` (MRO/metaclass errors at Step 5's check), fall back to
registering with `DjangoUserAdmin` alone and note it in the PR description.

### Step 5: Generate the migration inside a bake, then copy it back

1. Bake: `uvx cookiecutter . --no-input -o $BAKE` (this bake will FAIL pytest
   right now — expected; you only need the environment).
2. In `$BAKE/my-project`: `uv run python manage.py makemigrations users` →
   creates `src/apps/users/migrations/0001_initial.py`.
3. `uv run python manage.py check` → no issues (this runs django-extra-checks;
   fix any reported model/admin attribute and regenerate if the model changed).
4. Copy the generated `0001_initial.py` verbatim into the template at
   `{{cookiecutter.project_slug}}/src/apps/users/migrations/0001_initial.py`.
   Inspect it first: it must contain no absolute paths and no project-name
   references (it won't — the users app is project-name-independent).

**Verify**: fresh bake → `uv run python manage.py makemigrations --check --dry-run`
→ "No changes detected" (the shipped migration is complete).

### Step 6: Factories and tests

`tests/factories.py`:

```python
import factory

from apps.users.models import User


class UserFactory(factory.django.DjangoModelFactory):
    email = factory.Faker("email")
    username = factory.Sequence(lambda n: f"user-{n}")

    class Meta:
        model = User
```

`tests/conftest.py` — register it (pytest-factoryboy) alongside the existing
content:

```python
from pytest_factoryboy import register

from tests.factories import UserFactory

register(UserFactory)
```

(Keep existing fixtures/hooks; imports at top, follow Ruff ordering.)

`tests/unit/users/__init__.py` — empty.
`tests/unit/users/models_test.py` — behavioral tests (not settings
assertions), using the pytest-factoryboy `user` fixture:

```python
import pytest
from django.contrib.auth import get_user_model

from apps.users.models import User

pytestmark = pytest.mark.django_db


def test_get_user_model_returns_custom_user_when_project_is_configured() -> None:
    assert get_user_model() is User


def test_user_str_returns_username_for_created_user(user: User) -> None:
    assert str(user) == user.username
```

**Verify**: fresh bake → `uv run pytest` → all pass, coverage 100% (if any
users-app line is uncovered, the term-missing report names it — cover it with
a behavioral test, not a config assertion).

### Step 7: Truthful AGENTS.md

In `{{cookiecutter.project_slug}}/AGENTS.md`, the line
"Register factories in `tests/factories.py` when adding concrete models."
now matches reality — append a pointer so agents find the exemplar:
"Register factories in `tests/factories.py` when adding concrete models
(see `UserFactory`)."

### Step 8: Full verification loop

**Verify**:
- Fresh bake → `uv run pytest` → all pass, 100%
- `uv run python manage.py makemigrations --check --dry-run` → no changes
- `git add -A && uv run pre-commit run --all-files` → all pass

## Test plan

- `tests/unit/users/models_test.py`: the two tests above (swap point active;
  factory-created user behaves). Pattern: `tests/unit/api/api_test.py` for
  layout, AGENTS.md naming rules.
- Factory registration itself is exercised by the `user` fixture use.
- Existing suite (schemathesis, ready, request-id) must stay green — none of
  them reference `auth.User` directly (verified: no `django.contrib.auth`
  imports in current tests).

## Done criteria

- [ ] `grep -rn "AUTH_USER_MODEL" '{{cookiecutter.project_slug}}/src'` → exactly one hit in `components/authentication.py`
- [ ] Baked project: `uv run pytest` → all pass, 100%
- [ ] Baked project: `makemigrations --check --dry-run` → no changes detected
- [ ] Baked project: `manage.py check` → no issues (extra-checks satisfied)
- [ ] `tests/factories.py` exists in the template with `UserFactory`
- [ ] `uv run pre-commit run --all-files` in bake → all pass
- [ ] No files outside the in-scope list modified (`git status`)
- [ ] `plans/README.md` status row updated

## STOP conditions

Stop and report back if:

- `django_celery_results` or any other installed app's migration references
  `auth.User` in a way that breaks `migrate` in the bake (it should reference
  `settings.AUTH_USER_MODEL` via swappable dependencies — if not, this needs a
  maintainer decision).
- The unfold admin registration fails in BOTH the primary and fallback forms.
- The generated migration contains anything project-specific (unexpected —
  report the content).
- Schemathesis (`schema_test.py`) starts failing for reasons unrelated to a
  trivially added schema.

## Maintenance notes

- Every future concrete model should follow this pattern: model +
  extra-checks-satisfying Meta + admin + factory in `tests/factories.py`.
- If the maintainer later wants email-login or UUID pks for users, that is a
  NEW migration on top of this swap point — the expensive part (the swap) is
  now done.
- Plan 013's smoke test runs `migrate` in containers, which now includes the
  users migration — no action needed, just awareness.
