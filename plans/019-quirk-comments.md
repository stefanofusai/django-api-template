# Plan 019: Add quirk/decision comments at the codebase's trap points

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving to the
> next step. If anything in the "STOP conditions" section occurs, stop and
> report — do not improvise. When done, update the status row for this plan
> in `plans/README.md` — unless a reviewer dispatched you and told you they
> maintain the index.
>
> **Drift check (run first)**: `git diff --stat 7d246c3..HEAD -- '{{cookiecutter.project_slug}}/src/' '{{cookiecutter.project_slug}}/.docker/' '{{cookiecutter.project_slug}}/AGENTS.md'`
> Several pending plans rewrite files this plan comments — each site below
> carries its own "if plan NNN landed/changed this" note. Apply comments to
> the LIVE shape of each file; skip a site only when its note says so.

## Status

- **Priority**: P3
- **Effort**: S
- **Risk**: LOW (comment-only diff; zero runtime change)
- **Depends on**: none strictly; cleanest AFTER 004/005/006 (see per-site notes). Do not run in a parallel worktree with any plan touching the same files.
- **Category**: docs / dx
- **Planned at**: commit `7d246c3`, 2026-07-05

## Why this matters

This codebase has a small number of genuine trap points — places where a
competent reader (human or agent) confidently reaches the WRONG conclusion.
This is not hypothetical: during the 2026-07 audit, the unparenthesized
`except` in `ready.py` was independently flagged as a syntax error by three
reviewers, and the settings-module wiring in `config/__init__.py` was
falsely diagnosed as a missing-configuration bug. Each false alarm costs
investigation time on every future audit, review, or onboarding.

The maintainer wants comments **exactly in the style of the exemplar** in
`src/apps/api/pagination.py:7-10`:

```python
# Ninja defaults PAGINATION_MAX_LIMIT to inf; fall back to the page size so the
# default stays bounded, while an explicit finite setting can raise the cap.
# Note: ninja's PAGINATION_MAX_OFFSET defaults to 100 — raise it via
# NINJA_PAGINATION_MAX_OFFSET when clients must page past the first ~200 rows.
```

What makes that comment good, and the bar every comment in this plan must
meet: it states a **constraint the code cannot show** (an upstream default,
a cross-file coupling, a deliberately unusual construct) and names the
**concrete misreading it prevents**. If you cannot say what a reader would
get wrong without the comment, do not write it.

**Hard anti-goal**: no narration. Never add comments that restate what the
code does (`# create the router`), where something came from, or generic
section headers. A sprayed-comments diff is a failed execution of this plan.

## Important context: this is a cookiecutter template

- Project code lives under the literal `{{cookiecutter.project_slug}}/` dir —
  quote it in shell. Preserve Jinja placeholders verbatim.
- Verification = bake (`uvx cookiecutter . --no-input -o <dir>`) + baked
  suite (`uv run pytest`, 100% coverage — unaffected by comments) + baked
  pre-commit (ruff-format may rewrap long comment lines; yamllint requires
  at least one space between `#` and content in YAML).
- Comment style: full sentences, sentence case, wrapped near 79 columns,
  placed on the line(s) directly above the code they govern — match the
  exemplar.

## The comment sites

Each site: the live code anchor, the misreading being prevented, and the
comment text to place (adjust wrapping to the file; keep the meaning exact).

### Site 1 — `src/config/__init__.py` (settings wiring + import order)

Live file (whole):

```python
import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

from .celery import app as celery_app

__all__ = ("celery_app",)
```

Misreading prevented: reviewers conclude gunicorn/celery have no
`DJANGO_SETTINGS_MODULE` (it is set nowhere else), or "fix" the import order
by moving the celery import above the `setdefault`. Add above line 3:

```python
# Importing this package is what configures Django for every process:
# gunicorn (config.wsgi) and celery (-A config) both import it before
# touching settings. The celery import below must stay AFTER setdefault.
```

