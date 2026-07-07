# Plan 010: Close two CI gaps — exercise the example API under a stripped stack, and fail fast on Postgres image drift between Compose and workflow service blocks

> **Executor instructions**: This plan has two independent parts (A and B); do
> them in order but either can land alone. Run every verification command and
> confirm the expected result before moving on. If anything in "STOP conditions"
> occurs, stop and report. When done, update this plan's status row in
> `plans/README.md` — unless a reviewer dispatched you and told you they maintain
> the index.
>
> **Drift check (run first)**:
> `git diff --stat ae42991..HEAD -- .github/workflows/ci.yaml .pre-commit-config.yaml "{{cookiecutter.project_slug}}/.docker/compose/prod.yaml" "{{cookiecutter.project_slug}}/.docker/compose/dev.yaml" "{{cookiecutter.project_slug}}/.github/workflows/tests.yaml" "{{cookiecutter.project_slug}}/.github/workflows/migrations-check.yaml"`
> If any changed since this plan was written, compare "Current state" against the
> live files before proceeding; on a mismatch, STOP.

## Status

- **Priority**: P2
- **Effort**: S
- **Risk**: LOW
- **Depends on**: none (coordinates with plan 007 — both add a case to the root `ci.yaml` bake matrix; land one, then re-check the matrix)
- **Category**: tests
- **Planned at**: commit `ae42991`, 2026-07-07

## Repository context (read before anything else)

This is a **Cookiecutter template**. Source is under `{{cookiecutter.project_slug}}/`
— **quote it in shell**.

- The **repo-root** `.github/workflows/ci.yaml` is the template's *own* CI; it
  bakes many knob combinations (`bake` job matrix) and boots the stack
  (`docker-compose-smoke`). It is a normal author-time YAML file you may edit.
- The **repo-root** `.pre-commit-config.yaml` lints the template's own tracked
  files; it `exclude`s `{{cookiecutter.project_slug}}/`, `hooks/`, and `plans/`
  (line 4). A `local` hook with `pass_filenames: false` + `always_run: true`
  runs regardless of that exclude and can read any path — that is how Part B's
  drift check reaches into the excluded dirs.
- `.docker/*` inside `{{cookiecutter.project_slug}}/` is **rendered** (Jinja OK);
  `.github/workflows/*` and `.agents/*` are copied **unrendered**.
- Verification means baking (`uvx cookiecutter . --no-input -o /tmp/bake …`) and,
  for Part B, running the new hook via `uvx pre-commit run <id> --all-files`.

## Why this matters

**Part A (test coverage gap).** The example `notes` API is the template's only
real feature surface and carries its heaviest test — a Hypothesis-driven
Schemathesis contract test with `transaction=True` and real session queries. But
the only bake case that enables it (`ci.yaml` `example-api`) otherwise runs the
*full-feature* stack (celery, resend, sentry, s3, traefik). It is never baked
alongside `use_celery=none` / `email_provider=none` / `postgres=external`. A
Jinja interaction bug that only manifests when notes are enabled *and* other
features are stripped would ship undetected. Every single-knob value is covered
elsewhere; this is the one combinatorial hole worth one extra matrix cell.

**Part B (dependency drift).** `postgres:18.4` is hardcoded in five places:
`.docker/compose/{dev,prod}.yaml`, the generated `tests.yaml` and
`migrations-check.yaml` service blocks, and the root `ci.yaml` service block.
Dependabot updates the two Compose files but — as the in-file comments admit —
"does not track images inside workflow service blocks." So a security/patch bump
lands in Compose while CI keeps testing against the old Postgres (or vice-versa),
and the two silently diverge. A tiny drift check turns that latent split into a
fast pre-commit failure.

## Current state

### Part A — `.github/workflows/ci.yaml` `bake` matrix (excerpt)

