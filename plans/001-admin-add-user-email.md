# Plan 001: Collect `email` on the admin add-user form so a second admin-created user no longer 500s

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving to the
> next step. If anything in the "STOP conditions" section occurs, stop and
> report — do not improvise. When done, update the status row for this plan
> in `plans/README.md` — unless a reviewer dispatched you and told you they
> maintain the index.
>
> **Drift check (run first)**:
> `git diff --stat e0ec725..HEAD -- '{{cookiecutter.project_slug}}/src/apps/core/admin.py' '{{cookiecutter.project_slug}}/src/apps/core/models.py' '{{cookiecutter.project_slug}}/tests/core/integration/admin_test.py'`
> If any in-scope file changed since this plan was written, compare the
> "Current state" excerpts against the live code before proceeding; on a
> mismatch, treat it as a STOP condition.

## Status

- **Priority**: P1
- **Effort**: S
- **Risk**: LOW
- **Depends on**: none
- **Category**: bug
- **Planned at**: commit `e0ec725`, 2026-07-09

## Why this matters

This repository is a cookiecutter template; files under
`{{cookiecutter.project_slug}}/` are Jinja-templated and become the generated
Django project. The generated `User` model declares `email` as `unique=True`
with no `blank=True`, so its empty value is `""`. The admin's add-user form
(Django's default `add_fieldsets`, which unfold's `UserCreationForm` does not
extend) collects only `username`, `usable_password`, `password1`, and
`password2` — never `email`. The first admin-created user therefore saves with
`email=""`; the second one violates the unique constraint and the add view
raises `IntegrityError` (HTTP 500). Admin user creation is effectively limited
to one account in every generated project. `createsuperuser` is unaffected
because `AbstractUser.REQUIRED_FIELDS = ["email"]` prompts on the CLI path.
No test exercises the admin add flow, so CI stays green.

## Current state

- `{{cookiecutter.project_slug}}/src/apps/core/admin.py` — the whole file (no
  Jinja in it):

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

  Note: no `add_fieldsets` override, so Django's default applies
  (`django/contrib/auth/admin.py`, class `UserAdmin`):

  ```python
  add_fieldsets = (
      (
          None,
          {
              "classes": ("wide",),
              "fields": ("username", "usable_password", "password1", "password2"),
          },
      ),
  )
  ```

- `{{cookiecutter.project_slug}}/src/apps/core/models.py:32` —
  `email = models.EmailField(_("email address"), unique=True)` on
  `class User(UUIDModel, AbstractUser)`.

- `{{cookiecutter.project_slug}}/tests/core/integration/admin_test.py` — the
  only admin test; it GETs the changelist. Full file:

  ```python
  from http import HTTPStatus
  from typing import TYPE_CHECKING

  import pytest
  from django.urls import reverse

  if TYPE_CHECKING:
      from django.test import Client

      from apps.core.models import User

  pytestmark = pytest.mark.django_db


  @pytest.mark.parametrize("user__is_staff", [True])
  @pytest.mark.parametrize("user__is_superuser", [True])
  def test_user_changelist_returns_200_when_staff(
      client: Client,
      user: User,
  ) -> None:
      client.force_login(user)

      response = client.get(reverse("admin:core_user_changelist"))

      assert response.status_code == HTTPStatus.OK
  ```

- Mechanism to rely on: Django's `UserAdmin.get_fieldsets` returns
  `add_fieldsets` when `obj is None`, and `get_form` builds the add form with
  exactly those fields via `modelform_factory` — so adding `"email"` to
  `add_fieldsets` is sufficient to collect it; no custom form class is needed.
  The model field is `blank=False`, so the generated form field is required.

- Repo conventions that apply (from the repo root `AGENTS.md`): never add
  `from __future__ import annotations`; test names follow
  `test_<subject>_<expected_behavior>_when_<condition>`; keep test functions
  alphabetized within each file; use Faker/factory values for incidental data;
  blank lines around control-flow blocks.

## Commands you will need