(The existing `from .celery import ...` line may carry a `noqa: E402`-style
suppression after this change if Ruff asks for one — accept whatever Ruff
requires, but do not reorder the lines.)

### Site 2 — `src/apps/api/routes/ready.py` (PEP 758 + `is False`)

Live anchors: line 39 `if cache.set(cache_key, cache_value, timeout=1) is
False:` and line 44 `except ConnectionInterrupted, OSError, RedisError:`.

Misreadings prevented: (a) the parenthesis-free `except` tuple reads as a
Python 2 syntax error — three independent reviewers flagged it during the
audit; it is PEP 758, valid on the pinned 3.14; (b) `is False` looks like it
should be `not ...` — but `cache.set` returns `None` on backends that don't
report an outcome (e.g. locmem), and only an explicit `False` means the
backend rejected the write; the `get` round-trip below covers the `None`
case.

Above line 39:

```python
    # cache.set returns None on backends that do not report an outcome;
    # only an explicit False means the backend rejected the write. The get
    # round-trip below verifies the None case.
```

Above line 44 (attach to the `except` line):

```python
    # Parenthesis-free except tuples are PEP 758 syntax (Python 3.14+).
```

If a pending refactor has parenthesized the tuple by execution time, drop
the second comment — it earns its place only next to the unusual form.

### Site 3 — `src/apps/api/routes/health.py` (no-I/O liveness by design)

Live file: a single `/health` route returning `Status(200, ...)` with no
imports of `cache`/`connections`.

Misreading prevented: a future contributor "improves" the health check by
adding DB/cache probes — which reintroduces the exact bug the health/ready
split fixed (a DB blip restarting a healthy container). Add above the
`@router.get` decorator:

```python
# Liveness only, by design: no database or cache I/O. The container
# healthcheck restarts on failure here, so dependency outages must NOT fail
# this route — that is /ready's job (load balancers, not restarts).
```

### Site 4 — `src/config/settings/__init__.py` (the split-settings namespace)

Live anchor: the `include(...)` call listing components then
`f"environments/{DJANGO_ENV}.py"`.

Misreading prevented: the `noqa: F821` / `ty: ignore` markers scattered
through the environment overlays look like suppressed bugs; the mechanism
that makes those names real lives here. Add directly above `include(`:

```python
# include() executes every file below in one shared namespace, in order:
# components define names (MIDDLEWARE, LOGGING, STORAGES, ...) that the
# environment overlay at the end mutates. The overlays' noqa: F821 markers
# exist because linters cannot see this shared namespace.
```

### Site 5 — `src/config/settings/environments/prod.py` (two traps)

Live anchors (post-plan-002 shape): line 21 `SECURE_PROXY_SSL_HEADER = ...`
and line 22 `SECURE_REDIRECT_EXEMPT = [r"^api/health$", r"^api/ready$"]`.

Misreadings prevented: (a) the exempt patterns look like they are missing a
leading slash — they are not: Django matches them against
`request.path.lstrip("/")`, and the exemption is what lets plain-HTTP
container healthchecks reach the probes; (b) trusting
`HTTP_X_FORWARDED_PROTO` is only safe behind a proxy that overwrites the
client's value.

Above line 21 (one block covering both consecutive settings):

```python
# X-Forwarded-Proto is trusted here, which is only safe behind a proxy that
# overwrites the client-supplied header (see README, Production). The
# redirect-exempt patterns match request.path.lstrip("/") — no leading
# slash — and keep the plain-HTTP container healthchecks reachable.
```

If plan 018 (Traefik) has landed, keep the comment but the README pointer
already resolves to the rewritten Production section — no change needed.

### Site 6 — `src/apps/core/models.py` (uuid7 over uuid4)

Live anchor: `id = models.UUIDField(primary_key=True, default=uuid.uuid7,
editable=False)` in `UUIDModel`.

Misreading prevented: uuid7 looks like an arbitrary or erroneous choice next
to the ubiquitous uuid4. Add above the `id` field:

