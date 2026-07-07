# Plan 017: Scaffolding polish — `.editorconfig`, a generated `SECURITY.md`, an accurate README architecture map, and a clearer `traefik_tls` prompt

> **Executor instructions**: This plan bundles four small, independent
> improvements. Do them in order; each has its own verification. If anything in
> "STOP conditions" occurs, stop and report. When done, update this plan's status
> row in `plans/README.md` — unless a reviewer dispatched you and told you they
> maintain the index.
>
> **Drift check (run first)**:
> `git diff --stat ae42991..HEAD -- "{{cookiecutter.project_slug}}/README.md" cookiecutter.json "{{cookiecutter.project_slug}}/.pre-commit-config.yaml"`
> If any changed since this plan was written, compare "Current state" against the
> live files before proceeding; on a mismatch, STOP.

## Status

- **Priority**: P3
- **Effort**: S
- **Risk**: LOW
- **Depends on**: none
- **Category**: dx
- **Planned at**: commit `ae42991`, 2026-07-07

## Repository context (read before anything else)

This is a **Cookiecutter template**. Source is under `{{cookiecutter.project_slug}}/`
— **quote it in shell**. Files there are **rendered** (Jinja OK) except
`.github/workflows/*` and `.agents/*`.

- The baked project's formatting is enforced by pre-commit hooks
  (`ruff-format`, `yamlfmt`, `end-of-file-fixer`) — but only at commit time, not
  in-editor. `.editorconfig` gives editors the same rules up front.
- Verification means baking: `uvx cookiecutter . --no-input -o /tmp/bake [key=value …]`.
- The baked pre-commit stack includes `markdownlint`, `end-of-file-fixer`,
  `mixed-line-ending`, and `trailing-whitespace` — any new file must satisfy them.

## Why this matters

Four low-risk gaps, none critical, each a small correctness/polish win:

1. **No `.editorconfig`** anywhere. Contributors on editors without the ruff /
   yamlfmt plugins get wrong indentation and line endings until pre-commit
   rewrites them — a churn-and-fix loop the playbook calls out as baseline DX.
2. **Generated projects ship no `SECURITY.md`.** The template repo has one, but
   `find "{{cookiecutter.project_slug}}" -name SECURITY.md` is empty, so a
   downstream project has no documented vulnerability-disclosure channel.
3. **The generated README architecture map is wrong for the richest bake.** It
   lists `src/apps/core/` and `src/apps/api/` but never `src/apps/notes/` even
   when `use_example_api=yes`, and it describes `.github/` as "CI, pre-commit,
   dependency audit, Docker build workflows" while the project ships six
   workflows (also `deploy-check` and `migrations-check`).
4. **`traefik_tls` prompts unconditionally**, even for `use_traefik=no` bakes
   where it is a silent no-op — bake-time confusion. Cookiecutter has no native
   conditional prompts, so the honest fix is a clearer prompt string.

## Current state

### `.editorconfig` — absent

`ls "{{cookiecutter.project_slug}}/.editorconfig"` → no such file. Formatting
rules to mirror: Python 4-space indent (ruff default), YAML 2-space, LF line
endings, final newline, trim trailing whitespace (from the pre-commit hooks and
`AGENTS.md` style rules).

### `SECURITY.md` — absent in the generated project

`ls "{{cookiecutter.project_slug}}/SECURITY.md"` → no such file. The **template
repo's** root `SECURITY.md` exists and is a style reference — read it, but the
generated one should use the project's own contact
(`{{ cookiecutter.author_email }}`) and name (`{{ cookiecutter.project_name }}`).

### `{{cookiecutter.project_slug}}/README.md` — architecture block (today)

```text
## Architecture

​```text
{% if cookiecutter.use_celery != "none" -%}
src/config/          Django settings, URLs, Celery app, ASGI entrypoint
{%- else %}
src/config/          Django settings, URLs, ASGI entrypoint
{%- endif %}
src/apps/core/       shared abstract model bases
src/apps/api/        Django Ninja API, schemas, pagination, request metadata
tests/               unit and integration tests
.docker/             Dockerfile, Compose files, entrypoint scripts
.github/            CI, pre-commit, dependency audit, Docker build workflows
​```
```

(Note the existing `.github/` line has a single space before `CI` — verify and
keep alignment consistent with neighbors when you edit it.)

