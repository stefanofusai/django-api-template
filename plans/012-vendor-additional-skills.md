# Plan 012: Vendor three more agent skills — `django-safe-migration`, `django-perf-review`, `django-access-review`

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving on. If
> anything in "STOP conditions" occurs, stop and report — do not improvise. When
> done, update this plan's status row in `plans/README.md` — unless a reviewer
> dispatched you and told you they maintain the index.
>
> **Drift check (run first)**:
> `git diff --stat ae42991..HEAD -- "{{cookiecutter.project_slug}}/skills-lock.json" "{{cookiecutter.project_slug}}/.agents/README.md" hooks/post_gen_project.py`
> If any changed since this plan was written, compare "Current state" against the
> live files before proceeding; on a mismatch, STOP.

## Status

- **Priority**: P2
- **Effort**: S
- **Risk**: LOW
- **Depends on**: none (prefer landing 003 first — it changes the celery-skill artifacts this plan's byte-identity check references)
- **Category**: dx
- **Planned at**: commit `ae42991`, 2026-07-07

## Repository context (read before anything else)

This is a **Cookiecutter template**. The generated project vendors agent skills
under `{{cookiecutter.project_slug}}/.agents/skills/<name>/` with a
`{{cookiecutter.project_slug}}/skills-lock.json` manifest and attribution in
`{{cookiecutter.project_slug}}/.agents/README.md`.

- The vendoring tool is **`vercel-labs/skills`** (`npx skills`). `skills add`
  fetches a skill, writes it under the skills dir, and records
  `source`/`sourceType`/`skillPath`/`computedHash` in `skills-lock.json`.
- `{{cookiecutter.project_slug}}/.agents/*` is copied **without Jinja rendering**;
  `skills-lock.json` and `.agents/README.md` contain **no Jinja** either. So
  these are plain files you edit directly in the template source — the vendored
  content is committed verbatim, not rendered.
- `.agents/` is excluded from Ty and pre-commit (`AGENTS.md`), so vendored
  content is not linted — keep it as the tool produces it.
- Verification means baking (`uvx cookiecutter . --no-input -o /tmp/bake`) and
  confirming the skill trees, lock entries, and README bullets ship correctly.

## Why this matters

The maintainer wants three additional skills vendored so agents working in
generated projects get authoritative guidance on migration safety, performance
review, and access-control review — all high-value for a Django API service:

- `django-safe-migration` — `vintasoftware/django-ai-plugins` (same source as the
  existing `django-expert` / `django-celery-expert`).
- `django-perf-review` — `getsentry/skills`.
- `django-access-review` — `getsentry/skills`.

Requested source URLs:
- `https://www.skills.sh/vintasoftware/django-ai-plugins/django-safe-migration`
- `https://www.skills.sh/getsentry/skills/django-perf-review`
- `https://www.skills.sh/getsentry/skills/django-access-review`

## Current state

`{{cookiecutter.project_slug}}/skills-lock.json` (full file today):

```json
{
  "version": 1,
  "skills": {
    "django-celery-expert": {
      "source": "vintasoftware/django-ai-plugins",
      "sourceType": "github",
      "skillPath": "plugins/django-celery-expert/skills/SKILL.md",
      "computedHash": "31eb59e33c4251087afc81387abf26502814885921b93c9c9afa06090c3495ca"
    },
    "django-expert": {
      "source": "vintasoftware/django-ai-plugins",
      "sourceType": "github",
      "skillPath": "plugins/django-expert/skills/SKILL.md",
      "computedHash": "a6b8c224017570496d688a526fcbea74025a01cc90d9afb0977bfcc1f76af306"
    },
    "postgres": {
      "source": "planetscale/database-skills",
      "sourceType": "github",
      "skillPath": "skills/postgres/SKILL.md",
      "computedHash": "2acf9fae4fcdb6c392923708b67234828f8a9f10b10dfa5d228eaab6e9108245"
    }
  }
}
```

`{{cookiecutter.project_slug}}/.agents/README.md` (full file today):

```markdown
# Vendored Agent Skills

The generated project vendors agent-skill instructions for local development.
They are copied from upstream repositories under redistributable licenses:

- `django-celery-expert`: `vintasoftware/django-ai-plugins`, MIT.
- `django-expert`: `vintasoftware/django-ai-plugins`, MIT.
- `postgres`: `planetscale/database-skills`, MIT.
```

Existing skill dirs each contain a `SKILL.md` and a `references/` folder
(`ls "{{cookiecutter.project_slug}}/.agents/skills/django-expert/"`).

**Conventions (from `AGENTS.md`)**: markdown/YAML/JSON list items alphabetized —
`skills-lock.json` keys and `.agents/README.md` bullets are alphabetical. Match
the exact 2-space JSON indentation and the README bullet format
(`` - `name`: `source`, LICENSE. ``).

## Commands you will need

| Purpose | Command | Expected |
|---------|---------|----------|
| Skills CLI help | `npx skills add --help` | shows `add` flags incl. how to target a skills dir |
| Verify current lock | `cd "{{cookiecutter.project_slug}}" && npx skills verify` (or the installed equivalent) | current three skills verify |
| Bake default | `uvx cookiecutter . --no-input -o /tmp/bake` | project with all skills |
| Bake celery-off | `uvx cookiecutter . --no-input -o /tmp/bake-nc use_celery=none` | see interaction note below |
| JSON valid | `python -c "import json; json.load(open('{{cookiecutter.project_slug}}/skills-lock.json'))"` | exit 0 |
| Baked pre-commit | `cd /tmp/bake/my-project && git add -A && uv run pre-commit run --all-files` | exit 0 (`.agents/` excluded, but `check-json` may still validate the lock — confirm it stays valid) |
| Root pre-commit | (repo root) `uvx pre-commit run --all-files` | exit 0 |

**Network + Node required**: `npx skills` fetches from GitHub. If Node/npx or
network is unavailable, that is a STOP (you cannot vendor).

## Scope

**In scope**:
- `{{cookiecutter.project_slug}}/.agents/skills/django-safe-migration/` (add).
- `{{cookiecutter.project_slug}}/.agents/skills/django-perf-review/` (add).
- `{{cookiecutter.project_slug}}/.agents/skills/django-access-review/` (add).
- `{{cookiecutter.project_slug}}/skills-lock.json` (add three entries, alphabetized).
- `{{cookiecutter.project_slug}}/.agents/README.md` (add three bullets, alphabetized, with correct licenses).

**Out of scope**:
- The Ty / pre-commit `.agents/` exclusions — leave them.
- Any code/settings change — skills are documentation for agents, not runtime.
- Hash-verification enforcement in CI — that is plan 021.
- Changing the three existing skills.

## Git workflow

- Work directly on `main`. Do NOT branch/commit/push/PR unless told. If asked to
  commit: Conventional Commits, e.g. `feat: vendor django-safe-migration, django-perf-review, and django-access-review skills`.

## Steps

### Step 1: Confirm how the existing skills were vendored

Run `npx skills add --help` and inspect an existing skill dir to learn the exact
invocation that targets `.agents/skills/` and writes `skills-lock.json` at the
`{{cookiecutter.project_slug}}` root (the tool may need a `--dir`/target flag or a
config). The goal is to reproduce byte-compatible lock entries (same
`source`/`sourceType`/`skillPath`/`computedHash` shape). Work **inside**
`{{cookiecutter.project_slug}}/` so the lock and skill trees land in the template
source, not elsewhere.

**Verify**: you can state the exact `skills add` command (with target flags) that
will place a new skill under `{{cookiecutter.project_slug}}/.agents/skills/` and
update `{{cookiecutter.project_slug}}/skills-lock.json`.

### Step 2: Vendor the three skills

From inside `{{cookiecutter.project_slug}}/`, add the skills (adjust the exact
flags per Step 1):

```
npx skills add vintasoftware/django-ai-plugins --skill django-safe-migration
npx skills add getsentry/skills --skill django-perf-review --skill django-access-review
```

The `--skill` flag shown above is an assumption — Step 1's `--help` output is
authoritative. If the CLI's actual flags/invocation differ from what Step 1
revealed in a way you cannot resolve from `--help` alone (e.g. no way to select
a single skill from a repo), **STOP and report the real CLI surface** rather
than improvising. If only the slug differs, use the slug the skills.sh URL
implies (`django-perf-review`, `django-access-review`) and let the tool resolve
`skillPath`. Confirm each produced a `.agents/skills/<name>/SKILL.md` (+ any
`references/`).

**Verify**:
```
ls "{{cookiecutter.project_slug}}/.agents/skills/django-safe-migration/SKILL.md"
ls "{{cookiecutter.project_slug}}/.agents/skills/django-perf-review/SKILL.md"
ls "{{cookiecutter.project_slug}}/.agents/skills/django-access-review/SKILL.md"
python -c "import json; d=json.load(open('{{cookiecutter.project_slug}}/skills-lock.json')); print(sorted(d['skills']))"
```
→ all three SKILL.md files exist; the printed key list is the six skills,
alphabetized. If `skills add` did not update the lock, add the entries by hand
matching the existing shape (compute the hash the same way the tool does — read
`npx skills` docs; do NOT invent a hash).

### Step 3: Confirm lock ordering and formatting

`skills-lock.json` keys should be alphabetical (existing file is). If the tool
appended the new keys out of order, reorder them to keep the file alphabetized
and 2-space-indented with a trailing newline, matching the current style.

**Verify**: `python -c "import json; d=json.load(open('{{cookiecutter.project_slug}}/skills-lock.json')); ks=list(d['skills']); print(ks==sorted(ks))"` → `True`; the file diff shows only additions (existing three entries byte-unchanged).

### Step 4: Add attribution bullets

In `{{cookiecutter.project_slug}}/.agents/README.md`, add one alphabetized bullet
per new skill with its correct license. **Verify each source repo's license**
before writing it (do not assume MIT): read the LICENSE of
`vintasoftware/django-ai-plugins` (the existing bullets say MIT — reuse for
`django-safe-migration`) and of `getsentry/skills` (check its actual license —
it may be Apache-2.0 or MIT; state whatever it actually is). Resulting list,
alphabetized:

```markdown
- `django-access-review`: `getsentry/skills`, <LICENSE>.
- `django-celery-expert`: `vintasoftware/django-ai-plugins`, MIT.
- `django-expert`: `vintasoftware/django-ai-plugins`, MIT.
- `django-perf-review`: `getsentry/skills`, <LICENSE>.
- `django-safe-migration`: `vintasoftware/django-ai-plugins`, MIT.
- `postgres`: `planetscale/database-skills`, MIT.
```

**Verify**: by inspection — the bullets are alphabetized and each names a
license you confirmed from the source repo's LICENSE file. (Do NOT rely on
markdownlint here: the root pre-commit excludes the whole
`{{cookiecutter.project_slug}}/` dir and the baked pre-commit excludes
`.agents/`, so no linter ever sees this README — a lint pass proves nothing
about it.)

