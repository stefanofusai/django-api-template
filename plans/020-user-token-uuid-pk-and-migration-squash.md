# Plan 020: Convert User/Token to UUID primary keys and squash core/notes migrations to fresh initials

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving to the
> next step. If anything in the "STOP conditions" section occurs, stop and
> report — do not improvise. When done, update the status row for this plan
> in `plans/README.md` — unless a reviewer dispatched you and told you they
> maintain the index.
>
> **Drift check (run first)**:
> `git diff --stat 727b7bc..HEAD -- '{{cookiecutter.project_slug}}/src/apps/core/models.py' '{{cookiecutter.project_slug}}/src/apps/core/migrations' '{{cookiecutter.project_slug}}/src/apps/notes/migrations' hooks/post_gen_project.py`
> If any in-scope file changed since this plan was written, compare the
> "Current state" excerpts against the live code before proceeding; on a
> mismatch, treat it as a STOP condition.

## Status

- **Priority**: P2
- **Effort**: M
- **Risk**: MED
- **Depends on**: none
- **Category**: tech-debt / migration
- **Planned at**: commit `727b7bc`, 2026-07-09

## Why this matters

Every model in this template inherits `UUIDModel` for its primary key — every
model, that is, except `User` and `Token`, which still get Django's default
`BigAutoField`. `Note` already documents the rationale in `core/models.py`
(uuid7 keeps b-tree PK indexes append-mostly instead of randomly fragmented,
and avoids leaking a sequential row count through the API/admin). `User` and
`Token` are the odd ones out for no principled reason — just historical
accident of `AbstractUser` providing its own default pk.

**These two operator-requested improvements turn out to be mechanically
coupled, not just "nice to pair together."** Postgres has no cast from
`bigint` to `uuid` (not even via an explicit `USING col::uuid`), so changing
`User.id`'s type is not expressible as a normal incremental `AlterField`
migration — Django would emit one, and it would fail at `migrate` time with
`cannot cast type bigint to uuid`. The only clean path is for the UUID column
to be part of a **fresh** `CreateModel`, which means the migration-history
squash isn't a separate nice-to-have — it is the *only* way to land the PK
change at all, for both `core` (`User`, `Token`) and `notes` (`Note.owner` FK
also flips from `bigint` to `uuid`). Since nothing has ever been deployed
from this template (it is pre-generation source with zero live data
anywhere), squashing migration history costs nothing — there is no
production database whose history this would break.

As a **second-order benefit**, regenerating from scratch also fixes an
existing field-order drift: `notes/migrations/0001_initial.py`'s `CreateModel`
lists fields as `created_at, updated_at, id, title, body, owner`, but the
current `Note` model (`notes/models.py:8-17`) declares `owner` *first*,
before `title`/`body`. The migration's field order reflects however the model
looked the day `0001_initial.py` was generated; later edits to the model's
field order are not retroactively reflected in existing migration
operations (Django has no reason to touch them — reordering fields is a
no-op for the database). Deleting and regenerating fixes this for free,
because a fresh `CreateModel` always reflects the model's *current*
`_meta.fields` order.

## Current state

This repo is a **cookiecutter template**: everything under
`{{cookiecutter.project_slug}}/` is rendered as a Jinja template (except
`.github/workflows/*` and `.agents/*`, which are `_copy_without_render`).
Verification means baking a project
(`uvx cookiecutter . -o /tmp/verify --no-input <knobs>`) and running its
suite there. Always single-quote paths containing
`{{cookiecutter.project_slug}}` in shell commands.

### The models today

`{{cookiecutter.project_slug}}/src/apps/core/models.py` (relevant excerpt,
Jinja stripped for readability — the real file wraps the `Token` class and
several imports in
`{%- if cookiecutter.use_example_api == "yes" and cookiecutter.api_auth == "token" %}`):

