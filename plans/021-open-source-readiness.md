# Plan 021: Open-source readiness — de-personalized defaults, complete README, LICENSE, community files (supersedes plan 014)

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving to the
> next step. If anything in the "STOP conditions" section occurs, stop and
> report — do not improvise. When done, update the status row for this plan
> in `plans/README.md` — unless a reviewer dispatched you and told you they
> maintain the index.
>
> **Drift check (run first)**: `git diff --stat 28d30e8..HEAD -- README.md cookiecutter.json '{{cookiecutter.project_slug}}/README.md' '{{cookiecutter.project_slug}}/AGENTS.md' '{{cookiecutter.project_slug}}/pyproject.toml'`
> This plan runs LAST and documents the LIVE state — READMEs are expected to
> have drifted via other plans; re-read every target file fully before
> editing. On a mismatch in `cookiecutter.json` versus the excerpt below,
> STOP.

## Status

- **Priority**: P2
- **Effort**: M
- **Risk**: LOW (docs, metadata, and default-value changes; one behavioral surface — cookiecutter defaults — is CI-covered)
- **Depends on**: run LAST, after all other selected plans (it documents their final state). **Supersedes plan 014 entirely** — mark 014's index row SUPERSEDED; do not execute both.
- **Category**: docs / dx
- **Planned at**: commit `28d30e8`, 2026-07-05

## Why this matters

The template is about to be published as open source
(`uvx cookiecutter gh:stefanofusai/django-api-template`), and today it is
still shaped like a personal tool: the cookiecutter defaults bake the
maintainer's real name/email into every generated project, there is no
LICENSE anywhere (all-rights-reserved by default — recipients technically
have no usage grant), the baked AGENTS.md hard-requires `rtk` (a personal
CLI wrapper that fails with "command not found" for everyone else), the
root README documents neither the template's opinionated choices nor the
configuration a new user must supply, and the vendored `.agents/` skills
are redistributed without verified upstream licenses. This plan makes the
repo publishable: neutral defaults, a README that states every choice and
required configuration, LICENSE + minimal community files, and a
redistribution check.

## Important context: this is a cookiecutter template

- Project code lives under the literal `{{cookiecutter.project_slug}}/` dir —
  quote it in shell. Preserve every `{{ cookiecutter.* }}` placeholder.
- Verification = bake (`uvx cookiecutter . --no-input -o <dir>`) + baked
  suite (`uv run pytest`, 100%) + baked pre-commit. Root-level markdown is
  linted only if the root pre-commit config (plan 012) exists — check.

## Current state

- `cookiecutter.json` (whole file at `28d30e8`):

  ```json
  {
      "project_name": "My Project",
      "project_slug": "{{ cookiecutter.project_name.lower().replace(' ', '-').replace('_', '-') }}",
      "description": "A Django Ninja API service.",
      "author_name": "Stefano Fusai",
      "author_email": "stefanofusai@gmail.com",
      "github_username": "stefanofusai",
      "_copy_without_render": [
          ".github/workflows/*",
          ".agents/*"
      ]
  }
  ```

