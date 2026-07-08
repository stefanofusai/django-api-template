# Plan 018: SPIKE — design a "new API resource" scaffold

> **Executor instructions**: This is a DESIGN/INVESTIGATION plan, not a
> build plan. The deliverable is a design document at
> `plans/018-resource-scaffold-design.md` — you must NOT modify any file
> outside `plans/`. When done, update the status row for this plan in
> `plans/README.md` — unless a reviewer dispatched you and told you they
> maintain the index.
>
> **Drift check (run first)**:
> `git diff --stat 75c4dce..HEAD -- '{{cookiecutter.project_slug}}/src/apps/notes/' '{{cookiecutter.project_slug}}/tests/notes/' '{{cookiecutter.project_slug}}/AGENTS.md'`
> On drift, re-read before writing the design.

## Status

- **Priority**: P3
- **Effort**: M for the design; implementation likely L (coarse — say so in
  estimates)
- **Risk**: LOW (no code changes in this plan)
- **Depends on**: none (but read plans/006-token-lifecycle-endpoints-spike.md
  if present-and-done — a token-lifecycle resource would be the scaffold's
  second real consumer)
- **Category**: direction
- **Planned at**: commit `75c4dce`, 2026-07-08

## Why this matters

The example `notes` app is the template's only vertical-slice exemplar —
model, controller, schemas, admin, migration, factory, unit + integration
tests — and it is optional (`use_example_api`, deleted at bake when unset).
The generated `AGENTS.md` encodes roughly thirty structural conventions a
second resource must satisfy by hand: field ordering, django-extra-checks
requirements, test-tree layout, factory registration, router mounting. For
an "agent-first" template, "add a resource" is the single most repeated
downstream task, and today it means reverse-engineering notes while
satisfying every convention from prose. A scaffold — management command,
vendored agent skill, or documented recipe — turns that into one step. This
spike decides the delivery vehicle and specifies the scaffold's contract.

## Current state

Facts to verify and mine during investigation (all paths under
`{{cookiecutter.project_slug}}/`):

- `src/apps/notes/` — the exemplar: `models.py` (UUID pk,
  `(owner, -created_at)` index, timestamps), `controllers.py` (ninja-extra
  CBV, owner-scoped queries), `schemas.py` (`NoteInSchema` closed to
  title/body, `NoteFilterSchema`, `NoteOutSchema`), `admin.py`
  (`list_select_related`), `migrations/0001_*.py`, `apps.py`.
- `tests/notes/` + `tests/factories.py` — factory-boy +
  pytest-factoryboy registration, integration tests covering CRUD + IDOR
  (404 on other users' objects), unit tests.
- `AGENTS.md` — the conventions the scaffold must encode; read the whole
  "Style"/structure sections and COUNT the rules that apply to a new
  resource (the design doc must list them explicitly — they are the
  scaffold's spec).
- Wiring points a new resource touches: router mounting on the v1 API
  (`src/apps/api/` — find where notes' router is registered),
  `INSTALLED_APPS` (`src/config/settings/components/apps.py`), pyproject
  `[tool.django_migration_linter] include_apps`, and the 100% coverage gate
  (every generated line must arrive tested).
- Constraint: the scaffold itself lives in generated projects, so it must
  survive `use_example_api=no` bakes (it cannot depend on notes existing —
  or it templates FROM notes only when present; resolve this in the design).

## Scope

**In scope**: `plans/018-resource-scaffold-design.md` (create — only file).

**Out of scope**: implementing the scaffold; changing notes; changing
AGENTS.md.

## Steps

### Step 1: Inventory the contract

Bake `use_example_api=yes api_auth=session`, walk every notes-related file,
and produce the exhaustive checklist a new resource must satisfy (file list
+ per-file conventions + wiring points + test expectations). This checklist
IS the scaffold spec; completeness here is most of the spike's value.

### Step 2: Evaluate delivery vehicles

- **A. Django management command** (`manage.py startresource <name>`):
  deterministic, testable, works without an agent; costs template-in-template
  maintenance (the scaffold's file templates must track every convention
  change) and ships runtime code for a dev-time task.
- **B. Vendored agent skill** (`.agents/skills/new-resource/SKILL.md`):
  fits the agent-first posture and the existing `.agents/` mechanism
  (plus `skills-lock.json` — coordinate with plan 016's lifecycle design);
  instructions stay prose (cheap to maintain, LLM executes), but no
  guarantee of convention compliance beyond the existing CI gates.
- **C. Documented recipe** in the generated README/AGENTS.md: cheapest,
  weakest.

Score each against: convention-compliance guarantee, maintenance cost when
conventions change, works-for-humans vs works-for-agents, and
`use_example_api=no` behavior.

### Step 3: Write the design doc

`plans/018-resource-scaffold-design.md`: the step-1 checklist,
vehicle comparison, recommendation, the scaffold's user-facing contract
(exact invocation, inputs, generated files, post-generation todo list),
whether notes becomes the scaffold's reference output (i.e. scaffold
regenerates notes byte-identically — a strong self-test), implementation
effort estimate (expect L), and open questions for the maintainer.

## Done criteria

- [ ] Design doc exists with the complete convention checklist (explicitly
  enumerated, not "~30 rules"), vehicle recommendation, contract, and
  estimate
- [ ] No file outside `plans/` modified
- [ ] `plans/README.md` status row updated

## STOP conditions

- The notes app diverges from AGENTS.md's stated conventions anywhere —
  record each divergence in the design doc (it is a finding: either the doc
  or the exemplar is wrong) and continue; but if divergences are extensive
  (>5), stop and report — the conventions need reconciling before a scaffold
  can encode them.

## Maintenance notes

- Whichever vehicle is chosen, add "update the scaffold" to the definition
  of done for any future convention change in AGENTS.md — otherwise the
  scaffold rots into a convention-violation generator.