```python
class UUIDModel(models.Model):
    # uuid7 (stdlib since 3.14) over uuid4: time-ordered values keep b-tree
    # primary-key indexes append-mostly instead of randomly fragmented.
    id = models.UUIDField(primary_key=True, default=uuid.uuid7, editable=False)

    class Meta:
        abstract = True


class User(AbstractUser):
    email = models.EmailField(_("email address"), unique=True)

    class Meta:
        ordering = ("username",)
        verbose_name = AbstractUser.Meta.verbose_name
        verbose_name_plural = AbstractUser.Meta.verbose_name_plural


class Token(CreatedAtModel):
    expires_at = models.DateTimeField(_("expires at"), blank=True, null=True)
    last_used_at = models.DateTimeField(_("last used at"), blank=True, null=True)
    user = models.ForeignKey(
        User,
        db_index=True,
        on_delete=models.CASCADE,
        related_name="tokens",
        verbose_name=_("user"),
    )
    digest = models.CharField(_("digest"), max_length=64, unique=True)
    name = models.CharField(_("name"), max_length=100)
    prefix = models.CharField(_("prefix"), db_index=True, max_length=12)
    # ... __str__, hash, issue, is_expired, mark_used, prefix_from unchanged ...
```

`{{cookiecutter.project_slug}}/src/apps/notes/models.py` (entire file, the
precedent to match):

```python
from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.models import CreatedAtUpdatedAtModel, UUIDModel


class Note(UUIDModel, CreatedAtUpdatedAtModel):
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        db_index=True,
        on_delete=models.CASCADE,
        related_name="notes",
        verbose_name=_("owner"),
    )
    title = models.CharField(_("title"), max_length=255)
    body = models.TextField(_("body"), blank=True)

    class Meta:
        indexes = (models.Index(fields=["owner", "-created_at"]),)
        ordering = ("-created_at",)
        verbose_name = _("note")
        verbose_name_plural = _("notes")

    def __str__(self) -> str:
        return self.title
```