| Purpose | Command | Expected on success |
|---------|---------|---------------------|
| Bake a project | `uvx cookiecutter . -o /tmp/verify-001 --no-input` | exit 0; project at `/tmp/verify-001/my-project` |
| Prepare baked env | `cd /tmp/verify-001/my-project && cp .env.example .env && uv sync --locked` | exit 0 |
| Start test Postgres | `docker compose -f .docker/compose/dev.yaml --env-file=.env up -d --wait postgres` (in baked project) | exit 0, postgres healthy |
| Baked tests | `uv run pytest` (in baked project) | all pass, 100% branch coverage |
| Baked lint/format | `uv run pre-commit run --all-files` (in baked project) | exit 0 |
| Teardown | `docker compose -f .docker/compose/dev.yaml --env-file=.env down -v` (in baked project) | exit 0 |
| Root template checks | `uvx pre-commit run --all-files` (at repo root) | exit 0 |

Run all baked-project commands inside the baked output, not the template.
Always quote paths containing `{{cookiecutter.project_slug}}` in shell
commands — the braces are literal directory characters.

## Scope

**In scope** (the only files you should modify):

- `{{cookiecutter.project_slug}}/src/apps/core/admin.py`
- `{{cookiecutter.project_slug}}/tests/core/integration/admin_test.py`

**Out of scope** (do NOT touch, even though they look related):

- `{{cookiecutter.project_slug}}/src/apps/core/models.py` — do not add
  `blank=True`/`null=True` to `email`; uniqueness-with-required is the
  intended contract.
- `{{cookiecutter.project_slug}}/src/apps/core/migrations/` — no schema
  change is involved.
- `{{cookiecutter.project_slug}}/tests/factories.py` — the existing `user`
  fixture/factory already provides emails.

## Git workflow

- Branch: `advisor/001-admin-add-user-email`
- Commit style: conventional commits, matching `git log` (e.g.
  `fix: collect email on the admin add-user form`).
- Do NOT push or open a PR unless the operator instructed it.

## Steps

### Step 1: Override `add_fieldsets` in `UserAdmin`

In `{{cookiecutter.project_slug}}/src/apps/core/admin.py`, add an
`add_fieldsets` attribute to `UserAdmin` that reproduces Django's default with
`"email"` inserted after `"username"`. Keep the existing three form
attributes; place `add_fieldsets` before `add_form` (alphabetical attribute
order, matching the repo's alphabetize-when-order-doesn't-matter convention):

```python
@admin.register(User)
class UserAdmin(DjangoUserAdmin, ModelAdmin):
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "username",
                    "email",
                    "usable_password",
                    "password1",
                    "password2",
                ),
            },
        ),
    )
    add_form = UserCreationForm
    change_password_form = AdminPasswordChangeForm
    form = UserChangeForm
```