```yaml
          - case: example-api
            project_name: My Project
            extra-args: use_example_api=yes
            slug: my-project
          # ...
          - case: minimal
            project_name: My Project
            extra-args: use_celery=none email_provider=none use_sentry=no use_s3_media=no use_traefik=no
            slug: my-project
```

Matrix cases are alphabetized by `case:`. The `bake` job runs baked `pytest`,
`migrations-check.sh`, and baked pre-commit for each case.

### Part B — the five Postgres pins

All read `image: postgres:18.4`:
- `{{cookiecutter.project_slug}}/.docker/compose/prod.yaml` (the `postgres` service)
- `{{cookiecutter.project_slug}}/.docker/compose/dev.yaml`
- `{{cookiecutter.project_slug}}/.github/workflows/tests.yaml:18`
- `{{cookiecutter.project_slug}}/.github/workflows/migrations-check.yaml:18`
- `.github/workflows/ci.yaml:18` (repo root)

The workflow blocks carry the comment: `# Keep this image in sync with
.docker/compose/{dev,prod}.yaml; Dependabot does not track images inside workflow
service blocks.` (There is also a `v5.3.0` Docker Compose pin + sha256 in
`ci.yaml`'s smoke job — that is a *different* artifact; do NOT fold it into this
Postgres check.)

**Conventions (from `AGENTS.md`)**: extended YAML block style; short flags before
long; alphabetize matrix cases by `case:`; Ruff `ALL` for any Python you add;
never `from __future__ import annotations`.

## Commands you will need

| Purpose | Command | Expected |
|---------|---------|----------|
| actionlint the CI | (repo root) `uvx pre-commit run actionlint check-github-workflows --all-files` | exit 0 |
| Bake the new case locally | `uvx cookiecutter . --no-input -o /tmp/bake-em use_example_api=yes use_celery=none email_provider=none use_sentry=no use_s3_media=no use_traefik=no` | project bakes |
| Baked tests | `cd /tmp/bake-em/my-project && DATABASE_URL=postgres://postgres:postgres@localhost:5432/postgres uv run pytest` | 100% cov, all pass |
| Run the drift hook | (repo root) `uvx pre-commit run postgres-image-pin --all-files` | `Passed` |
| Root pre-commit | (repo root) `uvx pre-commit run --all-files` | exit 0 |

## Scope

**In scope**:
- `.github/workflows/ci.yaml` (repo root) — Part A: add one bake-matrix case.
- `.pre-commit-config.yaml` (repo root) — Part B: add the `local` drift-check hook.
- A small script the hook runs, at `scripts/check_postgres_image.py` (repo root;
  create — `scripts/` does not exist yet, create it). Part B.

**Out of scope**:
- The generated project's own workflows/compose files — Part B does not change
  them; it only asserts they agree.
- The Docker Compose `v5.3.0` pin/sha in the smoke job (unrelated artifact).
- The `docker-compose-smoke` job matrix (Part A adds to `bake`, not smoke).
- Making the image a single templated variable — considered and rejected below;
  a drift *check* is lower-risk than threading a version through service blocks.

## Git workflow

- Work directly on `main`. Do NOT branch/commit/push/PR unless told. If asked to
  commit: Conventional Commits, e.g. `ci: bake example API under a stripped stack and guard postgres image drift`.

## Steps

### Part A

#### Step A1: Add a stripped-stack example-api bake case

In `.github/workflows/ci.yaml`, in the `bake` job's `strategy.matrix.include`,
add a case that enables the example API on top of the `minimal` knob set. Keep
the list alphabetized by `case:` — `example-minimal` sorts between `example-api`
and `external-backing`:

```yaml
          - case: example-minimal
            project_name: My Project
            extra-args: use_example_api=yes use_celery=none email_provider=none use_sentry=no use_s3_media=no use_traefik=no
            slug: my-project
```

Do NOT add it to `docker-compose-smoke`.