### `cookiecutter.json` — `traefik_tls` prompt (today)

```json
"traefik_tls": {
    "__prompt__": "Traefik TLS certificate source",
    "letsencrypt": "Use Traefik ACME with Let's Encrypt",
    "external": "Use operator-provided PEM certificate files"
},
```

**Conventions (from `AGENTS.md`)**: extended YAML block style; markdown lists
alphabetized; only comment to state constraints code can't show; match existing
`cookiecutter.json` indentation/quoting exactly.

## Commands you will need

| Purpose | Command | Expected |
|---------|---------|----------|
| Bake default | `uvx cookiecutter . --no-input -o /tmp/bake` | project |
| Bake example-api | `uvx cookiecutter . --no-input -o /tmp/bake-ex use_example_api=yes` | notes app present |
| Bake minimal | `uvx cookiecutter . --no-input -o /tmp/bake-min use_celery=none email_provider=none use_sentry=no use_s3_media=no use_traefik=no` | stripped project |
| JSON valid | `python -c "import json; json.load(open('cookiecutter.json'))"` | exit 0 |
| Baked pre-commit | `cd /tmp/bake*/my-project && git add -A && uv run pre-commit run --all-files` | exit 0 |
| Root pre-commit | (repo root) `uvx pre-commit run --all-files` | exit 0 |

## Scope

**In scope** (create unless noted):
- `{{cookiecutter.project_slug}}/.editorconfig` (create).
- `{{cookiecutter.project_slug}}/SECURITY.md` (create — rendered, uses cookiecutter vars).
- `{{cookiecutter.project_slug}}/README.md` (edit — architecture block).
- `cookiecutter.json` (edit — `traefik_tls` `__prompt__` text only).

