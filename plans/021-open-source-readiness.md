# Plan 021: Open-source readiness — de-personalized defaults, complete README, LICENSE, community files (supersedes plan 014)

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving to the
> next step. If anything in the "STOP conditions" section occurs, stop and
> report — do not improvise. When done, update the status row for this plan
> in `plans/README.md` — unless a reviewer dispatched you and told you they
> maintain the index.
>
> **Drift check (run first)**: `git diff --stat 28d30e8..HEAD -- README.md AGENTS.md cookiecutter.json '{{cookiecutter.project_slug}}/README.md' '{{cookiecutter.project_slug}}/AGENTS.md' '{{cookiecutter.project_slug}}/pyproject.toml'`
> (root `AGENTS.md` did not exist at `28d30e8` — it will show as new; that
> is expected.)
> This plan runs LAST and documents the LIVE state — READMEs are expected to
> have drifted via other plans; re-read every target file fully before
> editing. In `cookiecutter.json`, plan 022's six knob entries
> (`use_celery`, `email_provider`, `use_sentry`, `use_s3_media`,
> `use_traefik`, `traefik_tls`) are EXPECTED drift versus the excerpt
> below; any other mismatch is a STOP.

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
have no usage grant), both AGENTS.md files (root and baked) hard-require
`rtk` (a personal CLI wrapper that fails with "command not found" for
everyone else), the
root README documents neither the template's opinionated choices nor the
configuration a new user must supply, and the vendored `.agents/` skills
are redistributed without verified upstream licenses. This plan makes the
repo publishable: neutral defaults, a README that states every choice and
required configuration, LICENSE + minimal community files, and a
redistribution check. It also adds a `domain_name` variable (folded in on
2026-07-05) so baked projects get prod-correct
`ALLOWED_HOSTS`/`CSRF_TRUSTED_ORIGINS`/`TRAEFIK_DOMAIN` values instead of
`example.com` placeholders.

## Important context: this is a cookiecutter template

- Project code lives under the literal `{{cookiecutter.project_slug}}/` dir —
  quote it in shell. Preserve every `{{ cookiecutter.* }}` placeholder.
- Verification = bake (`uvx cookiecutter . --no-input -o <dir>`) + baked
  suite (`uv run pytest`, 100%) + baked pre-commit. Root-level markdown is
  linted only if the root pre-commit config (plan 012) exists — check.

## Current state