Note that `Note(UUIDModel, CreatedAtUpdatedAtModel)` already puts `UUIDModel`
first in the base list, and Django accepts this today (the abstract
`UUIDModel.id` field satisfies the "every concrete model needs a pk" check
during class creation, so Django never auto-adds a `BigAutoField`). `User`
and `Token` should follow the identical pattern: `class User(UUIDModel,
AbstractUser):` and `class Token(UUIDModel, CreatedAtModel):`. There is no
diamond-inheritance conflict — `UUIDModel` and `AbstractUser`/`CreatedAtModel`
share no field names, and both trace back to `models.Model` as their only
common ancestor, so C3 linearization resolves cleanly (verify empirically in
Step 2 with `manage.py check`, don't just trust this description).

### The migrations today

`{{cookiecutter.project_slug}}/src/apps/core/migrations/0001_initial.py`
creates `User` with a `BigAutoField` id (unconditional — always present,
regardless of knobs).

`{{cookiecutter.project_slug}}/src/apps/core/migrations/0002_token.py`
creates `Token` with a `BigAutoField` id, depending on `("core",
"0001_initial")`. This file is deleted post-generation by
`hooks/post_gen_project.py` whenever the combo is **not**
`use_example_api=yes AND api_auth=token` — see `REMOVED_PATHS` there:

```python
    *(
        [
            "src/apps/api/auth.py",
            "src/apps/api/exceptions.py",
            "src/apps/core/migrations/0002_token.py",
            "tests/api/unit/auth_test.py",
        ]
        if not (USE_EXAMPLE_API == "yes" and API_AUTH == "token")
        else []
    ),
```

`{{cookiecutter.project_slug}}/src/apps/notes/migrations/0001_initial.py`
creates `Note` (fields as they existed when this migration was generated:
`created_at, updated_at, id, title, body, owner` — note `owner` is last here,
unlike the current model source above where it's declared first).
`{{cookiecutter.project_slug}}/src/apps/notes/migrations/0002_note_notes_note_owner_i_b6b830_idx.py`
adds the `["owner", "-created_at"]` index as a separate `AddIndex` operation,
generated the same day as `0001_initial.py` but after it (the index was added
to `Meta.indexes` in a later edit than the initial model). The whole `notes`
app (models, migrations, tests) is deleted post-generation whenever
`use_example_api == "no"` — see `REMOVED_DIRS` in
`hooks/post_gen_project.py`; nothing else in this plan needs to touch that.

### Why the `core` migration needs a Jinja conditional and `notes`' doesn't

`Token` only exists in `models.py` when `use_example_api=yes AND
api_auth=token` (the `{%- if %}` block noted above). `Note` has no such
per-knob variance — it exists whenever the whole `notes` app exists, in both
`api_auth` values identically. So:

- `notes/migrations/0001_initial.py` after regeneration: **no Jinja needed
  inside the file** — it's the same for every combo where `notes` exists at
  all (handled by the directory-level removal, not file content).
- `core/migrations/0001_initial.py` after regeneration: **must stay
  Jinja-conditional** for the `Token` `CreateModel` and its supporting
  imports, exactly mirroring the pattern already used in `core/models.py`
  (Token class + `hashlib`/`secrets`/`datetime`/`timezone` imports) and in
  `src/config/settings/components/apps.py` (mid-list conditional entries with
  trailing commas):

```python
INSTALLED_APPS = [
    ...
    "axes",
{%- if cookiecutter.use_cors == "yes" %}
    "corsheaders",
{%- endif %}
    ...
]
```

That `apps.py` snippet is your reference for exactly how a conditional
element inside a Python list literal renders correctly in this codebase —
match this shape for `core`'s `operations` list, not a novel construction.

### Repo conventions that apply

From `AGENTS.md`: "Order model fields logically, not alphabetically...
Order unordered list items alphabetically when dependency order does not
matter" (does not apply to migration field lists — those follow
Django's own generated order, never hand-reordered). Conventional commits.
Alphabetize within groups where order doesn't matter.

`{{cookiecutter.project_slug}}/pyproject.toml:140-141` already Jinja-gates
the migration linter's app list the same way:

```python
[tool.django_migration_linter]
include_apps = ["core"{% if cookiecutter.use_example_api == "yes" %}, "notes"{% endif %}]
```

## Commands you will need

| Purpose | Command | Expected on success |
|---------|---------|---------------------|
| Bake (token combo) | `uvx cookiecutter . -o /tmp/verify-020-token --no-input use_example_api=yes api_auth=token` | project at `/tmp/verify-020-token/my-project` |
| Bake (session combo) | `uvx cookiecutter . -o /tmp/verify-020-session --no-input use_example_api=yes` | project at `/tmp/verify-020-session/my-project` |
| Bake (no example api) | `uvx cookiecutter . -o /tmp/verify-020-default --no-input` | project at `/tmp/verify-020-default/my-project` |
| Bake (throttling combo) | `uvx cookiecutter . -o /tmp/verify-020-throttle --no-input use_example_api=yes api_auth=token api_throttling=basic` | project at `/tmp/verify-020-throttle/my-project` |
| Install deps (in each bake) | `uv sync --locked` | exit 0 |
| Start Postgres (in each bake) | `cp .env.example .env && docker compose -f .docker/compose/dev.yaml --env-file=.env up -d --wait postgres` | postgres healthy |
| Generate migrations (in each bake) | `uv run manage.py makemigrations core notes` | reports new migrations created |
| Migrations-check gate (in each bake) | `uv run manage.py makemigrations --check --dry-run` | exit 0, "No changes detected" |
| Migration linter (in each bake) | `uv run manage.py lintmigrations` | exit 0 |
| Full suite (in each bake) | `uv run pytest` | all pass, 100% coverage |
| Lint/format (in each bake) | `uvx ruff@0.15.16 format --check . && uvx ruff@0.15.16 check .` | exit 0 |
| Type check (in each bake) | `uv run pre-commit run ty --all-files` | exit 0 |
| Teardown (in each bake) | `docker compose -f .docker/compose/dev.yaml --env-file=.env down -v` | exit 0 |

## Scope

**In scope** (the only files you should modify):
- `{{cookiecutter.project_slug}}/src/apps/core/models.py` — `User`, `Token`
  base classes.
- `{{cookiecutter.project_slug}}/src/apps/core/migrations/0001_initial.py` —
  rewritten, merged, Jinja-conditional.
- `{{cookiecutter.project_slug}}/src/apps/core/migrations/0002_token.py` —
  deleted.
- `{{cookiecutter.project_slug}}/src/apps/notes/migrations/0001_initial.py` —
  rewritten, merged (no Jinja needed).
- `{{cookiecutter.project_slug}}/src/apps/notes/migrations/0002_note_notes_note_owner_i_b6b830_idx.py`
  — deleted.
- `hooks/post_gen_project.py` — remove the now-nonexistent
  `"src/apps/core/migrations/0002_token.py"` entry from `REMOVED_PATHS`
  (leaving it would raise `FileNotFoundError` on every non-token-auth bake,
  since `Path(removed_path).unlink()` has no `missing_ok=True`).

**Out of scope** (do NOT touch, even though they look related):
- `{{cookiecutter.project_slug}}/src/apps/notes/models.py` — `Note` already
  inherits `UUIDModel` correctly; nothing to change there.
- `{{cookiecutter.project_slug}}/src/apps/api/auth.py`,
  `{{cookiecutter.project_slug}}/src/apps/notes/controllers.py` — already
  pk-type-agnostic (confirmed during planning: no `int`-typed schema fields,
  no `<int:pk>` URL converters, no hardcoded pk-type assumptions anywhere in
  the API/auth/admin/throttling/factories layers).
- `{{cookiecutter.project_slug}}/tests/factories.py` — `UserFactory` and
  `TokenFactory` don't set `id` explicitly; no change needed.
- Any other app's migrations (`auth`, `admin`, `sessions`, etc.) — untouched,
  Django's own swappable-FK machinery adapts automatically.
- `[tool.django_migration_linter] include_apps` in `pyproject.toml` — already
  correctly Jinja-gated; no change needed there.

## Git workflow

- Branch: `advisor/020-user-token-uuid-pk-and-migration-squash`
- Commit per logical step is fine, but squash to one commit before finishing
  if the intermediate commits would leave the tree in a broken state (e.g.
  models.py changed but migrations not yet regenerated breaks every test that
  creates a `User`).
- Message style: conventional commits, e.g. `refactor: give User and Token
  UUID primary keys, squash core/notes migrations to fresh initials`.
- Do NOT push or open a PR unless the operator instructed it.

## Steps

### Step 1: Change the model base classes

In `core/models.py`, change:

```python
class User(AbstractUser):
```
to
```python
class User(UUIDModel, AbstractUser):
```

and change:
```python
class Token(CreatedAtModel):
```
to
```python
class Token(UUIDModel, CreatedAtModel):
```

`UUIDModel` is already defined above both classes in the same file, so no
new import is needed.

**Verify**: this step alone is not independently testable (the migration
history now disagrees with the model state) — proceed to Step 2 before
running any Django management command that touches the database or app
registry.

### Step 2: Sanity-check the model change in isolation

In the `use_example_api=yes api_auth=token` bake (so both `User` and `Token`
render), after applying Step 1's edit:

**Verify**: `uv run manage.py check` → `System check identified no issues (0
silenced)`. This catches any MRO/field-clash problem from the base-class
change before you touch migrations. If this fails, STOP — do not attempt to
work around a system-check error by reordering bases differently from
`class User(UUIDModel, AbstractUser)` / `class Token(UUIDModel,
CreatedAtModel)` without understanding why; report what `check` says instead.

### Step 3: Delete the old migrations

In the template source (not a bake — edit these files directly):

```
rm '{{cookiecutter.project_slug}}/src/apps/core/migrations/0001_initial.py'
rm '{{cookiecutter.project_slug}}/src/apps/core/migrations/0002_token.py'
rm '{{cookiecutter.project_slug}}/src/apps/notes/migrations/0001_initial.py'
rm '{{cookiecutter.project_slug}}/src/apps/notes/migrations/0002_note_notes_note_owner_i_b6b830_idx.py'
```

Keep both `migrations/__init__.py` files untouched.

**Verify**: `ls '{{cookiecutter.project_slug}}/src/apps/core/migrations/'
'{{cookiecutter.project_slug}}/src/apps/notes/migrations/'` → each shows only
`__init__.py`.

### Step 4: Generate the "token" shape

Bake with `use_example_api=yes api_auth=token` (see commands table). Copy
your Step 1+3 changes into the bake (or re-bake from a template checkout with
the changes already applied — either way, the bake must contain both the new
`models.py` and the emptied `migrations/` directories). Then, inside the
bake:

```
uv run manage.py makemigrations core notes
```

This creates exactly two new files:
`src/apps/core/migrations/0001_initial.py` (with `CreateModel(User)` and
`CreateModel(Token)`, both with UUID ids — Token's FK to
`settings.AUTH_USER_MODEL` needs no `swappable_dependency` since `User` is
created in the same file, same as today) and
`src/apps/notes/migrations/0001_initial.py` (with `CreateModel(Note)`,
`Meta.indexes` embedded directly in `options=` instead of a separate
`AddIndex` — Django does this automatically when a model's `Meta.indexes` is
already populated at generation time; you do not need to hand-craft this).

Save both files' contents somewhere you can diff against Step 5's output
(e.g. `cp` them to a scratch location outside the bake).

**Verify**: `uv run manage.py makemigrations --check --dry-run` → exit 0,
"No changes detected".

### Step 5: Generate the "no Token" shape for `core`

Bake with `use_example_api=yes` (no `api_auth=token` — defaults to
`session`, per `cookiecutter.json`). Apply the same Step 1+3 changes. Inside
this bake:

```
uv run manage.py makemigrations core
```

This creates `src/apps/core/migrations/0001_initial.py` with only
`CreateModel(User)` — no `Token` operation at all, since the `Token` class
doesn't render into `models.py` for this combo. You do not need to run this
for `notes` — `Note` doesn't vary by `api_auth`, so Step 4's
`notes/migrations/0001_initial.py` is already final.

**Verify**: `uv run manage.py makemigrations --check --dry-run` → exit 0,
"No changes detected".

### Step 6: Hand-merge `core/migrations/0001_initial.py`

Diff Step 4's `core/migrations/0001_initial.py` (has Token) against Step 5's
(no Token). The diff isolates exactly two things: (a) the imports Token's
`CreateModel` needs that User's doesn't (`django.db.models.deletion` for
`on_delete=CASCADE`, `from django.conf import settings` for
`to=settings.AUTH_USER_MODEL`), and (b) the `Token` `CreateModel` operation
itself.

Write the merged, Jinja-conditional file back into the template source at
`{{cookiecutter.project_slug}}/src/apps/core/migrations/0001_initial.py`:
start from Step 5's content (the "no Token" baseline, since it's the
strict subset), then wrap the Token-only imports and the Token-only
`CreateModel` operation in
`{%- if cookiecutter.use_example_api == "yes" and cookiecutter.api_auth == "token" %}`
/ `{%- endif %}`, matching the exact shape shown in the "Current state"
section's `apps.py` excerpt (conditional list element, trailing comma stays
attached to the element, `{%- if %}`/`{%- endif %}` on their own lines with
the `-` to strip surrounding whitespace). `User`'s `CreateModel` stays
unconditional. The file's `dependencies` list stays
`[("auth", "0012_alter_user_first_name_max_length")]` unconditionally (Token
needs no additional dependency — it's created in the same migration as the
`User` it references).

