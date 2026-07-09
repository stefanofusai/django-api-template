# Plan 018: Build the "new API resource" vendored agent skill

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving to the
> next step. If anything in the "STOP conditions" section occurs, stop and
> report — do not improvise. When done, update the status row for this plan
> in `plans/README.md` — unless a reviewer dispatched you and told you they
> maintain the index.
>
> This plan replaces the former 018 design spike (since removed from
> `plans/`); the delivery vehicle is already decided (a vendored first-party
> agent skill — see "Settled design decision"). Do not re-open the vehicle
> question.
>
> **Drift check (run first)**:
> `git diff --stat 16a12b3..HEAD -- '{{cookiecutter.project_slug}}/src/apps/notes/' '{{cookiecutter.project_slug}}/tests/notes/' '{{cookiecutter.project_slug}}/tests/factories.py' '{{cookiecutter.project_slug}}/tests/conftest.py' '{{cookiecutter.project_slug}}/AGENTS.md' '{{cookiecutter.project_slug}}/.agents/' '{{cookiecutter.project_slug}}/skills-lock.json' hooks/post_gen_project.py`
> If any in-scope file changed since this plan was written, compare the
> "Current state" and "Convention checklist" excerpts against the live code
> before proceeding; on a mismatch that changes a convention, treat it as a
> STOP condition (the checklist below is the skill's spec and must match the
> exemplar it is distilled from).

## Status

- **Priority**: P3
- **Effort**: L (the convention checklist + skill authoring + a validation
  bake that instantiates a real resource and runs the full generated gate)
- **Risk**: LOW (adds one vendored Markdown skill + one lock entry + one
  README line; no runtime code, no change to any generated Python)
- **Depends on**: 016 (**soft** — the skills-lock entry shape; see
  "Coordination with plan 016")
- **Category**: dx / direction
- **Planned at**: commit `16a12b3`, 2026-07-09

## Why this matters

The example `notes` app is the template's only vertical-slice exemplar —
model, controller, schemas, admin, migration, factory, unit + integration
tests — and it is optional (`use_example_api`, deleted at bake when unset via
`hooks/post_gen_project.py`). Adding a second resource today means
reverse-engineering `notes` while hand-satisfying every convention the
generated `AGENTS.md` states in prose. This plan turns "add a resource" —
the single most repeated downstream task in an agent-first template — into
one skill invocation.

The **settled design decision** (do not re-open): the vehicle is a
**vendored, first-party agent skill** at
`'{{cookiecutter.project_slug}}/.agents/skills/new-api-resource/SKILL.md'`
(chosen over a management command and a documented recipe). Rationale to
record in the skill's own preamble:

- It fits the template's agent-first posture and reuses the existing
  `.agents/` + `skills-lock.json` mechanism.
- Conventions are enforced **mechanically** by the generated project's CI
  gates regardless (100% coverage, ruff `ALL`, ty, django-extra-checks,
  the migration linter). The skill therefore only needs to encode the recipe
  well enough that a first pass lands green; it does not need to *guarantee*
  compliance, because the gates do.
- A management command (vehicle A) would mean template-in-template
  maintenance (Jinja that emits Jinja-free Python that must itself track
  every convention change) and ships runtime code for a dev-time task. It
  rots. A documented recipe (vehicle C) is the cheapest and weakest; the
  skill *is* the recipe, made executable.

The skill must be **self-contained**: `use_example_api=no` bakes delete
`src/apps/notes` and `tests/notes`, so the skill CANNOT point at notes files.
It embeds its own miniature exemplar snippets (below) instead.

## Current state

All generated-project paths are under `{{cookiecutter.project_slug}}/`.
Verified by baking `uvx cookiecutter . -o /tmp/verify-018 --no-input
use_example_api=yes api_auth=session` at commit `16a12b3` and walking every
notes-related file.

- `src/apps/notes/` — the exemplar: `models.py` (inherits `UUIDModel,
  CreatedAtUpdatedAtModel` from `apps.core.models`; `owner` FK with
  `db_index`, `related_name`, gettext `verbose_name`; a `(owner, -created_at)`
  index; `Meta.ordering`; `__str__`), `schemas.py` (In/Out/Filter split, In
  closed to writable fields with `max_length`/`min_length`/`NO_NUL_PATTERN`),
  `controllers.py` (ninja-extra `@api_controller` CBV, `auth=django_auth`,
  owner-scoped `get_object_or_404`, pagination/ordering/searching on list),
  `admin.py` (unfold `ModelAdmin`, timestamp-led `list_display`,
  `list_select_related`), `apps.py`, `migrations/0001_initial.py` +
  `0002_*_idx.py`.