**Verify**:
```
uvx pre-commit run actionlint check-github-workflows --all-files   # exit 0
uvx cookiecutter . --no-input -o /tmp/bake-em use_example_api=yes use_celery=none email_provider=none use_sentry=no use_s3_media=no use_traefik=no
cd /tmp/bake-em/my-project && DATABASE_URL=postgres://postgres:postgres@localhost:5432/postgres uv run pytest
```
→ actionlint clean; the stripped+notes bake passes at 100% coverage. If the baked
suite fails on this combination, you have found the exact bug this case exists to
catch — STOP and report it (do not "fix" the test to make it pass).

### Part B

#### Step B1: Write the drift-check script

Create `scripts/check_postgres_image.py` (repo root). It extracts the
`postgres:` image tag from the canonical source
(`{{cookiecutter.project_slug}}/.docker/compose/prod.yaml`) and asserts every
other tracked `postgres:<tag>` reference matches, printing a clear diff and
exiting non-zero on mismatch. Keep it dependency-free (stdlib `re`/`pathlib`),
Ruff-`ALL`-clean, no `from __future__ import annotations`. Target shape:

```python
import re
import sys
from pathlib import Path

CANONICAL = Path("{{cookiecutter.project_slug}}/.docker/compose/prod.yaml")
FILES = [
    Path("{{cookiecutter.project_slug}}/.docker/compose/dev.yaml"),
    Path("{{cookiecutter.project_slug}}/.github/workflows/tests.yaml"),
    Path("{{cookiecutter.project_slug}}/.github/workflows/migrations-check.yaml"),
    Path(".github/workflows/ci.yaml"),
]
PATTERN = re.compile(r"\bpostgres:(\d+\.\d+(?:\.\d+)?)\b")


def _tags(path: Path) -> set[str]:
    return set(PATTERN.findall(path.read_text()))


def main() -> int:
    expected = _tags(CANONICAL)
    if len(expected) != 1:
        print(f"expected exactly one postgres tag in {CANONICAL}, found {expected}")
        return 1

    mismatches = [
        (path, tags)
        for path in FILES
        for tags in [_tags(path)]
        if tags != expected
    ]
    if mismatches:
        print(f"postgres image drift: canonical {expected} in {CANONICAL}")
        for path, tags in mismatches:
            print(f"  {path}: {tags or 'NO postgres:<major.minor> tag found'}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
```

Note the literal path `{{cookiecutter.project_slug}}` — this script lives in the
**template repo**, is never rendered, and reads the template source directory by
its literal name. Confirm the paths resolve from the repo root.

Design note: the comparison is `tags != expected` (NOT `tags and tags != ...`),
so a listed file whose pin *disappears* (or moves to a form the regex can't see,
e.g. a major-only `postgres:18` or a `@sha256:` digest) fails loudly instead of
passing silently. Every file in `FILES` is there because it is known to pin
postgres; if that ever legitimately stops being true, the file is removed from
`FILES` consciously.

**Verify**: `python scripts/check_postgres_image.py; echo $?` → prints nothing,
exits `0` (all five agree today). Then two injections, reverting each: (a) edit
one workflow's tag to a different value → exits `1` with a clear message; (b)
change one workflow's tag to `postgres:18` (major-only) → also exits `1`
(the no-match case is a failure, not a skip).

#### Step B2: Wire it as a `local` pre-commit hook

In the repo-root `.pre-commit-config.yaml`, add a `local` repo (place it in a
sensible section — after the `# GitHub Actions / JSON schema` block, or add a new
`# Repo invariants` section). Because the config `exclude`s the template dir, the
hook must not be file-scoped:

```yaml
  # Repo invariants
  - repo: local
    hooks:
      - id: postgres-image-pin
        name: postgres image pins agree across compose and workflows
        entry: python scripts/check_postgres_image.py
        language: system
        pass_filenames: false
        always_run: true
```

**Verify**:
```
uvx pre-commit run postgres-image-pin --all-files   # Passed
uvx pre-commit run --all-files                       # exit 0
uvx ruff check --select ALL scripts/check_postgres_image.py   # exit 0 (see note)
```