(Do not alphabetize the `fields` tuple — field order here is display order
and mirrors Django's default with email slotted in.)

**Verify**: from the repo root,
`python -c "print(open('{{cookiecutter.project_slug}}/src/apps/core/admin.py').read())"`
shows the new attribute → then run `uvx pre-commit run --all-files` → exit 0
(the `generated-format` hook re-bakes and ruff-checks generated projects).

### Step 2: Add admin add-flow regression tests

In `{{cookiecutter.project_slug}}/tests/core/integration/admin_test.py`, add
two tests (keep all test functions alphabetized; the two new names below sort
before the existing `test_user_changelist_returns_200_when_staff`):

1. `test_user_add_form_creates_second_user_when_emails_differ` — the
   regression test for this bug. Log in a staff+superuser (reuse the existing
   `@pytest.mark.parametrize("user__is_staff", [True])` /
   `("user__is_superuser", [True])` pattern), then POST
   `reverse("admin:core_user_add")` twice with two distinct usernames, two
   distinct Faker emails, and a valid identical password pair, and assert both
   POSTs redirect (`HTTPStatus.FOUND`) and both users exist. Use
   `faker.password(length=16, special_chars=False)` for the password and
   include `"usable_password": "true"` in the POST data (Django's add form
   includes that toggle field). Suggested shape:

   ```python
   @pytest.mark.parametrize("user__is_staff", [True])
   @pytest.mark.parametrize("user__is_superuser", [True])
   def test_user_add_form_creates_second_user_when_emails_differ(
       client: Client,
       faker: Faker,
       user: User,
   ) -> None:
       client.force_login(user)
       password = faker.password(length=16, special_chars=False)

       for username, email in (
           (faker.user_name(), faker.email()),
           (faker.user_name(), faker.email()),
       ):
           response = client.post(
               reverse("admin:core_user_add"),
               {
                   "email": email,
                   "password1": password,
                   "password2": password,
                   "usable_password": "true",
                   "username": username,
               },
           )

           assert response.status_code == HTTPStatus.FOUND
           assert User.objects.filter(email=email, username=username).exists()
   ```

   (Import `Faker` under `TYPE_CHECKING` alongside the existing imports;
   `faker` is a session fixture provided by pytest plugins already in use —
   see `{{cookiecutter.project_slug}}/tests/api/integration/jwt_test.py` for
   an existing `faker: Faker` usage pattern. If Faker ever yields a duplicate
   username/email pair, regenerate — but `faker.user_name()`/`faker.email()`
   collisions within one test are effectively impossible.)

2. `test_user_add_form_requires_email_when_omitted` — POST the same data
   without the `email` key; assert the response is `HTTPStatus.OK` (form
   redisplay, not a redirect) and no user with that username was created.

**Verify**: bake and run the suite —
`uvx cookiecutter . -o /tmp/verify-001 --no-input` then, inside
`/tmp/verify-001/my-project`: `cp .env.example .env && uv sync --locked`,
start Postgres, `uv run pytest` → all tests pass including the two new ones
(`-k user_add_form` should select exactly 2 tests).

### Step 3: Full verification sweep

Run the baked project's `uv run pre-commit run --all-files` and the repo
root's `uvx pre-commit run --all-files`.

**Verify**: both exit 0. Tear down the compose Postgres afterwards.

## Test plan

- New tests (step 2), in
  `{{cookiecutter.project_slug}}/tests/core/integration/admin_test.py`:
  second-user creation succeeds (regression), and email is required on the
  add form. Model them structurally on the existing changelist test in the
  same file.
- Verification: `uv run pytest` in a default bake → all pass; coverage stays
  at the enforced 100% branch threshold (admin config is declarative, so no
  new uncovered branches).

## Done criteria

Machine-checkable. ALL must hold:

- [ ] `grep -n "add_fieldsets" '{{cookiecutter.project_slug}}/src/apps/core/admin.py'` → one match
- [ ] In a fresh default bake: `uv run pytest -k user_add_form` → 2 passed
- [ ] In a fresh default bake: `uv run pytest` → all pass (coverage gate holds)
- [ ] In the baked project: `uv run pre-commit run --all-files` → exit 0
- [ ] At repo root: `uvx pre-commit run --all-files` → exit 0
- [ ] `git status` shows no modified files outside the in-scope list
- [ ] `plans/README.md` status row updated

## STOP conditions

Stop and report back (do not improvise) if:

- `admin.py` no longer matches the excerpt in "Current state" (someone else
  fixed or changed the admin since `e0ec725`).
- The second POST in the regression test still returns 200 with a form error
  or 500 after step 1 — that means the installed Django/unfold versions build
  the add form differently than this plan assumes (e.g. `usable_password`
  renamed); report the actual form fields you observe
  (`response.context["adminform"].form.fields.keys()`).
- The fix appears to require editing `unfold`'s form classes or the `User`
  model.

## Maintenance notes

- If the `User` model ever gains more required fields, they must be added to
  this `add_fieldsets` too — the regression test will catch the 500 but not a
  silently-empty new field.
- Reviewer should scrutinize: the `usable_password` form-field name (Django
  version dependent) and that the test POSTs match the real form contract.
- Deferred: surfacing `email` on the admin *change* list/filters — cosmetic,
  not part of this bug.
