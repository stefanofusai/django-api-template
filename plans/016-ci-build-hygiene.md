# Plan 016: CI/build hygiene — cache pre-commit hook envs, keep `.agents/` out of the Docker image, fix the `$$POSTGRES_USER` health-cmd

> **Executor instructions**: Three independent parts (A, B, C) — each can land
> alone; do them in order. Run every verification command. If anything in
> "STOP conditions" occurs, stop and report. When done, update this plan's
> status row in `plans/README.md` — unless a reviewer dispatched you and told
> you they maintain the index.
>
> **Drift check (run first)**:
> `git diff --stat ae42991..HEAD -- .github/workflows/ci.yaml "{{cookiecutter.project_slug}}/.docker/Dockerfile.dockerignore" "{{cookiecutter.project_slug}}/.github/workflows/tests.yaml" "{{cookiecutter.project_slug}}/.github/workflows/migrations-check.yaml"`
> On a mismatch with "Current state", STOP. (Plans 007/010 add bake-matrix
> cases to `ci.yaml` — different region; reconcile if landed.)

## Status

- **Priority**: P3
- **Effort**: S (each part)
- **Risk**: LOW
- **Depends on**: none
- **Category**: dx (A: CI wall-clock; B: image size; C: latent correctness)
- **Planned at**: commit `ae42991`, 2026-07-07

## Repository context (read before anything else)

This is a **Cookiecutter template**; source under
`{{cookiecutter.project_slug}}/` (**quote in shell**). The repo-root
`.github/workflows/ci.yaml` is the template's own CI (editable YAML). The
generated `.github/workflows/*` are copied **without rendering** — no Jinja
there. `.docker/*` is rendered. The baked pre-commit stack includes a
`file-contents-sorter` hook scoped to `.docker/Dockerfile.dockerignore` — that
file must stay sorted (the hook auto-sorts it).

## Why this matters

- **Part A**: the root CI's `bake` job runs the full baked pre-commit in **all
  11 matrix cases**, plus a standalone root `pre-commit` job — and no
  `actions/cache` step for `~/.cache/pre-commit` exists anywhere in
  `ci.yaml`. The identical hook toolchain (ruff, ty, gitlint, markdownlint,
  yamllint/yamlfmt, actionlint, uv-audit, …) is cloned and built from scratch
  ~12× per CI run. One cache step per job removes a large chunk of repeated
  wall-clock.
- **Part B**: `.docker/Dockerfile.dockerignore` excludes `tests/`, `.github/`,
  etc. but **not `.agents/`** — so the entire vendored agent-skills doc tree
  (dozens of markdown files), plus `AGENTS.md`/`skills-lock.json`, is copied
  into the builder (`COPY . /app`, Dockerfile:27) and shipped in the runtime
  image (`COPY --from=builder /app /app`, Dockerfile:79). Pure dead weight in
  every production image.
- **Part C**: three workflow Postgres service blocks use
  `--health-cmd="pg_isready --username=$$POSTGRES_USER"`. The `$$` convention
  was copied from the Compose files, where Compose's own interpolation
  collapses `$$`→`$` — but GitHub Actions passes the string verbatim to
  `docker create`, and the container shell then expands `$$` to its **PID**:
  the check actually runs `pg_isready --username=<pid>POSTGRES_USER`.
  Currently benign (`pg_isready` doesn't authenticate, so the exit code is
  unchanged) but it silently isn't doing what it reads as, and it's a trap if
  the health command is ever extended.

## Current state

Root `.github/workflows/ci.yaml`:
- `bake` job (line 11), Postgres service block lines 15-26 ending in
  `options: >-` / `--health-cmd="pg_isready --username=$$POSTGRES_USER" …`
  (line 26).
- Per-case steps include `uv sync --locked`, `uv run pytest`,
  `./.github/scripts/migrations-check.sh`, and `Run pre-commit`:
  `git add -A && uv run pre-commit run --all-files`.
- Standalone `pre-commit` job near the end: setup-python 3.14, setup-uv
  `astral-sh/setup-uv@v8.2.0`, then `uvx pre-commit run --all-files`.
