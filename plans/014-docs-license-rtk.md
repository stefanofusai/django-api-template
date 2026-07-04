# Plan 014: LICENSE, README truthfulness, and an optional (not mandatory) rtk prefix

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving to the
> next step. If anything in the "STOP conditions" section occurs, stop and
> report — do not improvise. When done, update the status row for this plan
> in `plans/README.md` — unless a reviewer dispatched you and told you they
> maintain the index.
>
> **Drift check (run first)**: `git diff --stat 924bfba..HEAD -- README.md '{{cookiecutter.project_slug}}/README.md' '{{cookiecutter.project_slug}}/AGENTS.md' '{{cookiecutter.project_slug}}/pyproject.toml'`
> READMEs and AGENTS.md are expected to have drifted (plans 002/003/006/007/
> 008/009 all touch them) — this plan runs LAST precisely so it documents the
> final state. Re-read each target file fully before editing.

## Status

- **Priority**: P3
- **Effort**: S
- **Risk**: LOW (docs + metadata only)
- **Depends on**: run after all other selected plans (documents their final state)
- **Category**: docs / dx
- **Planned at**: commit `924bfba`, 2026-07-04

## Why this matters

Four documentation-layer costs with concrete consequences:

1. **No LICENSE anywhere** — the template is publicly distributed
   (`uvx cookiecutter gh:stefanofusai/django-api-template`) with an
   all-rights-reserved default; recipients technically have no usage grant,
   and baked projects ship with no license metadata either.
