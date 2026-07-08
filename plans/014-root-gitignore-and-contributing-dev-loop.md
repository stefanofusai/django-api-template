# Plan 014: Complete the root .gitignore and fix CONTRIBUTING's dev loop

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving to the
> next step. If anything in the "STOP conditions" section occurs, stop and
> report — do not improvise. When done, update the status row for this plan
> in `plans/README.md` — unless a reviewer dispatched you and told you they
> maintain the index.
>
> **Drift check (run first)**:
> `git diff --stat 75c4dce..HEAD -- .gitignore CONTRIBUTING.md`
> If either file changed since this plan was written, compare the "Current
> state" excerpts against the live code before proceeding; on a mismatch,
> treat it as a STOP condition.

## Status

- **Priority**: P3
- **Effort**: S
- **Risk**: LOW
- **Depends on**: none
- **Category**: dx / docs
- **Planned at**: commit `75c4dce`, 2026-07-08

## Why this matters

Two small onboarding hazards for anyone who is not the maintainer on the
maintainer's machine. First, the root `.gitignore` is two lines; the
template repo's own toolchain produces `.ruff_cache/`, `.pytest_cache/`,
`.hypothesis/`, and IDE dirs that stay out of `git status` today only
because of the maintainer's personal global gitignore — a fresh contributor
clone sees untracked noise and risks committing it. Second,
`CONTRIBUTING.md`'s documented development loop runs `uv run pytest` in a
fresh bake without starting Postgres; the suite connects to a real Postgres
on `localhost:5432`, so the documented loop fails on a clean machine.

## Current state

- `.gitignore` (root, entire file):

```gitignore
__pycache__/
.venv/
```

Facts verified during the audit: `.idea/` is ignored on the maintainer's
machine only via `~/.gitignore.global`; `.ruff_cache/`, `.pytest_cache/`,
and `.hypothesis/` match no committed rule (they hide via cache-internal
self-ignore files, which `git status` honors but which is incidental, and
`.hypothesis` currently sits visible at the repo root). Contrast the
generated project's comprehensive
`{{cookiecutter.project_slug}}/.gitignore`.

- `CONTRIBUTING.md:7-16` (the broken loop):

```markdown
## Development Loop

Edit the template, then bake a project and run checks inside the bake:

```shell
uvx cookiecutter . --no-input -o /tmp/bake
cd /tmp/bake/my-project
uv run pytest
uv run pre-commit run --all-files
```
```

- The generated project's own README documents the working sequence
  (`{{cookiecutter.project_slug}}/README.md:597-604`, "Testing"):

```shell
docker compose -f .docker/compose/dev.yaml --env-file=.env up -d --wait postgres
uv run pytest
```

and its "Required Configuration" section starts with
`cp .env.example .env` (the compose file needs `--env-file=.env`).
"Tests connect to `localhost:5432` by default and honor a `DATABASE_URL`
environment override" (`README.md:606-607`).

## Commands you will need

| Purpose | Command | Expected on success |
|---------|---------|---------------------|
| Ignore check | `git check-ignore -v .ruff_cache .pytest_cache .hypothesis .idea` | every path matched by the ROOT `.gitignore` (not the personal global file) |
| Status check | `git status --short` | no untracked cache/IDE dirs listed |
| Docs lint | `uvx pre-commit run markdownlint --all-files` | exit 0 |
| Rehearse the documented loop | run the CONTRIBUTING commands verbatim in a fresh shell | pytest passes |

## Scope

**In scope**:

- `.gitignore` (root)
- `CONTRIBUTING.md`

**Out of scope** (do NOT touch):

- `{{cookiecutter.project_slug}}/.gitignore` — already comprehensive.
- The generated README's Testing/Verification sections — already correct;
  they are the SOURCE this plan copies from.
- Adding an `.editorconfig` — considered and rejected this cycle (hooks
  already enforce whitespace/EOL; see plans/README.md rejected list).

## Git workflow

- Conventional commits; this is naturally two commits:
  `chore: cover toolchain artifacts in the root .gitignore` and
  `docs: start postgres in the CONTRIBUTING dev loop`.
- Do NOT push unless instructed.

## Steps

### Step 1: Extend the root `.gitignore`

Replace the file content with (keep it minimal and sorted, matching the
two-line file's plainness — this is the template REPO's ignore file, not the
generated project's):

```gitignore
__pycache__/
.coverage
.hypothesis/
.idea/
.pytest_cache/
.ruff_cache/
.venv/
.vscode/
htmlcov/
```

(Sorted with `sort`'s default C-locale ordering: dotfiles after
`__pycache__/`. Match `end-of-file-fixer`: single trailing newline.)

**Verify**:
`git check-ignore -v .ruff_cache .pytest_cache .hypothesis .idea` → four
lines, each attributing the match to `.gitignore` (the repo one, not a home
path); `git status --short` no longer lists any of these dirs (only
`plans/` and in-progress work should remain).

### Step 2: Fix the CONTRIBUTING dev loop

In `CONTRIBUTING.md`, replace the Development Loop code block with:

```shell
uvx cookiecutter . --no-input -o /tmp/bake
cd /tmp/bake/my-project
cp .env.example .env
docker compose -f .docker/compose/dev.yaml --env-file=.env up -d --wait postgres
uv run pytest
uv run pre-commit run --all-files
```

And immediately after the block, add one sentence: "Tests connect to the
dev-compose Postgres on `localhost:5432` and honor a `DATABASE_URL`
override." (Mirrors the generated README's wording so the two documents
agree.)

**Verify**: `uvx pre-commit run markdownlint --all-files` → exit 0.

### Step 3: Rehearse the documented loop verbatim

Run exactly the six commands from step 2's block in a fresh shell (use
`/tmp/bake-014` instead of `/tmp/bake` if `/tmp/bake` already exists).
Afterwards tear down:
`docker compose -f .docker/compose/dev.yaml --env-file=.env down -v`.

**Verify**: `uv run pytest` passes (100% coverage) — the documented loop
now works on a machine that only has Docker, uv, and Python. If Docker is
unavailable in your environment, report that step 3 was skipped and why.

## Test plan

No unit tests — docs and ignore rules. The executable test is step 3: the
documented loop must pass verbatim.

## Done criteria

- [ ] `git check-ignore` attributes all four dirs to the root `.gitignore`
- [ ] CONTRIBUTING's loop contains the `cp .env.example .env` and
  `docker compose ... up -d --wait postgres` lines before `uv run pytest`
- [ ] markdownlint passes
- [ ] Step 3 rehearsal passed (or Docker unavailability reported)
- [ ] `git status` shows only the two in-scope files modified
- [ ] `plans/README.md` status row updated

## STOP conditions

Stop and report back if:

- The generated project's dev compose file no longer has a `postgres`
  service or the `--env-file=.env` requirement (drift — re-read
  `{{cookiecutter.project_slug}}/README.md` Testing section and mirror
  whatever it now says).
- Step 3's pytest fails for reasons unrelated to the DB connection (that
  would be a template regression this plan must not paper over).

## Maintenance notes

- If the template repo ever gains tooling that writes new cache dirs (mypy,
  ty, etc.), extend the root `.gitignore` — the generated project's
  comprehensive `.gitignore` is the reference list.
- Plan 004 (consistency sweep) also edits root-adjacent docs; if both are
  in flight, land in numeric order to avoid trivial conflicts.
  CONTRIBUTING.md itself is not in plan 004's scope, so no real dependency.