- No `actions/cache` anywhere in the file.

`{{cookiecutter.project_slug}}/.docker/Dockerfile.dockerignore` (22 sorted
lines): `*.py[cod]`, `.coverage`, `.docker/compose/`, `.env`, `.git/`,
`.github/`, `.idea/`, `.mypy_cache/`, `.pytest_cache/`, `.ruff_cache/`,
`.ty/`, `.venv/`, `.vscode/`, `README.md`, `TODO.md`, `__pycache__/`,
`dist/`, `docs/`, `htmlcov/`, `staticfiles/`, `tests/`. No `.agents/`, no
`AGENTS.md`, no `skills-lock.json`, no `CONTRIBUTING.md`.

`$$POSTGRES_USER` sites (all three):
- `.github/workflows/ci.yaml:26` (repo root)
- `{{cookiecutter.project_slug}}/.github/workflows/tests.yaml:25`
- `{{cookiecutter.project_slug}}/.github/workflows/migrations-check.yaml:25`

Contrast (correct, do NOT touch): the Compose files use `$${POSTGRES_USER}`
(`.docker/compose/prod.yaml:144`, `dev.yaml:99`) — there Compose interpolation
makes `$$` right.

**Conventions**: exact action pins (`actions/checkout@v6.0.3` style);
extended YAML block style; `Dockerfile.dockerignore` stays sorted
(`file-contents-sorter` enforces it).

## Commands you will need

| Purpose | Command | Expected |
|---------|---------|----------|
| actionlint | (repo root) `uvx pre-commit run actionlint check-github-workflows --all-files` | exit 0 |
| No Jinja in generated workflows | `grep -c cookiecutter "{{cookiecutter.project_slug}}/.github/workflows/tests.yaml"` | 0 |
| Bake default | `uvx cookiecutter . --no-input -o /tmp/bake` | project |
| Image build (needs Docker) | `cd /tmp/bake/my-project && docker build -f .docker/Dockerfile --build-arg UV_DEPENDENCY_GROUP=prod -t smoke-016 .` | builds; image lacks `.agents/` |
| Check image contents | `docker run --rm --entrypoint sh smoke-016 -c 'ls -a /app'` | no `.agents`, no `AGENTS.md` |
| Baked + root pre-commit | as in other plans | exit 0 |

## Scope

**In scope**:
- `.github/workflows/ci.yaml` (repo root) — Part A cache steps; Part C `$$`
  fix on line 26.
- `{{cookiecutter.project_slug}}/.docker/Dockerfile.dockerignore` — Part B.
- `{{cookiecutter.project_slug}}/.github/workflows/tests.yaml` and
  `migrations-check.yaml` — Part C `$$` fix only (these are unrendered — no
  Jinja).

**Out of scope**:
- The Compose files' `$${POSTGRES_USER}` (CORRECT there — Compose interpolates).
- The generated `pre-commit.yaml` workflow (it uses `pre-commit/action`,
  which has its own internal cache already — verify and leave alone).
- Any Dockerfile instruction change (Part B is dockerignore-only).
- Adding caching to the *generated* workflows (their own repos' concern;
  `pre-commit/action` covers the pre-commit one).

## Git workflow

- Work directly on `main`. Do NOT branch/commit/push/PR unless told. If asked
  to commit: Conventional Commits, e.g.
  `ci: cache pre-commit envs, trim docker context, fix health-cmd var`.

## Steps

### Part A: cache `~/.cache/pre-commit` in the root CI

In `ci.yaml`, add an `actions/cache` step (pin the exact latest `vX.Y.Z` —
match the repo's exact-pin convention) in TWO places:

1. **`bake` job** — after the uv setup step, before the bake step. The baked
   config is generated, so key on the *template's* copy (it becomes the baked
   file byte-for-byte apart from rendering):