Copy Step 4's `notes/migrations/0001_initial.py` into the template source at
`{{cookiecutter.project_slug}}/src/apps/notes/migrations/0001_initial.py`
verbatim — no Jinja needed.

**Verify**: re-bake both the token combo and the session combo from the
now-edited template source (fresh `-o` directories), and in each:
`uv run manage.py makemigrations --check --dry-run` → exit 0, "No changes
detected" in **both**. This is the step that actually proves the
hand-written Jinja renders correctly for both shapes — a syntax mistake in
the conditional will either produce invalid Python (bake fails immediately)
or silently include/exclude the wrong operations (this check catches that
too, since a mismatch between rendered migration and rendered model state
shows up as detected changes).

### Step 7: Remove the dead `REMOVED_PATHS` entry

In `hooks/post_gen_project.py`, `src/apps/core/migrations/0002_token.py` no
longer exists as a file, so remove it from this list (leave the sibling
entries untouched):

```python
    *(
        [
            "src/apps/api/auth.py",
            "src/apps/api/exceptions.py",
            "src/apps/core/migrations/0002_token.py",
            "tests/api/unit/auth_test.py",
        ]
        if not (USE_EXAMPLE_API == "yes" and API_AUTH == "token")
        else []
    ),
```

becomes:

```python
    *(
        [
            "src/apps/api/auth.py",
            "src/apps/api/exceptions.py",
            "tests/api/unit/auth_test.py",
        ]
        if not (USE_EXAMPLE_API == "yes" and API_AUTH == "token")
        else []
    ),
```