### Step 5: Bake and confirm the skills ship

```
uvx cookiecutter . --no-input -o /tmp/bake
for s in django-access-review django-perf-review django-safe-migration; do
  test -f "/tmp/bake/my-project/.agents/skills/$s/SKILL.md" && echo "OK $s"
done
grep -c "django-safe-migration\|django-perf-review\|django-access-review" /tmp/bake/my-project/.agents/README.md   # expect 3
python -c "import json; print(len(json.load(open('/tmp/bake/my-project/skills-lock.json'))['skills']))"   # expect 6
cd /tmp/bake/my-project && git add -A && uv run pre-commit run --all-files
```

**Verify**: all three `OK`; README grep 3; six skills in the baked lock; baked
pre-commit exit 0; root `uvx pre-commit run --all-files` exit 0.

### Step 6: Confirm interaction with plan 003 (celery-skill pruning)

If plan 003 has landed (`use_celery=none` prunes `django-celery-expert`), bake
`use_celery=none` and confirm the **new** skills still ship (they are not
Celery-specific) and only `django-celery-expert` is removed:

```
uvx cookiecutter . --no-input -o /tmp/bake-nc use_celery=none
test -d /tmp/bake-nc/my-project/.agents/skills/django-safe-migration && echo OK
test ! -d /tmp/bake-nc/my-project/.agents/skills/django-celery-expert && echo CELERY_GONE
python -c "import json; print(sorted(json.load(open('/tmp/bake-nc/my-project/skills-lock.json'))['skills']))"
```