Note on the ruff check: the repo root has **no ruff config** (no root
`pyproject.toml`/`ruff.toml`), so the root pre-commit's ruff hooks lint
`scripts/` with ruff's *default* ruleset only. The `--select ALL` convention
from the template's `AGENTS.md` is therefore NOT enforced automatically — run
the explicit command above and fix findings (a couple of doc/print-related
rules may warrant a targeted `# noqa` with justification; keep those minimal).

#### Step B3: Update the in-file comments to point at the guard

In `tests.yaml`, `migrations-check.yaml` (generated) and root `ci.yaml`, the
existing comment says Dependabot doesn't track these. Append that a pre-commit
check now enforces agreement, so a reader knows the safety net exists — e.g.
`# ... enforced by scripts/check_postgres_image.py (postgres-image-pin hook).`
Keep it a comment-only edit; do not change the image tag.

**Verify**: `uvx pre-commit run --all-files` exit 0; the two generated files are
still copied-unrendered YAML (no Jinja introduced): `grep -c cookiecutter
"{{cookiecutter.project_slug}}/.github/workflows/tests.yaml"` → 0.

## Test plan

- **Part A**: the new matrix case *is* the test — a baked `pytest` run of
  notes+stripped-stack. Verify locally in Step A1; CI runs it on every push.
- **Part B**: the script's own behavior is verified by the deliberate-mismatch
  check in Step B1 (exit 1) and the clean run (exit 0). No pytest is needed for a
  repo-invariant script, but if you want one, a `tests/`-style check is out of
  scope here (the template repo has no root test suite).

## Done criteria

ALL must hold:

- [ ] `.github/workflows/ci.yaml` has an `example-minimal` bake case (alphabetized) with the stripped+notes args; actionlint + check-github-workflows pass.
- [ ] The stripped+notes bake passes baked `pytest` at 100% locally.
- [ ] `scripts/check_postgres_image.py` exists, exits 0 today, and exits 1 on an injected mismatch.
- [ ] `.pre-commit-config.yaml` has the `postgres-image-pin` local hook; `uvx pre-commit run postgres-image-pin --all-files` passes.
- [ ] Root `uvx pre-commit run --all-files` exits 0; no Jinja added to any unrendered workflow.
- [ ] No out-of-scope files modified (`git status`).
- [ ] `plans/README.md` status row updated.

## STOP conditions

Stop and report (do not improvise) if:

- The stripped+notes bake's `pytest` fails — that is a real bug in the notes ×
  stripped-stack rendering; report it rather than editing tests to pass.
- The canonical `prod.yaml` contains more than one distinct `postgres:` tag (the
  regex/assumption is wrong).
- A `local` hook cannot read the excluded template dir in this pre-commit version
  (report; a `files:`-scoped exception may be needed).

## Maintenance notes

- **Rejected alternative**: making `postgres:18.4` a single templated variable
  threaded into workflow service blocks. GitHub Actions service `image:` fields
  accept expressions poorly across matrices, and it would spread Jinja into
  unrendered workflow files. A drift *check* is lower-risk and Dependabot-friendly
  (bump Compose; the hook forces the rest to follow).
- If a new file gains a `postgres:` service pin, add it to `FILES` in the script;
  if a listed file legitimately stops pinning postgres, remove it from `FILES`
  (the script treats a missing pin as drift by design).
- When manually grepping for pins (`grep -rn "postgres:1" .`), exclude
  `.claude/worktrees/` — stale agent worktrees can hold duplicate copies of the
  repo and double the hits.
- A reviewer should confirm the new bake case actually enables notes (not a
  no-op) and that the drift hook runs despite the config-level `exclude`.
- Interacts with any future Redis/Traefik version-pin duplication — the same
  `local`-hook pattern can be extended if that becomes a second drift source.