```yaml
      - name: Cache pre-commit environments
        uses: actions/cache@<pinned>
        with:
          path: ~/.cache/pre-commit
          key: pre-commit-${{ runner.os }}-${{ hashFiles('{{cookiecutter.project_slug}}/.pre-commit-config.yaml') }}
```

   (GitHub's `hashFiles` treats the braces literally here — it is a glob over
   a literal path; verify with actionlint and, if `hashFiles` cannot match the
   braced path, fall back to `hashFiles('**/.pre-commit-config.yaml')` and
   say so in your report.)

2. **`pre-commit` job** — same step keyed on the ROOT config:
   `key: pre-commit-root-${{ runner.os }}-${{ hashFiles('.pre-commit-config.yaml') }}`.

**Verify**: actionlint + check-github-workflows exit 0. (The cache's actual
hit behavior is only observable in CI — note in your report that the first CI
run seeds and the second should show `Cache restored` on all 12 jobs.)

### Part B: exclude the agent docs from the Docker build context

Add to `{{cookiecutter.project_slug}}/.docker/Dockerfile.dockerignore` (the
`file-contents-sorter` hook keeps it sorted — add the lines and let the baked
pre-commit sort/confirm):

```
.agents/
AGENTS.md
CONTRIBUTING.md
skills-lock.json
```

**Verify**: bake, build the prod image, and inspect (Commands table) → `/app`
contains no `.agents`, `AGENTS.md`, `CONTRIBUTING.md`, or `skills-lock.json`;
the container still boots (`docker run --rm --entrypoint sh smoke-016 -c
'python -c "import config"'` under the required env, or rely on the existing
compose smoke if Docker boot env is inconvenient — at minimum the image must
build). Baked pre-commit exits 0 (sorter satisfied).

### Part C: fix `$$POSTGRES_USER` → `$POSTGRES_USER`

In the three workflow files listed in Current state, change the health-cmd to
`--health-cmd="pg_isready --username=$POSTGRES_USER"`. Single-character fix
per file; do NOT touch the Compose files.

**Verify**: actionlint + check-github-workflows exit 0;
`grep -rn '\$\$POSTGRES_USER' .github "{{cookiecutter.project_slug}}/.github"`
→ no matches; `grep -c '\$\${POSTGRES_USER}'
"{{cookiecutter.project_slug}}/.docker/compose/prod.yaml"` → unchanged (1).

## Test plan

- No pytest — CI/build config. Gates: actionlint/check-github-workflows, the
  image-contents inspection (Part B), the greps (Part C), and baked + root
  pre-commit runs. The cache's effectiveness is confirmed on the second CI
  run after merge (note it in the report/maintenance).

## Done criteria

ALL must hold:

- [ ] `ci.yaml` has pre-commit cache steps in both the `bake` and `pre-commit` jobs, exact-pinned `actions/cache`; actionlint passes.
- [ ] `Dockerfile.dockerignore` excludes `.agents/`, `AGENTS.md`, `CONTRIBUTING.md`, `skills-lock.json`; file remains sorted (baked pre-commit exit 0); a built prod image contains none of them.
- [ ] Zero `$$POSTGRES_USER` occurrences in workflow files; Compose files untouched.
- [ ] Root + baked pre-commit exit 0; no Jinja introduced into any unrendered workflow.
- [ ] No out-of-scope files modified (`git status`); `plans/README.md` status row updated.

## STOP conditions

Stop and report (do not improvise) if:

- `hashFiles` cannot address the braced template path AND the `**` glob
  fallback would hash unrelated configs ambiguously — report the options
  rather than shipping a key that never matches.
- The image build fails after the dockerignore change (something at runtime
  imports from an excluded path — investigate which, report; do not just
  un-exclude).
- The health-cmd change makes any workflow's Postgres service fail to report
  healthy (it should not — report the log).

## Maintenance notes

- After merge, confirm on the second CI run that all 12 jobs restore the
  pre-commit cache; if the bake jobs miss, the key's `hashFiles` path is the
  suspect.
- If the baked pre-commit config later gains Jinja-conditional hooks, the
  cache key (template copy) still changes whenever the config changes — the
  key stays correct.
- The `$$` fix is the canonical example of "Compose escaping copied into a
  non-Compose context"; a reviewer seeing future service blocks should check
  which interpolation layer actually applies.