**Verify**: `uvx cookiecutter . -o /tmp/verify-020-hook-check --no-input`
(default combo, no token) completes without a `FileNotFoundError` traceback
from the hook.

### Step 8: Full verification across the bake matrix

For each of the four combos in the commands table (token, session,
no-example-api, throttling), fresh-bake from the finished template source
and run, with Postgres up:

1. `uv run manage.py makemigrations --check --dry-run` → exit 0
2. `uv run manage.py lintmigrations` → exit 0
3. `uv run pytest` → all pass, 100% coverage
4. `uvx ruff@0.15.16 format --check . && uvx ruff@0.15.16 check .` → exit 0
5. `uv run pre-commit run ty --all-files` → exit 0

**Verify**: all five checks pass in all four combos.

## Test plan

No new application tests are needed — this plan changes schema plumbing, not
behavior. The existing suite (`tests/core/unit/models_test.py`,
`tests/api/unit/auth_test.py`, `tests/notes/**`, `tests/core/integration/**`)
already exercises `User`/`Token`/`Note` creation and must keep passing
unchanged at 100% coverage in every combo — that's the regression signal.
Pay attention to any test that special-cased pk type (none were found during
planning, but re-confirm): `grep -rn "isinstance.*\.pk" tests/` and
`grep -rn "\.id ==" tests/` — if either turns up an `int`-typed literal
compared against a `User`/`Token` pk, STOP and report (means a test assumed
the old pk type and needs updating, which is outside this plan's original
scope).