**Out of scope**:
- The template repo's own root `SECURITY.md` / `.editorconfig` — this plan is
  about the *generated* project. (Adding a root `.editorconfig` is a fine
  separate follow-up; note it, don't do it here.)
- Any behavioral/knob change to `traefik_tls` (cookiecutter can't do conditional
  prompts; this is a wording fix only).
- `hooks/post_gen_project.py` — `.editorconfig` and `SECURITY.md` ship for all
  knobs, so no deletion rule is needed.

## Git workflow

- Work directly on `main`. Do NOT branch/commit/push/PR unless told. If asked to
  commit: Conventional Commits, e.g. `chore: add editorconfig, generated SECURITY.md, and fix README architecture map`.

## Steps

### Step 1: Add `.editorconfig`

Create `{{cookiecutter.project_slug}}/.editorconfig` mirroring the enforced
formatting (no Jinja needed):

```ini
root = true

[*]
charset = utf-8
end_of_line = lf
insert_final_newline = true
trim_trailing_whitespace = true
indent_style = space
indent_size = 4

[*.{yaml,yml,json,md}]
indent_size = 2
```

(No markdown `trim_trailing_whitespace = false` override: the baked
`trailing-whitespace` pre-commit hook strips trailing spaces in `.md` files too
— the repo does not use two-space hard line breaks — so the editorconfig must
agree with the hook, or editors and commits will fight over `.md` files.)

**Verify**: default bake contains `.editorconfig`; baked + root pre-commit exit
0 (the file must satisfy `end-of-file-fixer`/`trailing-whitespace`).

### Step 2: Add a generated `SECURITY.md`

Create `{{cookiecutter.project_slug}}/SECURITY.md`, modeled on the template
repo's root `SECURITY.md` but using the project's identity. Keep it short and
markdownlint-clean (MD013 is disabled; other rules apply). Use
`{{ cookiecutter.author_email }}` as the disclosure contact and
`{{ cookiecutter.project_name }}` in the heading. Do not invent a support policy
the maintainer hasn't stated — a minimal "report privately to <email>, please do
not open public issues for vulnerabilities" is enough.

**Verify**: default bake contains `SECURITY.md`; it renders the real
author email (not `{{ ... }}`); `uvx pre-commit run markdownlint --all-files`
(root) and baked pre-commit exit 0.

### Step 3: Fix the README architecture map

In `{{cookiecutter.project_slug}}/README.md`, inside the architecture code block:

- Add a `src/apps/notes/` line guarded on the example API knob, e.g.:
  ```text
  {%- if cookiecutter.use_example_api == "yes" %}
  src/apps/notes/      example notes resource (model, router, schemas, tests)
  {%- endif %}
  ```
  Place it after the `src/apps/api/` line, matching the column alignment of the
  surrounding entries.
- Correct the `.github/` description to enumerate the real shipped set. The six
  workflows are exactly: `dependency-audit.yaml`, `deploy-check.yaml`,
  `docker-build.yaml`, `migrations-check.yaml`, `pre-commit.yaml`,
  `tests.yaml` (re-verify by listing
  `{{cookiecutter.project_slug}}/.github/workflows/` — plan 014/015 may have
  added one). Suggested line: "dependency audit, deploy check, Docker build,
  migration check, pre-commit, and test workflows" — note there is no workflow
  named "CI", so do not write "CI" as if it were one. Fix the stray
  leading-space alignment on that line while you are there (its description
  column starts one space earlier than every other entry).

Keep the code block valid (it is inside a fenced ```text block; Jinja whitespace
control must not break the fence).

**Verify**:
```
grep -c "src/apps/notes/" /tmp/bake-ex/my-project/README.md   # expect 1 (example-api bake)
grep -c "src/apps/notes/" /tmp/bake/my-project/README.md      # expect 0 (default bake has no notes)
```
(Default bake has `use_example_api=no`, so the notes line must be absent.) Both
bakes: `uvx pre-commit run markdownlint --all-files` passes.

### Step 4: Clarify the `traefik_tls` prompt

In `cookiecutter.json`, reword the `traefik_tls` `__prompt__` to state it only
applies when Traefik is enabled:

```json
"traefik_tls": {
    "__prompt__": "Traefik TLS certificate source (ignored when use_traefik=no)",
    "letsencrypt": "Use Traefik ACME with Let's Encrypt",
    "external": "Use operator-provided PEM certificate files"
},
```

Change only the `__prompt__` string; leave the choice values and everything else
untouched.

**Verify**: `python -c "import json; json.load(open('cookiecutter.json'))"` exits
0; a bake still works (`uvx cookiecutter . --no-input -o /tmp/bake use_traefik=no`
succeeds and produces no Traefik artifacts).

### Step 5: Full regression across knob states

Bake default, `use_example_api=yes`, and minimal; for each run baked pre-commit;
then root pre-commit.

**Verify**: all bakes' `git add -A && uv run pre-commit run --all-files` exit 0;
root `uvx pre-commit run --all-files` exits 0.

## Test plan

- No pytest — these are scaffolding/docs files with no Python surface;
  `AGENTS.md` forbids config-only assertion tests. Verification is the bake +
  pre-commit matrix (Steps 1-5) and the README grep assertions (Step 3).

## Done criteria

ALL must hold:

- [ ] Default bake contains `.editorconfig` and `SECURITY.md`; `SECURITY.md` shows the real author email.
- [ ] `use_example_api=yes` bake README shows a `src/apps/notes/` line; default bake README does not.
- [ ] Generated README `.github/` line enumerates the actual shipped workflows.
- [ ] `cookiecutter.json` `traefik_tls` prompt notes it is ignored when `use_traefik=no`; `json.load` succeeds.
- [ ] Baked pre-commit exits 0 on default, example-api, and minimal bakes; root pre-commit exits 0.
- [ ] No out-of-scope files modified (`git status`); no `hooks/` change.
- [ ] `plans/README.md` status row updated.

## STOP conditions

Stop and report (do not improvise) if:

- Any "Current state" excerpt no longer matches the live file.
- `uv`/`uvx` is unavailable or a bake fails to produce `uv.lock` — you cannot
  verify without baking.
- markdownlint rejects the new `SECURITY.md` / README edits in a way that needs a
  config change (report; do not disable rules globally).
- The Jinja-guarded notes line breaks the fenced code block rendering (report the
  whitespace-control issue).

## Maintenance notes

- **Deferred**: a root-repo `.editorconfig` for template contributors (separate
  from the generated one).
- If more apps are added to the template, extend the README architecture map (and
  consider generating it, though that is heavier than warranted today).
- A reviewer should confirm the notes line is knob-gated (absent in
  `use_example_api=no`) and `SECURITY.md` uses the project's own contact, not a
  placeholder.