- Root `README.md`: 66 lines — What You Get (stale: still lists Hypothesis,
  which nothing imports directly; missing features landed since), Usage,
  Variables table (defaults show the personal identity), Post-Generation,
  Verification (the compose block runs `up --build` in the foreground, so
  the `curl`/`down` lines after it never execute as written; "Docker with
  Compose lifecycle hook support" doesn't name the ≥ 2.30 floor).
- Personal identity appears in exactly two files (verified by grep):
  `README.md` and `cookiecutter.json`. The `gh:stefanofusai/...` Usage URL
  is the real repository coordinate — it STAYS.
- No LICENSE at the root or in `{{cookiecutter.project_slug}}/`; the only
  license in-tree is the vendored
  `.agents/skills/mcp-builder/LICENSE.txt`. Baked `pyproject.toml
  [project]` has no `license` key.
- Baked `AGENTS.md:5`: "Always prefix shell commands with `rtk`." and the
  Testing section lists `rtk uv run ...` commands — `rtk` is not part of
  the template's toolchain.
- Vendored skills in `{{cookiecutter.project_slug}}/.agents/skills/`:
  `django-celery-expert`, `django-expert` (source
  `vintasoftware/django-ai-plugins`), `mcp-builder` (source
  `anthropics/skills`, has LICENSE.txt), `postgres` (source
  `planetscale/database-skills`). Sources and hashes recorded in
  `skills-lock.json` (which may still contain a stale
  `playwright-best-practices` entry — plan 010's item, not yours).
- The `pre_gen_project.py` email check accepts `john.doe@example.com`
  under both the current `"@" in` check and plan 011's stricter regex.
- CI (`.github/workflows/ci.yaml`) bakes with `--no-input`, so default
  values are exercised on every push — your default changes are CI-covered.
- Conventions: alphabetical list ordering (AGENTS.md), extended YAML block
  style, conventional commits via gitlint.

## Commands you will need

| Purpose | Command | Expected on success |
|---------|---------|---------------------|
| Bake (defaults) | `uvx cookiecutter . --no-input -o $BAKE` (template root) | exit 0 |
| Tests | `cd $BAKE/my-project && uv run pytest` | all pass, 100% |
| Hooks | `cd $BAKE/my-project && git add -A && uv run pre-commit run --all-files` | all pass |
| Identity sweep | `rg -in "stefano" . --glob '!plans/**' --glob '!.git/**'` (template root) | matches ONLY the Usage URL in README.md and the root LICENSE copyright line |
| Root hooks (only if plan 012 landed) | `uvx pre-commit run --all-files` | all pass |

## Scope

**In scope**:
- `cookiecutter.json` (three default values)
- `README.md` (template root — restructure per Step 3)
- `LICENSE` (create, template root)
- `CONTRIBUTING.md` (create, template root)
- `SECURITY.md` (create, template root)
- `{{cookiecutter.project_slug}}/LICENSE` (create)
- `{{cookiecutter.project_slug}}/pyproject.toml` (`license` key only)
- `{{cookiecutter.project_slug}}/README.md` (truthfulness fixes, Step 5)
- `{{cookiecutter.project_slug}}/AGENTS.md` (rtk optionalization)
- `{{cookiecutter.project_slug}}/.agents/` attribution note (Step 7 — a new
  `README.md` or NOTICE inside `.agents/`, nothing else in that tree)

**Out of scope**:
- CODE_OF_CONDUCT.md and issue/PR templates — deliberately skipped for now
  (GitHub UI can add them later); record in the PR description.
- Any `src/`, compose, workflow, or hook changes.
- `skills-lock.json` (plan 010 owns its reconcile).
- GitHub repo settings (description, topics, branch protection, advisories)
  — manual publishing checklist, see Maintenance notes.
- The `plans/` directory's fate — maintainer decision, see Maintenance
  notes; do NOT delete it yourself.

## Git workflow

- Branch: `advisor/021-open-source-readiness`
- Conventional commit, e.g. `docs: prepare repository for open source release`
- Do NOT push or open a PR unless the operator instructed it.

## Steps

### Step 1: Neutral cookiecutter defaults

In `cookiecutter.json`: `author_name` → `"John Doe"`, `author_email` →
`"john.doe@example.com"`, `github_username` → `"johndoe"`. Nothing else
changes. Update the root README Variables table defaults to match (Step 3
rewrites that section anyway — keep the values in sync).

**Verify**: `uvx cookiecutter . --no-input -o $BAKE` →
`grep -n "John Doe" $BAKE/my-project/pyproject.toml` → authors/maintainers
lines; `grep -n "johndoe" $BAKE/my-project/.github/dependabot.yml` →
assignee entries; baked `uv run pytest` → all pass.

### Step 2: LICENSE + metadata

1. Template root `LICENSE`: MIT text, `Copyright (c) 2026 Stefano Fusai`
   (the AUTHOR keeps copyright — de-personalizing defaults does not mean
   erasing authorship).
2. `{{cookiecutter.project_slug}}/LICENSE`: MIT text with
   `Copyright (c) 2026 {{ cookiecutter.author_name }}` (Jinja renders it —
   baked projects are owned by their generators).
3. Baked `pyproject.toml [project]`: add `license = "MIT"` (SPDX string,
   PEP 639; place after `readme`). If the pinned uv rejects the SPDX string
   form, STOP and report before falling back to the table form.

**Verify**: fresh bake → `test -f $BAKE/my-project/LICENSE`;
`grep -n 'license = "MIT"' $BAKE/my-project/pyproject.toml`;
`uv run pytest` in the bake still passes (uv parses the metadata during the
post-gen lock).

### Step 3: Rewrite the root README as the open-source front door

Re-read the LIVE root README first, then restructure. Required sections, in
order — derive all feature claims from the live repo, not from this plan:

1. **Title + one-paragraph pitch** + badges: CI workflow badge
   (`.github/workflows/ci.yaml` exists) and an MIT license badge.
2. **What You Get** — regenerate the list against the live tree
   (alphabetical). Check for and include, if present: celery beat service,
   custom user model, health/ready split, Sentry integration, email stack,
   Traefik + docker-rollout deploys, /api/v1 versioning, factories/testing
   stack (say "Schemathesis property-based contract tests" — do not name
   Hypothesis unless something imports it directly; verify with
   `rg "from hypothesis" '{{cookiecutter.project_slug}}/tests'`).
3. **Design Decisions** (NEW — this is the "specifies all choices" ask):
   one line each, stating the choice AND its rationale. Derive from the
   live repo; the known set at planning time: uv with exact pins
   (reproducible bakes); `src/` layout; django-split-settings
   components + ci/dev/prod overlays (one concern per file); Django Ninja
   (typed, OpenAPI-first); Celery + Redis with results opt-in per task;
   PostgreSQL; custom user model from day one (the famously irreversible
   Django decision); 100% coverage gate over all of `src/`; liveness
   (`/api/health`) vs readiness (`/api/ready`) split; Sentry required in
   production (boot fails without a DSN); no CORS and no throttling by
   design — add them when a real consumer needs them. Append any decisions
   landed since (versioned API, standardized deploys) per the live tree.
4. **Requirements**: Python 3.14, uv, Docker Compose ≥ 2.30 (lifecycle
   hooks).
5. **Usage** (unchanged command) + **Variables** table (Step 1 defaults;
   keep the slug constraints line, updated if plan 011 added length/char
   rules).
6. **Required Configuration** (NEW): the after-baking checklist — copy
   `.env.example`, then the production-required values (derive from the
   live `.env.example`: every uncommented empty value is required in prod —
   at planning time: `AWS_STORAGE_BUCKET_NAME`, `SENTRY_DSN`, plus
   `SECRET_KEY` regeneration and real `ALLOWED_HOSTS`/`CSRF_TRUSTED_ORIGINS`;
   include keys added by landed plans). Point at `.env.example`'s own
   documentation and the baked README's Production section for the rest.
7. **Post-Generation** (keep, verbatim intent) and **Verification** —
   fix the block so it runs top-to-bottom:

   ```shell
   uv run pytest
   uv run pre-commit run --all-files
   docker compose -f .docker/compose/dev.yaml up -d --build --wait
   curl -fsS http://localhost:8000/api/ready
   docker compose -f .docker/compose/dev.yaml down -v
   ```

8. **License** section: one line, MIT.

**Verify**: if plan 012's root pre-commit exists →
`uvx pre-commit run markdownlint --all-files` passes; otherwise visual +
the baked project's markdownlint does not apply to root files — state that
in the PR.

### Step 4: Community files (root, deliberately minimal)

1. `CONTRIBUTING.md`: how to work on the template — the dev loop
   (edit template → `uvx cookiecutter . --no-input -o /tmp/bake` →
   `uv run pytest` + `uv run pre-commit run --all-files` inside the bake),
   conventional-commit requirement (gitlint enforces in baked projects; use
   the same style here), and that CI bakes the template on every PR.
2. `SECURITY.md`: report vulnerabilities privately via GitHub Security
   Advisories ("Report a vulnerability" on the repo's Security tab); no
   personal email.

Keep each under ~40 lines; match the root README's plain tone.

### Step 5: Baked README truthfulness (absorbed from plan 014)

In `{{cookiecutter.project_slug}}/README.md` (re-read it first — many plans
have edited it): apply the same Verification-block fix (`up -d --build
--wait`), ensure the Quickstart names Docker Compose ≥ 2.30, remove any
unqualified Hypothesis claim, and add a one-line License section (MIT, see
LICENSE). Reconcile — don't duplicate — sections other plans added.

### Step 6: Make rtk optional in baked AGENTS.md (absorbed from plan 014)

1. Replace "Always prefix shell commands with `rtk`." with: "If the `rtk`
   CLI is available, prefix shell commands with `rtk` (token-optimizing
   proxy); otherwise run commands directly."
2. Strip the `rtk ` prefix from every command in the Testing section (and
   anywhere else: `grep -n "rtk uv" '{{cookiecutter.project_slug}}/AGENTS.md'`),
   adding one line after the verification list: "Prefix these with `rtk`
   when it is available."

**Verify**: `grep -cn "rtk uv" '{{cookiecutter.project_slug}}/AGENTS.md'`
→ 0; no remaining command line *starts with* `rtk `.

### Step 7: Vendored-content redistribution check

For each vendored skill, find the upstream license (sources are recorded in
`{{cookiecutter.project_slug}}/skills-lock.json`): `anthropics/skills`
(mcp-builder — LICENSE.txt already vendored), `vintasoftware/django-ai-plugins`
(django-expert, django-celery-expert), `planetscale/database-skills`
(postgres). Check each upstream repo's LICENSE on GitHub.

- If ALL permit redistribution (MIT/Apache-2.0/BSD/CC): create
  `{{cookiecutter.project_slug}}/.agents/README.md` crediting each skill
  with its upstream repo and license name, one line each.
- If ANY upstream has NO license or a non-redistributable one: **STOP and
  report which** — the maintainer must remove that skill or obtain
  permission before publishing; do not decide for them.

### Step 8: Full verification loop

**Verify**:
- Fresh default bake → `uv run pytest` → all pass, 100%;
  `git add -A && uv run pre-commit run --all-files` → all pass.
- Identity sweep (commands table) → only the Usage URL and root LICENSE
  copyright remain.
- `grep -rn "Stefano\|stefanofusai" $BAKE/my-project/` → no matches (baked
  projects are fully neutral).

## Test plan

No pytest changes. Gates: the CI-covered default bake (Step 1), the
identity sweeps (Step 8), the metadata parse via post-gen `uv lock`
(Step 2), and markdownlint where available.

## Done criteria

- [ ] `cookiecutter.json` defaults are John Doe / john.doe@example.com / johndoe; root README table matches
- [ ] Default bake: pyproject authors = John Doe; dependabot assignees = johndoe; suite passes at 100%
- [ ] LICENSE at root (maintainer copyright) and in the baked tree (rendered author); `license = "MIT"` in baked pyproject
- [ ] Root README has Design Decisions + Required Configuration sections and a runnable Verification block
- [ ] CONTRIBUTING.md and SECURITY.md exist at root
- [ ] No baked-AGENTS.md command starts with `rtk `
- [ ] `.agents/README.md` credits every vendored skill with a verified redistributable license (or the Step 7 STOP fired)
- [ ] Identity sweep: only Usage URL + root LICENSE copyright mention the maintainer
- [ ] No files outside the in-scope list modified (`git status`)
- [ ] `plans/README.md`: this row updated AND 014 marked SUPERSEDED by 021

## STOP conditions

- Step 7 finds an unlicensed/non-redistributable vendored skill (see
  inline instruction).
- Any evidence the maintainer wants a license other than MIT (existing
  license text anywhere, a note in plans/README.md) — stop and ask.
- uv rejects the PEP 639 `license = "MIT"` string on the pinned version.
- The default bake fails after Step 1 — a hook or file unexpectedly depends
  on the old default values; report which.
- Plan 014 turns out to be DONE or IN PROGRESS in the index — reconcile
  with its executor's changes instead of re-applying; report the overlap.

## Maintenance notes

**Manual publishing checklist for the maintainer (not executor actions):**

- Decide the fate of `plans/` before the repo goes public: it is an
  internal audit trail and several TODO plans describe not-yet-hardened
  areas (e.g. docs exposure). Recommendation: finish or prune them, or
  exclude the directory from the published history.
- Set the GitHub repo description + topics (cookiecutter, django,
  django-ninja, celery, uv, template), enable Dependabot alerts and secret
  scanning, protect `main`, and enable the Security tab's private
  vulnerability reporting (SECURITY.md points there).
- After renaming/moving the repo, update the `gh:stefanofusai/...` Usage
  URL.

**Ongoing:** every feature plan that lands after this one must update the
root README's What You Get / Design Decisions / Required Configuration
sections — the index should note this for any future plan. The John Doe
defaults are now part of the public contract; CI bakes them on every push.