## Done criteria

Machine-checkable. ALL must hold:

- [ ] `core/models.py`: `class User(UUIDModel, AbstractUser):` and `class
      Token(UUIDModel, CreatedAtModel):`
- [ ] `core/migrations/` contains only `__init__.py` and `0001_initial.py`
- [ ] `notes/migrations/` contains only `__init__.py` and `0001_initial.py`
- [ ] `grep -c "0002_token" hooks/post_gen_project.py` → `0`
- [ ] In all four bake-matrix combos: `makemigrations --check --dry-run`
      exits 0, `lintmigrations` exits 0, `pytest` passes at 100% coverage,
      `ruff format --check` + `ruff check` exit 0, `ty` (via pre-commit)
      exits 0
- [ ] `git status --short` shows changes only to the in-scope files listed
      above
- [ ] `plans/README.md` status row updated

## STOP conditions

Stop and report back (do not improvise) if:

- `manage.py check` (Step 2) reports an error from the new base-class order —
  do not silently reorder bases or drop `UUIDModel` to make the error go
  away; report the exact check error.
- The hand-merged `core/migrations/0001_initial.py` (Step 6) fails
  `makemigrations --check --dry-run` in either combo after two reasonable
  fix attempts — the Jinja conditional is likely malformed; report the
  rendered output (`cookiecutter` renders to a real file you can inspect in
  each bake directory) rather than guessing further.
- Any test in the suite fails for a reason other than an obvious pk-type
  literal (see Test plan) — report which test and its failure, don't patch
  around it blindly.
- You discover a third-party `INSTALLED_APPS` dependency (`axes`, `unfold`,
  `django_structlog`, etc.) has its own migration with a hardcoded FK to
  `AUTH_USER_MODEL` that doesn't use `swappable_dependency` — this would be a
  bug in that dependency, not something to fix here; report it and stop.

## Maintenance notes

- Any future model that needs a user FK should reference
  `settings.AUTH_USER_MODEL` (as `Token.user` and `Note.owner` already do),
  never a hardcoded `core.User` string — this keeps the swappable-model
  contract intact regardless of pk type.
- If a future knob introduces a third `core` model that's also conditional
  (like `Token` is today), it joins the same Jinja-conditional pattern in
  `core/migrations/0001_initial.py` — don't reintroduce a separate numbered
  migration file for it unless the model is added to an *already-generated*
  project's upgrade path (not applicable to this template's own source).
- Reviewer: confirm the rendered `core/migrations/0001_initial.py` in the
  "no Token" combo contains zero references to `Token` or
  `django.db.models.deletion` (an unused import would fail `ruff check`
  F401, which Step 8 already gates on, but double-check by eye too).
- Deliberately not done: no attempt to preserve a "clean" incremental
  migration path for hypothetical already-generated downstream projects that
  baked this template before this change — cookiecutter templates are a
  one-time scaffold, not something projects re-sync against, and the
  operator confirmed there's no live data anywhere this could affect.