- `cookiecutter.json` (whole file at `28d30e8`; plan 022 adds six knob
  entries between `github_username` and `_copy_without_render` — expected):

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
- `{{cookiecutter.project_slug}}/.env.example` hardcodes the deployment
  domain placeholders (values as of 2026-07-05, with plan 018's changes):
  `ALLOWED_HOSTS=localhost,127.0.0.1`,
  `CSRF_TRUSTED_ORIGINS=https://example.com,https://www.example.com`, and
  `TRAEFIK_DOMAIN=example.com`. By execution time, plan 022 wraps the
  `TRAEFIK_*` lines in a `{%- if cookiecutter.use_traefik == "yes" %}`
  conditional and plan 020 may have grouped lines into commented blocks —
  in Step 1b, edit the VALUES only and leave any wrappers/blocks intact.
- `hooks/pre_gen_project.py` validates each variable that is written into
  rendered files, using rendered `tojson` constants + compiled regex +
  `sys.exit` (e.g. `GITHUB_USERNAME_PATTERN`). `domain_name` (Step 1b)
  follows the same pattern.
- No LICENSE at the root or in `{{cookiecutter.project_slug}}/`; the only
  license in-tree is the vendored
  `.agents/skills/mcp-builder/LICENSE.txt`. Baked `pyproject.toml
  [project]` has no `license` key.
- Baked `AGENTS.md:5`: "Always prefix shell commands with `rtk`." and the
  Testing section lists `rtk uv run ...` commands — `rtk` is not part of
  the template's toolchain.
- Root `AGENTS.md` (added at `b7200cf`, after this plan was written) has
  the same problem: its Command Workflow section opens with "Always prefix
  shell commands with `rtk`." and its Verification section lists
  `rtk pre-commit ...` / `rtk uv run ...` / `rtk docker compose ...` /
  `rtk curl ...` commands. Its fff-MCP bullet is fine as-is (it already
  says "when available; otherwise use `rg`") — leave that one alone.
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
- `cookiecutter.json` (three default values + the new `domain_name` entry)
- `hooks/pre_gen_project.py` (Step 1b `domain_name` validation ONLY)
- `{{cookiecutter.project_slug}}/.env.example` (Step 1b domain values ONLY)
- `.github/workflows/ci.yaml` (root — one new `bake-invalid` matrix case
  ONLY)
- `README.md` (template root — restructure per Step 3)
- `LICENSE` (create, template root)
- `CONTRIBUTING.md` (create, template root)
- `SECURITY.md` (create, template root)
- `{{cookiecutter.project_slug}}/LICENSE` (create)
- `{{cookiecutter.project_slug}}/pyproject.toml` (`license` key only)
- `{{cookiecutter.project_slug}}/README.md` (truthfulness fixes, Step 5)
- `{{cookiecutter.project_slug}}/AGENTS.md` (rtk optionalization)
- `AGENTS.md` (root — rtk optionalization ONLY, Step 6; do not touch its
  other guidance)
- `{{cookiecutter.project_slug}}/.agents/` attribution note (Step 7 — a new
  `README.md` or NOTICE inside `.agents/`, nothing else in that tree)

**Out of scope**:
- CODE_OF_CONDUCT.md and issue/PR templates — deliberately skipped for now
  (GitHub UI can add them later); record in the PR description.
- Any `src/`, compose, workflow, or hook changes beyond the three Step 1b
  carve-outs listed in scope.
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

### Step 1b: Add the `domain_name` variable (folded in 2026-07-05)

Maintainer decision: a plain `domain_name` variable (default
`"example.com"`) pre-fills the deployment-domain placeholders, so a
project baked with its real domain gets a prod-correct `.env.example` out
of the box. In particular it closes a real deploy footgun: Traefik routes
`` Host(`TRAEFIK_DOMAIN`) `` to the api container, but Django rejects that
host with a 400 until the operator remembers to extend `ALLOWED_HOSTS`.
This is a value variable, NOT a feature knob — no conditionals, no file
deletions.

1. `cookiecutter.json`: add `"domain_name": "example.com",` after
   `"github_username"` and before plan 022's knob entries.
2. `hooks/pre_gen_project.py`: add validation in the file's existing style
   (constants alphabetized with the others):

   ```python
   DOMAIN_NAME = {{ cookiecutter.domain_name | tojson }}
   DOMAIN_NAME_PATTERN = re.compile(
       r"^[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?(\.[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?)+$"
   )
   ```

   and in `main()`, alongside the other checks:

   ```python
       if not DOMAIN_NAME_PATTERN.fullmatch(DOMAIN_NAME):
           sys.exit(
               "domain_name must be a bare lowercase hostname such as "
               "api.example.com (no scheme, port, path, or trailing dot)."
           )
   ```

3. `{{cookiecutter.project_slug}}/.env.example` — replace the literal
   domain VALUES; leave plan 022's `{%- if %}` wrappers and any plan-020
   block structure exactly where they are:
   - `ALLOWED_HOSTS=localhost,127.0.0.1` →
     `ALLOWED_HOSTS=localhost,127.0.0.1,{{ cookiecutter.domain_name }}`
     (this is the ONE line whose default rendering changes — it gains
     `,example.com`, which is harmless in dev and CI: the pytest env sets
     its own `ALLOWED_HOSTS`, and the compose smoke probes localhost).
   - `CSRF_TRUSTED_ORIGINS=https://example.com,https://www.example.com` →
     `CSRF_TRUSTED_ORIGINS=https://{{ cookiecutter.domain_name }},https://www.{{ cookiecutter.domain_name }}`
   - `TRAEFIK_DOMAIN=example.com` →
     `TRAEFIK_DOMAIN={{ cookiecutter.domain_name }}` (inside 022's
     `use_traefik` conditional).
4. Root `.github/workflows/ci.yaml`, `bake-invalid` job matrix: add
   `- case: bad-domain` with `extra-args: domain_name=no-dot`.
5. Baked `{{cookiecutter.project_slug}}/README.md`: reconcile in Step 5 —
   where the Production section tells the operator to add their domain to
   `ALLOWED_HOSTS`/`CSRF_TRUSTED_ORIGINS`/`TRAEFIK_DOMAIN` manually,
   reword to say these are pre-filled from `domain_name` at bake time
   (keep the "keep `127.0.0.1` for the container healthcheck" guidance).

**Verify**:
- Default bake: `grep -n "^ALLOWED_HOSTS=" $BAKE/my-project/.env.example`
  → `localhost,127.0.0.1,example.com`; `TRAEFIK_DOMAIN=example.com` and
  the `CSRF_TRUSTED_ORIGINS` line render exactly as today.
- `uvx cookiecutter . --no-input -o /tmp/dn domain_name=api.acme.dev` →
  `grep -c "api.acme.dev" /tmp/dn/my-project/.env.example` → 4 occurrences
  (1 ALLOWED_HOSTS + 2 CSRF + 1 TRAEFIK_DOMAIN); baked pytest passes.
- `uvx cookiecutter . --no-input -o /tmp/dnbad domain_name=no-dot` →
  non-zero exit, message names `domain_name`, and no project directory is
  created.
- Root `uvx pre-commit run --all-files` → exit 0 (actionlint on ci.yaml).

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
   include the `domain_name` row — default `example.com`, "deployment
   domain pre-filled into ALLOWED_HOSTS, CSRF_TRUSTED_ORIGINS, and
   TRAEFIK_DOMAIN" — and keep plan 022's six knob rows; keep the slug
   constraints line, updated if plan 011 added length/char rules).