- `tests/notes/{integration,unit}/` — integration CRUD + IDOR (404 on other
  users' objects) + 401 + 422 + list filter/search/order/pagination bounds;
  unit controller test; per-tree `conftest.py` registering named model
  fixtures (`note_1`, `note_2`, `note_owner_user_1` via `LazyFixture`).
- `tests/factories.py` — `UserFactory`, `NoteFactory` (factory-boy).
- `tests/conftest.py` — `register(UserFactory)` / `register(NoteFactory)`
  (pytest-factoryboy), the ninja `TestClient` fixtures, and the
  `AuthenticatedTestClient` wrapper fixture `authenticated_v1_api_client`.
- Wiring points a new resource touches:
  - `src/apps/api/api.py` — `v1_api.register_controllers(NotesController)`
    (import + register the new controller here).
  - `src/config/settings/components/apps.py` — `INSTALLED_APPS`, `# Project`
    block (`apps.api`, `apps.core`, `apps.notes`), alphabetical.
  - `pyproject.toml` `[tool.django_migration_linter] include_apps =
    ["core", "notes"]`.
  - `pyproject.toml` `[tool.pytest.ini_options]` enforces
    `--cov-fail-under=100` over `--cov=src --cov=tests`.
- `src/config/settings/components/checks.py` — the active `EXTRA_CHECKS`
  list (the mechanical enforcement of most model conventions below).
- `skills-lock.json` — 6 entries, each `{source, sourceType: "github",
  skillPath, computedHash}`; `version: 1`. `hooks/post_gen_project.py`
  only mutates it to drop `django-celery-expert` when `use_celery=none`.
- `.agents/README.md` — "Vendored Agent Skills", one bullet per skill:
  `` `name`: `source`, LICENSE ``.
- `hooks/post_gen_project.py` `REMOVED_DIRS`/`REMOVED_PATHS` — knob-gated
  deletions. **None reference `new-api-resource`**, so the new skill is
  knob-independent and survives every bake (confirmed by reading lines
  35–89: the only `.agents/` deletion is `django-celery-expert` under
  `use_celery=none`).

## Convention checklist (the skill's spec)

This is the exhaustive, explicitly-enumerated set of conventions a new
resource must satisfy, mined from `AGENTS.md`, `checks.py`, and the notes
exemplar. **40 rules.** They are the SKILL.md body; the skill must encode
every one (most are satisfied automatically by copying the embedded snippets,
but the skill must call them out so a human or agent can verify a hand-edit).

**Model — `src/apps/<app>/models.py`** (django-extra-checks enforces 1–8):

1. Define `__str__` (extra-checks `model-attribute: __str__`).
2. Define `Meta.ordering` (extra-checks `model-meta-attribute: ordering`).
3. Register the model in admin (extra-checks `model-admin`).
4. Every field has a gettext `verbose_name` (`field-verbose-name`,
   `field-verbose-name-gettext`, `field-verbose-name-gettext-case`); help
   text, if any, is gettext (`field-help-text-gettext`).
5. FKs declare explicit `related_name` and `db_index`
   (`field-related-name`, `field-foreign-key-db-index: always`).
6. Choice fields use a DB constraint (`field-choices-constraint`).
7. Use `UniqueConstraint`, never `unique_together` (`no-unique-together`).
8. Respect null rules (`field-null`, `field-text-null`, `field-default-null`);
   text fields use `blank=True`, not `null=True`.
9. Inherit `UUIDModel, CreatedAtUpdatedAtModel` from `apps.core.models`
   (UUIDv7 pk + `created_at`/`updated_at`) — the observed base for
   owner-owned resources.
10. Order model fields logically, not alphabetically: inherited timestamps
    first, then relations (the `owner` FK), then scalar attributes, with
    large `TextField` bodies last.
11. Add an index for the owner-scoped list query:
    `Meta.indexes = (models.Index(fields=["owner", "-created_at"]),)`.

**Schemas — `src/apps/<app>/schemas.py`**:

12. Provide the In/Out/Filter split (`<Model>InSchema`, `<Model>OutSchema`,
    `<Model>FilterSchema`).
13. `<Model>InSchema` is closed to writable fields only, each validated
    (`max_length`, `min_length` for required text, `pattern=NO_NUL_PATTERN`).
14. Order Ninja schema fields to match the model's field order, not
    alphabetically.

**Controller — `src/apps/<app>/controllers.py`**:

15. Use a ninja-extra class-based controller (`@api_controller`,
    `ControllerBase`) mounted at the resource prefix (`/<app>`), with
    route-local paths relative.
16. Set `auth=django_auth` on the controller — the API has no default auth;
    never ship a mutating endpoint unauthenticated.
17. Owner-scope every lookup with `get_object_or_404(<Model>, id=...,
    owner=request.user)` (IDOR protection: other users' rows 404).
18. Each operation's `response=` map declares the error schemas it can emit
    (400/401/403/404/422 as applicable) using `ErrorSchema` /
    `ValidationErrorSchema` from `apps.api.schemas`.
19. List uses `BoundedLimitOffsetPagination`, `@ordering(...)`,
    `@searching(...)`, and `filters.filter(<Model>.objects.filter(
    owner=request.user))`.
20. Alphabetize the controller's public methods (create/delete/get/list/
    update); `request` and other framework-required leading params are exempt
    from parameter alphabetization.

**Admin — `src/apps/<app>/admin.py`**:

21. `@admin.register(<Model>)` on an `unfold.admin.ModelAdmin` subclass.
22. Lead `list_display` with `created_at`, `updated_at`, then other columns.
23. Declare `list_select_related` for FK columns shown in the list.

**App config — `src/apps/<app>/apps.py`**:

24. `AppConfig` subclass with `name = "apps.<app>"`.

**Migrations — `src/apps/<app>/migrations/`**:

25. Run `manage.py makemigrations <app>`; commit the migration.
26. **Annotate the generated migration**: `makemigrations` emits
    `dependencies = [...]` / `operations = [...]` as bare mutable class
    attributes, which ruff `RUF012` rejects. Add
    `from typing import ClassVar` and annotate
    `dependencies: ClassVar[list[tuple[str, str]]]` and
    `operations: ClassVar[list[object]]` to match the notes migrations.
    (This is a required hand-edit — RUF012 has no autofix. See "Validation".)
27. Run `ruff format` on the migration — `makemigrations` emits long
    single-line field definitions that the formatter wraps.

**Factory — `tests/factories.py`**:

28. Add a `<Model>Factory(factory.django.DjangoModelFactory)` with
    `owner = factory.SubFactory(UserFactory)` and Faker-backed fields.
29. Order factory fields to match the model's field order; place a factory
    after any factory it references via `SubFactory` (so `UserFactory` first).

**Factory registration — `tests/conftest.py` + per-tree conftest**:

30. `register(<Model>Factory)` in `tests/conftest.py` (pytest-factoryboy),
    and import it in the factories import line.
31. In `tests/<app>/integration/conftest.py`, register named model fixtures
    with sequence suffixes (`<model>_1`, `<model>_2`) and a
    `<model>_owner_user_1` via `LazyFixture("user_1")` for IDOR tests.
32. In `tests/<app>/unit/conftest.py`, expose a
    `<app>_controller_client` fixture (`ninja_extra.testing.TestClient`).

**Tests — `tests/<app>/{integration,unit}/`**:

33. Organize by app then type; `tests/conftest.py` auto-applies the
    `integration`/`unit` marker from the path segment (no manual marker).
34. Test names follow `test_<subject>_<expected>_when_<condition>` (or
    `for_<scenario>`); keep functions alphabetized within each file.
35. Drive endpoints through the ninja `TestClient` fixtures
    (`v1_api_client`, `authenticated_v1_api_client`), read `response.data`,
    use router-relative paths, pass `user=` for authenticated calls.
36. Cover the full behavior set so 100% coverage is reached: create (201,
    401, 422×2), delete (204 owner, 404 other user), detail (200 owner, 404
    other user), list (pagination cap, 401, 422 limit/offset over max,
    unknown-ordering-ignored, owner-only, filter, order, second page,
    search across both text fields), update (200 owner, 422 over-length, 404
    other user). An under-specified test set leaves controller branches
    uncovered and fails `--cov-fail-under=100`.
37. Admin: a staff/superuser changelist-200 test resolving the URL with
    `django.urls.reverse("admin:<app>_<model>_changelist")`.
38. Use Faker/factory values for incidental data; keep fixed literals only
    when they are the behavior under test; avoid `Model.objects.create(...)`
    (use factories).

**Wiring**:

39. Add `"apps.<app>"` to `INSTALLED_APPS` (`# Project` block, alphabetical),
    add `<app>` to `[tool.django_migration_linter] include_apps`, and import
    + register the controller in `src/apps/api/api.py`
    (`v1_api.register_controllers(NotesController, <Model>sController)`).
40. Final verification is the full generated gate: `uv run pytest` at 100%
    coverage **and** `uv run pre-commit run --all-files` (ruff, ty,
    extra-checks) **and** the migration CI check
    (`manage.py makemigrations --check --dry-run` + `manage.py
    lintmigrations`).

### notes ↔ AGENTS.md divergences found

Mined during the inventory; **1 confirmed divergence** (well under the
>5-divergences reconciliation threshold in STOP conditions):

1. **`AGENTS.md` names a fixture `authenticated_client` that does not
   exist.** The Testing section says to test through
   `internal_api_client`, `v1_api_client`, `authenticated_client` and to
   "use `authenticated_client`" for authenticated endpoints — but the
   only such fixture the baked project defines is
   `authenticated_v1_api_client` (confirmed: `grep -rn authenticated_client`
   over the baked tree returns nothing). The skill must use the real name,
   `authenticated_v1_api_client`. *This is a latent `AGENTS.md` doc bug worth
   a one-line fix in a future docs pass; it is out of scope here (this plan
   does not touch `AGENTS.md`).*

Borderline items examined and deliberately NOT recorded as divergences: the
`<Model>OutSchema` field order (`id` first, then the inherited timestamps)
vs. the model's inherited-timestamps-first layout — this is a defensible
read of "match the model's field order" for the serialized surface and the
notes exemplar does exactly this, so the skill mirrors it rather than
flagging it.

### Validation already performed (proof the recipe lands green)

This recipe was exercised end-to-end during planning, in the
`use_example_api=yes api_auth=session` bake, by instantiating a toy `widgets`
resource (a user-owned model with a `name` CharField and a `description`
TextField — the minimal shape that exercises filter/search/order/pagination)
following the checklist above, then running the full generated gate against a
throwaway Postgres. Results:

- `uv run pytest` → **95 passed, 100.00% coverage** (the widgets files reach
  100% with the test set enumerated in rule 36; a thinner test set does not).
- `uv run pre-commit run --all-files` → **all hooks pass** (ruff, ty,
  markdownlint, yamllint, deptry, uv-lock, etc.).
- Migration CI checks → `makemigrations --check --dry-run` clean;
  `lintmigrations` → `(widgets, 0001_initial)... OK`, 0 erroneous.

Two gaps the bake surfaced (both now encoded as rules 26–27, and the reason
the validation bake in Step 5 is mandatory, not optional):

- `makemigrations` output trips ruff `RUF012` until `dependencies`/
  `operations` get `ClassVar` annotations (no autofix — a required hand-edit).
- `makemigrations` emits long single-line field defs that `ruff format`
  rewraps.

The toy resource was deleted after validation.

## Commands you will need

Baking and the generated suite need Postgres; the bake dir is disposable.

| Purpose | Command | Expected on success |
|---------|---------|---------------------|
| Bake exemplar | `uvx cookiecutter . -o /tmp/verify-018 --no-input use_example_api=yes api_auth=session` | project at `/tmp/verify-018/my-project` |
| Bake no-example (survival) | `uvx cookiecutter . -o /tmp/verify-018-noex --no-input use_example_api=no` | `.agents/skills/new-api-resource/SKILL.md` still present; no `src/apps/notes` |
| Deps | `uv sync --locked` (in the bake) | resolved env |
| Postgres for suite | `docker compose -f .docker/compose/dev.yaml --env-file=.env up -d --wait postgres` | `postgres` healthy |
| Full suite | `uv run pytest` (in the bake) | `100%`, all passed |
| Full pre-commit | `uv run pre-commit run --all-files` (in the bake) | all hooks pass |
| Skill markdown lint | `uvx pre-commit run markdownlint --files '{{cookiecutter.project_slug}}/.agents/skills/new-api-resource/SKILL.md'` | pass (see note in Step 1) |

Note: `.agents/` is `_copy_without_render` — write pure Markdown, no Jinja,
in the SKILL.md. If port 5432 is already taken by another container, run a
throwaway Postgres on another port and export a matching `DATABASE_URL` for
the suite (the pytest env's `DATABASE_URL` is a `D:`-prefixed default and is
overridable).

## Scope

**In scope** (four files, all under the template):

- `'{{cookiecutter.project_slug}}/.agents/skills/new-api-resource/SKILL.md'`
  (create — the skill).
- `'{{cookiecutter.project_slug}}/skills-lock.json'` (add one entry).
- `'{{cookiecutter.project_slug}}/.agents/README.md'` (add one line under a
  new "First-party skills" note — see Step 3).
- `'{{cookiecutter.project_slug}}/AGENTS.md'` — **only** the one-line pointer
  in Step 4 (optional; see Step 4 for the decision). No convention changes.

**Out of scope** (do NOT touch):

- `src/apps/notes/`, `tests/notes/`, `tests/factories.py`, `tests/conftest.py`
  — the exemplar is copied FROM, never modified.
- `hooks/post_gen_project.py` — the skill is knob-independent; confirm (do
  not edit) that no removal list references `new-api-resource` (Step 4).
- Any generated Python, `checks.py`, or the CI workflows.

## Git workflow

- Conventional commit, e.g. `feat: add new-api-resource agent skill`.
- Do NOT push unless instructed.

## Steps

### Step 1: Author the SKILL.md

Match the frontmatter format of the existing vendored skills — read
`'{{cookiecutter.project_slug}}/.agents/skills/django-access-review/SKILL.md'`
first. It uses YAML frontmatter with `name`, `description`, `allowed-tools`,
`license`. For this **first-party, file-writing** skill:

- `name: new-api-resource`
- `description`: one line with trigger keywords, e.g. `Scaffold a new
  authenticated, owner-scoped API resource (model, schemas, ninja-extra
  controller, admin, migration, factory, tests) following this project's
  AGENTS.md conventions. Use when adding a new REST resource / endpoint /
  CRUD app. Trigger: "new resource", "add an endpoint", "new model API".`
- `allowed-tools: Read, Write, Edit, Bash` (it writes files and runs
  `makemigrations`; do NOT copy the read-only tool set from the review
  skills).
- Omit `license` (or set it to note the skill is first-party, part of this
  template) — there is no separate upstream LICENSE file to reference.

Body structure:

1. **Preamble**: what the skill does and the "Why this matters" rationale
   above (agent-first; CI gates are the real enforcement; the skill is the
   recipe made executable). State that it is self-contained and does not
   depend on `notes` existing.
2. **Inputs**: the resource name (singular + plural, e.g. `widget`/`widgets`,
   `Widget`), its owner (default: the auth user), and its scalar fields.
3. **The convention checklist** (all 40 rules above, verbatim — this is the
   spec).
4. **Embedded file templates** (below), with placeholders `<app>` (snake
   plural), `<Model>` (PascalCase singular), `<model>` (snake singular).
5. **Post-generation todo list** (Step's rules 25–27, 30–32, 39): run
   `makemigrations <app>`, annotate + format the migration, register the
   factory, wire `INSTALLED_APPS` / `api.py` / migration-linter
   `include_apps`.
6. **Acceptance self-test** (rule 40): the resource is done only when
   `uv run pytest` is green at 100% coverage AND
   `uv run pre-commit run --all-files` passes AND the migration checks pass
   (start Postgres first). Tell the reader to add tests until coverage is
   100% rather than lowering the bar.

The embedded templates are the validated `widgets` files with the toy names
replaced by placeholders. Include, in full, the model, schemas, controller,
admin, apps, factory, per-tree conftests, unit test, admin test, and — most
importantly for coverage — the complete integration test set (rule 36). The
canonical content for each is exactly the notes exemplar generalized; the
`widgets` version validated during planning is the reference. Key template
excerpts the skill must contain (abbreviated here; the skill carries them in
full):

```python
# src/apps/<app>/models.py
from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.models import CreatedAtUpdatedAtModel, UUIDModel


class <Model>(UUIDModel, CreatedAtUpdatedAtModel):
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        db_index=True,
        on_delete=models.CASCADE,
        related_name="<app>",
        verbose_name=_("owner"),
    )
    name = models.CharField(_("name"), max_length=255)
    description = models.TextField(_("description"), blank=True)

    class Meta:
        indexes = (models.Index(fields=["owner", "-created_at"]),)
        ordering = ("-created_at",)
        verbose_name = _("<model>")
        verbose_name_plural = _("<app>")

    def __str__(self) -> str:
        return self.name
```

```python
# src/apps/<app>/migrations/0001_initial.py — the REQUIRED hand-edit (rule 26)
import uuid
from typing import ClassVar

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies: ClassVar[list[tuple[str, str]]] = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]
    operations: ClassVar[list[object]] = [
        # ... makemigrations output, then `ruff format` (rule 27) ...
    ]
```

The controller, schemas, admin, factory, conftests, and the full test files
follow the notes exemplar one-to-one with the name substitution; the skill
embeds them verbatim (the planning bake proved they reach 100% coverage and
pass every hook).

**Verify**: the file is valid Markdown with parseable YAML frontmatter, is
Jinja-free (`.agents/` is `_copy_without_render`), and markdownlint passes.
`plans/` is pre-commit-excluded but `.agents/skills/**` under a bake is not —
run markdownlint against the SKILL.md inside a fresh bake, or directly:
`uvx pre-commit run markdownlint --files
'{{cookiecutter.project_slug}}/.agents/skills/new-api-resource/SKILL.md'`.

### Step 2: Add the skills-lock.json entry

Add a `new-api-resource` entry so plan 016's verify gate covers it against
tampering. Because it is first-party (not fetched from a GitHub repo), it has
NO `source`; mark it `"sourceType": "local"`:

```json
"new-api-resource": {
  "sourceType": "local",
  "skillPath": ".agents/skills/new-api-resource/SKILL.md",
  "computedHash": "<sha256 per plan 016's confirmed recipe>"
}
```

Keep the object's keys alphabetical to match the existing entries and insert
`new-api-resource` in alphabetical position among the skills. Compute
`computedHash` with plan 016's settled recipe: **`sha256` of the raw
`SKILL.md` bytes** (`shasum -a 256 <file>`). If 016 has already landed, the
lock is at `version: 2` and every entry uses that recipe; if it has not, add
the entry with the same recipe anyway and note in the commit message that
016's re-baseline will cover seven entries.

**Verify**: `python -c "import json,
pathlib; json.loads(pathlib.Path('/tmp/verify-018/my-project/skills-lock.json').read_text())"`
parses; the entry is present in a fresh bake and survives a `use_celery=none`
bake (only `django-celery-expert` is pruned).

### Step 3: Add the .agents/README.md line

The README is titled "Vendored Agent Skills" and lists upstream
source+license per skill. `new-api-resource` is first-party, not vendored, so
do not list it as an upstream import. Add a short separate note, e.g. under
the existing list:

```markdown
## First-party skills

- `new-api-resource`: maintained in this template (no upstream source);
  scaffolds a new API resource per `AGENTS.md`.
```

Keep prose consistent with the file's existing style.

**Verify**: markdownlint passes on `.agents/README.md` in a bake.

### Step 4: Confirm knob-independence (no hook change) and add the pointer

- **No `post_gen_project.py` change.** Confirm (read, do not edit) that
  `REMOVED_DIRS`/`REMOVED_PATHS` never reference `new-api-resource`; the
  skill must survive all bakes. Verify empirically with the `use_example_api=no`
  survival bake in "Commands".
- **Optional one-line pointer in `AGENTS.md`.** Consider adding a single
  bullet under the Testing/structure area pointing agents at the skill for
  new resources (e.g. "To add a new API resource, use the `new-api-resource`
  agent skill in `.agents/skills/`."). This is the ONLY `AGENTS.md` edit in
  scope; if you add it, do NOT change any existing convention text. If in
  doubt, leave `AGENTS.md` untouched and mention the skill's discoverability
  in the open questions.

### Step 5: Validation bake (mandatory — rebuild the widgets proof)

Repeat the planning validation to prove the shipped skill text is correct
(the skill's snippets are what changed; regenerate a toy resource by
following the SKILL.md as written, not from memory):

1. Bake `use_example_api=yes api_auth=session` into `/tmp/verify-018`.
2. In the bake, follow the SKILL.md to create a throwaway resource (e.g.
   `widgets`). `uv sync --locked`.
3. Start Postgres:
   `docker compose -f .docker/compose/dev.yaml --env-file=.env up -d --wait postgres`
   (if 5432 is busy, use a throwaway Postgres on another port and export a
   matching `DATABASE_URL`).
4. `uv run pytest` → **100% coverage, all passed**.
5. `uv run pre-commit run --all-files` → all hooks pass.
6. Migration checks: `manage.py makemigrations --check --dry-run` (clean) and
   `manage.py lintmigrations` (the new migration `OK`).
7. **Delete the toy resource** (or just discard the disposable bake dir).

If any gate fails, the SKILL.md text is wrong — fix the skill (and this
plan's checklist if a rule is missing) and re-run. Do not ship a skill whose
own output fails the gate.

## Test plan

The skill's acceptance criterion IS a test: a resource generated by
following the skill must pass the generated project's full gate. Step 5
exercises this once against a real bake. There is no root-repo unit test for
the skill (it is Markdown consumed by an agent); the guarantee is the
validation bake plus plan 016's hash-verify gate (tamper detection).

## Done criteria

- [ ] `.agents/skills/new-api-resource/SKILL.md` exists, is Jinja-free, valid
  Markdown with parseable frontmatter (`allowed-tools: Read, Write, Edit,
  Bash`), and contains all 40 checklist rules + the embedded templates + the
  post-gen todo + the acceptance self-test.
- [ ] `skills-lock.json` has a `new-api-resource` entry with
  `"sourceType": "local"`, no `source`, and a `computedHash` (016's recipe).
- [ ] `.agents/README.md` notes the first-party skill.
- [ ] The skill survives a `use_example_api=no` bake (present, no notes).
- [ ] Step 5 validation bake is green: `uv run pytest` at 100%,
  `uv run pre-commit run --all-files` passes, migration checks pass.
- [ ] `git status` clean apart from the in-scope files.
- [ ] `plans/README.md` status row updated.

## STOP conditions

Stop and report back if:

- A fresh bake's `notes` files diverge from the checklist/embedded templates
  in a way that changes a convention (the skill would ship a stale recipe) —
  more than the one recorded `authenticated_client` naming divergence, or a
  new divergence in model/controller/schema/test shape.
- The Step 5 validation bake cannot reach 100% coverage by following the
  skill text as written — it means the embedded test set (rule 36) is
  incomplete; fix the skill, do not lower the coverage bar or add
  `# pragma: no cover`.
- The lock's existing entries visibly use a different hash recipe than plan
  016's settled `sha256(raw SKILL.md bytes)` AND plan 016 has not landed —
  ship this entry with the settled recipe anyway and flag the mixed-recipe
  state in your report rather than inventing a third recipe.

## Maintenance notes

- **Any future `AGENTS.md` convention change must update this skill** (and
  this plan's checklist). Add "update `new-api-resource`" to the definition
  of done for convention changes — otherwise the skill rots into a
  convention-violation generator.
- The one recorded divergence (`authenticated_client` in `AGENTS.md`) should
  be fixed to `authenticated_v1_api_client` in a future docs pass; the skill
  already uses the correct name.

## Coordination with plan 016 (soft dependency, both directions)

Plan 016 (`016-skills-lock-verify-gate.md`) adds a verify-only
`scripts/check_skills_lock.py` that recomputes the sha256 of each vendored
`SKILL.md` (raw bytes) and compares it to `skills-lock.json`, re-baselining
the lock to that recipe at `version: 2`. For this plan's first-party entry to
coexist:

- **This plan → 016**: the `new-api-resource` entry uses
  `"sourceType": "local"` and has NO `source` field. Its `computedHash` must
  be produced by the exact recipe 016 pins down, so 016's check validates it.
- **016 → this plan**: 016's `check_skills_lock.py` must NOT require a
  `source` repo for entries where `sourceType == "local"`; it should still
  recompute and compare `computedHash` for them (tamper coverage). Record
  this as a soft dependency in plan 016 as well.

Either plan may land first; the recipe is the same either way. 016's
`check()` reads only `computedHash` per entry, so the source-less local entry
needs no special handling; if this plan lands first, 016's re-baseline simply
covers seven entries instead of six.