```python
    # uuid7 (stdlib since 3.14) over uuid4: time-ordered values keep b-tree
    # primary-key indexes append-mostly instead of randomly fragmented.
```

Note: this file currently also contains `User(AbstractUser)` — do not touch
it; it belongs to plan 003's follow-ups.

### Site 7 — `.docker/Dockerfile` (dummy env for collectstatic + two-phase sync)

Live anchors: the first `RUN --mount... uv sync ... --no-install-project`
block, and the `RUN ALLOWED_HOSTS=localhost ... collectstatic --no-input`
block with `$(uuidgen)` values.

Misreadings prevented: (a) the doubled `uv sync` looks redundant — the first
pass installs only dependencies so the layer caches independently of source
changes; (b) the env block looks like real configuration — the values exist
solely to satisfy prod settings import during `collectstatic` and are never
used. Dockerfile comments use `#`:

```dockerfile
# Dependencies only (no project) so this layer caches until the lockfile
# changes; the post-COPY sync below installs the rest.
```

```dockerfile
# Throwaway values: prod settings require these at import time, but nothing
# reads them during collectstatic.
```

If plan 010 landed (apt split across stages), anchors shift but both RUN
blocks still exist — place the comments on the live lines. If plans 007/009
landed, the env block also contains SENTRY_DSN/RESEND_API_KEY dummies — the
comment covers them unchanged.

### Site 8 — `.docker/compose/dev.yaml` AND `prod.yaml` (worker gate)

Live anchor in both files: the worker service's

```yaml
    depends_on:
      api:
        condition: service_healthy
```

Misreading prevented: the worker does not talk to the api over HTTP, so this
dependency looks wrong/removable — but api "healthy" is the proxy for
"migrations completed" (api's `pre_start` blocks its start on
`migrations.sh`). Add above `depends_on:` in the worker service of BOTH
files (yamllint needs a space after `#`):

```yaml
    # Gates on api health as a "migrations completed" signal: api's
    # pre_start runs migrate before the api container starts serving.
    depends_on:
```

If plan 008 landed, the beat service has the same dependency for the same
reason — add the same comment there too.

## Codify the policy (AGENTS.md)

Add one bullet under `## Style` in `{{cookiecutter.project_slug}}/AGENTS.md`:

"Only add code comments that state constraints the code cannot show —
upstream defaults, cross-file couplings, deliberately unusual constructs —
and that name the misreading they prevent (see
`src/apps/api/pagination.py` for the canonical example). Never add comments
that narrate what the code does."

This makes the practice durable: every future agent baking from this
template inherits the rule, not just the instances.

## Commands you will need

| Purpose | Command | Expected on success |
|---------|---------|---------------------|
| Bake | `uvx cookiecutter . --no-input -o $BAKE` (template root) | exit 0 |
| Tests | `cd $BAKE/my-project && uv run pytest` | all pass, 100% |
| Hooks | `cd $BAKE/my-project && git add -A && uv run pre-commit run --all-files` | all pass (ruff-format, yamllint, yamlfmt validate the comments) |

## Scope

**In scope** (comments and the AGENTS.md bullet ONLY — no code changes):
- `{{cookiecutter.project_slug}}/src/config/__init__.py`
- `{{cookiecutter.project_slug}}/src/apps/api/routes/ready.py`
- `{{cookiecutter.project_slug}}/src/apps/api/routes/health.py`
- `{{cookiecutter.project_slug}}/src/config/settings/__init__.py`
- `{{cookiecutter.project_slug}}/src/config/settings/environments/prod.py`
- `{{cookiecutter.project_slug}}/src/apps/core/models.py`
- `{{cookiecutter.project_slug}}/.docker/Dockerfile`
- `{{cookiecutter.project_slug}}/.docker/compose/dev.yaml`
- `{{cookiecutter.project_slug}}/.docker/compose/prod.yaml`
- `{{cookiecutter.project_slug}}/AGENTS.md`