**Verify**: `OK`; `CELERY_GONE` (if 003 landed); the celery-off lock has 5 skills
(six minus `django-celery-expert`) and is valid JSON. If plan 003 has NOT landed
yet, all six ship regardless — note that in your report so 003's byte-identity
check accounts for the new entries.

## Test plan

- No pytest — skills are agent documentation, `.agents/` is excluded from
  linting. Verification is the bake + file-presence + JSON-validity matrix
  (Steps 2, 5, 6) and markdownlint on the README.

## Done criteria

ALL must hold:

- [ ] Three new skill trees exist under `{{cookiecutter.project_slug}}/.agents/skills/` each with a `SKILL.md`.
- [ ] `skills-lock.json` has six alphabetized entries; the original three are byte-unchanged; the file is valid JSON with the existing formatting.
- [ ] `.agents/README.md` has six alphabetized bullets, each naming a license confirmed from the source repo.
- [ ] A default bake ships all six skills; baked `git add -A && uv run pre-commit run --all-files` exits 0.
- [ ] Root `uvx pre-commit run --all-files` exits 0.
- [ ] (If plan 003 landed) `use_celery=none` bake keeps the new skills and removes only `django-celery-expert`.
- [ ] No out-of-scope files modified (`git status`).
- [ ] `plans/README.md` status row updated.

## STOP conditions

Stop and report (do not improvise) if:

- `npx`/Node or network is unavailable — you cannot vendor.
- The skills CLI's actual flags/invocation differ from Step 1's expectations in
  a way `--help` cannot resolve — report the real CLI surface; do not improvise.
- A source repo's license is not clearly redistributable — do NOT vendor it;
  report the license so the maintainer decides (the `.agents/README.md` claims
  "redistributable licenses" — that must remain true).
- `skills add` cannot target `{{cookiecutter.project_slug}}/.agents/skills/` /
  the root `skills-lock.json` the way the existing three are laid out — report the
  mismatch rather than scattering files.
- A requested skill slug does not exist in its source repo — report the exact
  available slug.

## Maintenance notes

- These three skills ship for all knobs (they are not feature-specific), unlike
  `django-celery-expert` (pruned by plan 003 when Celery is off). If any future
  vendored skill IS feature-specific, extend plan 003's pruning pattern.
- Dependabot does not track skills.sh sources today; skill freshness is manual
  (or via plan 021's verification). A reviewer should confirm the licenses are
  stated correctly and the lock's existing entries are untouched.
- If the maintainer later wants hash-drift enforcement, that is plan 021.