6. **Required Configuration** (NEW): the after-baking checklist — copy
   `.env.example`, then the production-required values (derive from the
   live `.env.example`: every uncommented empty value is required in prod —
   at planning time: `AWS_STORAGE_BUCKET_NAME`, `SENTRY_DSN`, plus
   `SECRET_KEY` regeneration; note that
   `ALLOWED_HOSTS`/`CSRF_TRUSTED_ORIGINS`/`TRAEFIK_DOMAIN` are pre-filled
   from `domain_name` when the project is baked with its real domain
   (Step 1b); include keys added by landed plans). Point at
   `.env.example`'s own documentation and the baked README's Production
   section for the rest.
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

### Step 6: Make rtk optional in BOTH AGENTS.md files (absorbed from plan 014; root file folded in 2026-07-05)

In `{{cookiecutter.project_slug}}/AGENTS.md` (baked):

1. Replace "Always prefix shell commands with `rtk`." with: "If the `rtk`
   CLI is available, prefix shell commands with `rtk` (token-optimizing
   proxy); otherwise run commands directly."
2. Strip the `rtk ` prefix from every command in the Testing section (and
   anywhere else: `grep -n "rtk uv" '{{cookiecutter.project_slug}}/AGENTS.md'`),
   adding one line after the verification list: "Prefix these with `rtk`
   when it is available."

In the root `AGENTS.md` (same treatment, rtk lines ONLY):

3. Replace its "Always prefix shell commands with `rtk`." bullet with the
   same conditional sentence as item 1.
4. Strip the `rtk ` prefix from every command bullet in its Verification
   section (`rtk pre-commit ...`, `rtk uv run ...`,
   `rtk docker compose ...`, `rtk curl ...`), adding the same "Prefix
   these with `rtk` when it is available." line after the list. Leave the
   fff-MCP bullet and all other guidance untouched.

**Verify**: `grep -rn "rtk " AGENTS.md '{{cookiecutter.project_slug}}/AGENTS.md'`
→ the only matches are the two "If the `rtk` CLI is available..."
sentences and the two "Prefix these with `rtk` when it is available."
lines; no line in either file *starts with* `rtk ` (allowing leading
list markers/whitespace, i.e. `grep -rEn "^[-* ]*\`?rtk " ...` → 0
matches).

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
- [ ] `domain_name` exists (default `example.com`), pre_gen rejects `no-dot`, and a `domain_name=api.acme.dev` bake renders it 4 times in `.env.example`; `bake-invalid` has the `bad-domain` case
- [ ] Default bake: pyproject authors = John Doe; dependabot assignees = johndoe; suite passes at 100%
- [ ] LICENSE at root (maintainer copyright) and in the baked tree (rendered author); `license = "MIT"` in baked pyproject
- [ ] Root README has Design Decisions + Required Configuration sections and a runnable Verification block
- [ ] CONTRIBUTING.md and SECURITY.md exist at root
- [ ] No command in either AGENTS.md (root or baked) starts with `rtk `;
      both carry the "if available" conditional instead
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
- The three domain lines cannot be located in the live `.env.example`
  (drift beyond plan 020's block restructuring and plan 022's
  conditionals) — report what the file looks like instead.
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