**Out of scope — files whose quirks are owned by pending plans (check
`plans/README.md` status before touching):**
- `src/config/settings/components/celery.py` — plan 006 adds the
  results-are-opt-in comment; do not duplicate it here.
- `src/config/pyproject.py` — plan 005 rewrites the module.
- `src/apps/api/api.py` — plans 015/017 rewrite it (015's split and 017's
  decorator carry their own explanatory needs).
- `src/config/settings/components/database.py` — plan 016 replaces it.
- `.env.example` — the file-contents-sorter hook reorders lines; free-form
  comments do not survive placement.
- Any comment restating behavior (the anti-goal) anywhere.

## Git workflow

- Branch: `advisor/019-quirk-comments`
- Conventional commit, e.g. `docs: add quirk and decision comments at trap points`
- Do NOT push or open a PR unless the operator instructed it.

## Steps

### Step 1: Python sites (1–6)

Apply the comments exactly as specified, adjusted only for the live shape of
each file per the per-site notes.

**Verify**: bake → `uv run pytest` → all pass, 100% (comments cannot change
coverage; if anything fails, you changed code — revert and redo).

### Step 2: Dockerfile + compose sites (7–8)

Apply the three infrastructure comments (both compose files).

**Verify**: in the bake, `docker compose -f .docker/compose/dev.yaml config`
→ renders unchanged apart from nothing (comments are stripped from rendered
output; the command exiting 0 proves YAML validity). If Docker is absent,
`uv run pre-commit run yamllint --all-files` is the fallback gate.

### Step 3: AGENTS.md bullet

Add the policy bullet under `## Style`.

**Verify**: `uv run pre-commit run markdownlint --all-files` in the bake →
passes.

### Step 4: Anti-noise review + full loop

Run `git diff` on the template repo and confirm: every added line is a
comment line (or the AGENTS.md bullet); **zero** modified or deleted code
lines; no file outside the in-scope list.

**Verify**: fresh bake → `uv run pytest` → all pass, 100%;
`git add -A && uv run pre-commit run --all-files` → all pass.

## Test plan

None — a comment-only diff has no behavior to test. The gates are: the full
suite unchanged, the hooks (format/lint the comments), and the Step 4
diff-is-comments-only review.

## Done criteria

- [ ] Each in-scope file contains its specified comment (spot-check greps: `grep -n "PEP 758" .../routes/ready.py`, `grep -n "Liveness only" .../routes/health.py`, `grep -n "shared namespace" .../settings/__init__.py`, `grep -n "migrations completed" .../compose/prod.yaml`)
- [ ] AGENTS.md has the comment-policy bullet referencing pagination.py
- [ ] `git diff` shows added comment lines only — no code line modified or deleted
- [ ] Baked project: `uv run pytest` → all pass, 100%
- [ ] Baked project: `uv run pre-commit run --all-files` → all pass
- [ ] No files outside the in-scope list modified (`git status`)
- [ ] `plans/README.md` status row updated

## STOP conditions

- A site's live code no longer matches even the per-site drift note (e.g. a
  pending plan removed the construct the comment explains) — skip that site
  with a note in the index row; if more than three sites are gone, stop and
  report (the plan needs re-anchoring, not improvisation).
- Ruff or ruff-format demands a CODE change (not a comment rewrap) to accept
  a comment — stop; comments must never force code changes.
- You feel the urge to add a comment at a site not listed here — resist it;
  propose it in the PR description instead. The list is the scope.

## Maintenance notes

- The AGENTS.md bullet is the enduring deliverable; the eight sites are the
  seed examples. Reviewers should hold future comments to the same bar:
  name the misreading or delete the comment.
- When pending plans (005/006/015/016/017) land their own rewrites, their
  new code carries its own comments per that bullet — this plan deliberately
  does not pre-comment code that is about to be replaced.
- If `ready.py`'s except tuple is ever parenthesized, delete the PEP 758
  comment with it.