2. **Baked AGENTS.md mandates `rtk`** ("Always prefix shell commands with
   `rtk`", and all verification commands are `rtk uv run ...`). `rtk` is the
   maintainer's personal CLI wrapper — it exists on his machine, not in the
   template's declared toolchain. Any other consumer's coding agent obeys
   AGENTS.md and gets `command not found` on every command. It must become
   conditional, not mandatory.
3. **README overstatements**: the template README advertises "Hypothesis"
   (declared, never used directly — it powers Schemathesis transitively), and
   its Verification block lists `docker compose up --build` followed by
   `curl`/`down` as one sequence — `up` without `-d` blocks, so the following
   commands never run as written.
4. **Small drift**: `DJANGO_ENV` lives in both `.env.example` and compose
   `environment:` (compose wins — undocumented); AGENTS.md's "one-shot
   migration services should remain `restart: no`" predates the `pre_start`
   migration approach.

## Important context

- Two README files exist: the TEMPLATE root `README.md` (about the template)
  and `{{cookiecutter.project_slug}}/README.md` (baked project). AGENTS.md is
  baked-project only. Preserve all Jinja placeholders in the baked files.
- License choice: **MIT** (single-maintainer permissive default). If the
  operator has expressed a different preference anywhere in `plans/README.md`
  or the repo, use that instead — check first.

## Current state

- `git ls-files | grep -i licen` → only
  `{{cookiecutter.project_slug}}/.agents/skills/mcp-builder/LICENSE.txt`
  (vendored, not the project's).
- `{{cookiecutter.project_slug}}/pyproject.toml` `[project]` has no `license`
  key.
- `{{cookiecutter.project_slug}}/AGENTS.md:5`: "Always prefix shell commands
  with `rtk`."; lines 63-68 list verification commands as
  `rtk uv run pre-commit run ...` / `rtk uv run pytest`.
- Template `README.md:13`: "pytest with 100% coverage, Hypothesis, and
  Schemathesis"; lines 57-65 (Verification block):

  ```shell
  uv run pytest
  uv run pre-commit run --all-files
  docker compose -f .docker/compose/dev.yaml up --build
  curl -fsS http://localhost:8000/api/ready
  docker compose -f .docker/compose/dev.yaml down -v
  ```

- Baked `README.md` "Local Setup" documents `.env.example` vars; the
  `DJANGO_ENV` compose-override subtlety is unmentioned.
- AGENTS.md "Docker And Runtime" contains the vestigial migration-service
  bullet.

## Commands you will need

| Purpose | Command | Expected on success |
|---------|---------|---------------------|
| Bake | `uvx cookiecutter . --no-input -o $BAKE` | exit 0 |
| Tests | `cd $BAKE/my-project && uv run pytest` | all pass, 100% |
| Hooks | `cd $BAKE/my-project && git add -A && uv run pre-commit run --all-files` | all pass (markdownlint gates the doc edits) |
| Root hooks (if 012 landed) | `uvx pre-commit run --all-files` at root | all pass |

## Scope

**In scope**:
- `LICENSE` (create, template root)
- `{{cookiecutter.project_slug}}/LICENSE` (create)
- `{{cookiecutter.project_slug}}/pyproject.toml` (`license` metadata)
- `README.md` (template root)
- `{{cookiecutter.project_slug}}/README.md`
- `{{cookiecutter.project_slug}}/AGENTS.md`

**Out of scope**:
- CHANGELOG / CONTRIBUTING / SECURITY.md — considered, low value at this
  repo's stage; do not add.
- Any behavior change (this plan is text/metadata only).
- The cruft/template-update story — recorded as future direction, not built.

## Git workflow

- Branch: `advisor/014-docs-license-rtk`
- Conventional commit, e.g. `docs: add license, fix readme claims, make rtk optional`
- Do NOT push or open a PR unless the operator instructed it.

## Steps

### Step 1: LICENSE files + metadata

1. Template root `LICENSE`: standard MIT text,
   `Copyright (c) 2026 Stefano Fusai`.
2. Baked `{{cookiecutter.project_slug}}/LICENSE`: MIT text with
   `Copyright (c) 2026 {{ cookiecutter.author_name }}` (Jinja renders it).
3. Baked `pyproject.toml` `[project]`: add `license = "MIT"` (SPDX string,
   PEP 639 — supported by current uv) in the field position Ruff/uv expect
   (after `readme`, before `authors` is conventional; match the file's
   existing key ordering style).
4. Template root README "What You Get" list: add a line for the license
   (alphabetical order of that list per house style).

**Verify**: fresh bake → `test -f $BAKE/my-project/LICENSE` and
`grep -n 'license = "MIT"' $BAKE/my-project/pyproject.toml` → present;
`uv run pytest` still passes (uv parses the new metadata during sync — a
bad SPDX string fails there).

### Step 2: Make rtk optional in baked AGENTS.md

1. Replace line 5's "Always prefix shell commands with `rtk`." with:
   "If the `rtk` CLI is available, prefix shell commands with `rtk`
   (token-optimizing proxy); otherwise run commands directly."
2. In the Testing section, strip the `rtk ` prefix from the four verification
   commands (`uv run pre-commit run ruff-check --all-files`, etc.) and add
   one line after the list: "Prefix these with `rtk` when it is available."
3. Line 63's "final verification should include `rtk uv run pytest`" → drop
   the prefix there too.

**Verify**: `grep -n "rtk" '{{cookiecutter.project_slug}}/AGENTS.md'` → only
the two conditional mentions remain; no command in the file *starts* with
`rtk `.

### Step 3: Template README truthfulness

1. Line 13: "pytest with 100% coverage, Hypothesis, and Schemathesis" →
   "pytest with 100% coverage and Schemathesis property-based contract
   tests". (If a direct Hypothesis test exists by now — check
   `grep -rn "from hypothesis" '{{cookiecutter.project_slug}}/tests'` — keep
   the original wording instead.)
2. Verification block: make it runnable top-to-bottom:

   ```shell
   uv run pytest
   uv run pre-commit run --all-files
   docker compose -f .docker/compose/dev.yaml up -d --build --wait
   curl -fsS http://localhost:8000/api/ready
   docker compose -f .docker/compose/dev.yaml down -v
   ```

3. If Plan 002 landed, confirm the Quickstart "Docker Compose ≥ 2.30" note
   exists in the BAKED README; add the same note to the template README's
   Verification section.

### Step 4: Baked README small fixes

In "Local Setup", add one sentence: "`DJANGO_ENV` in `.env` applies to local
tooling; the Compose files override it per service (`dev`/`prod`)." Check the
rest of the Local Setup list still matches `.env.example` after plans
002/007/009 (each added vars with their own doc lines — reconcile, don't
duplicate).

### Step 5: AGENTS.md vestigial bullet

Replace "Long-running services should use restart policies; one-shot
migration services should remain `restart: no`." with "Long-running services
should use restart policies; migrations run via the Compose `pre_start`
hook on the api service."

### Step 6: Full verification loop

**Verify**: fresh bake → `uv run pytest` → all pass; `git add -A && uv run
pre-commit run --all-files` → all pass (markdownlint validates every edited
markdown file); if Plan 012 landed, root `uvx pre-commit run --all-files` →
all pass.

## Test plan

Docs-only: the executable gates are markdownlint (both trees), uv's metadata
parse (license key), and the greps in Steps 1-2. No pytest changes.

## Done criteria

- [ ] LICENSE at root and in the baked tree; `license = "MIT"` in baked pyproject
- [ ] No baked AGENTS.md command line starts with `rtk `
- [ ] Template README: no unqualified Hypothesis claim; Verification block uses `up -d --build --wait`
- [ ] Baked README documents the DJANGO_ENV override
- [ ] Fresh bake: pytest + pre-commit all pass
- [ ] No files outside the in-scope list modified (`git status`)
- [ ] `plans/README.md` status row updated (and this is the last plan — set the index's overall state)

## STOP conditions

- Any evidence the maintainer wants a license other than MIT (existing
  license text anywhere, a note in plans/README.md) — stop and ask.
- uv rejects the PEP 639 `license = "MIT"` string on the pinned version —
  report and fall back to the classic table form only with operator OK.
- The AGENTS.md rtk edit conflicts with maintainer-side tooling assumptions
  you can see in the repo (e.g. a committed rtk config) — the *baked* projects
  still must not hard-require it; report the tension instead of choosing.

## Maintenance notes

- The rtk wording keeps the maintainer's personal workflow intact (rtk when
  present) while unbreaking everyone else — if rtk ever ships as a public
  dependency of the template, revisit.
- Future plans that add env vars or services: the baked README's Local Setup
  list and the template README's feature list are the two places that go
  stale — check both in review.
- Deferred, recorded as future direction: a `cruft`-based template-update
  story for already-baked projects (no doc promise made anywhere yet).
