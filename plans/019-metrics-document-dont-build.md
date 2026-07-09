# Plan 019 (build): Document the metrics recipe instead of growing a template knob

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving to the
> next step. If anything in the "STOP conditions" section occurs, stop and
> report — do not improvise. When done, update the status row for this plan
> in `plans/README.md` — unless a reviewer dispatched you and told you they
> maintain the index.
>
> **Drift check (run first)**:
> `git diff --stat 16a12b3..HEAD -- README.md '{{cookiecutter.project_slug}}/README.md' '{{cookiecutter.project_slug}}/src/config/settings/components/sentry.py'`
> If any in-scope file changed since this plan was written, compare the
> "Current state" excerpts against the live code before proceeding; on a
> mismatch, treat it as a STOP condition.

## Status

- **Priority**: P3
- **Effort**: S
- **Risk**: LOW
- **Depends on**: none (coordinate with plan 015 — see Current state; both edit
  the generated README's Production section)
- **Category**: docs / direction
- **Planned at**: commit `16a12b3`, 2026-07-09

This is the BUILD plan that settles the former 019 metrics spike (since
removed from `plans/`). The decision below is settled; this plan encodes it
and does not re-open it.

## Why this matters

The former 019 spike asked whether the template should own a metrics surface
(a `/metrics` knob or an OTLP exporter knob). The answer is
**Option A — no knob; document the recipe instead**, for these reasons:

- Sentry, boot-required in production when enabled, already covers error rates
  and sampled request traces and latency (see Current state). That is most of
  what a single-operator deployment — the maintainer's target — needs.
- A scraped `/metrics` endpoint is a new unauthenticated attack surface that
  must be kept off the public ingress, i.e. real security work to ship safely.
- Either knob carries the full optional-integration lifecycle:
  `cookiecutter.json` → gated dependency in `pyproject.toml` → gated settings
  component → removal-list entries in `hooks/post_gen_project.py` → a
  bake-matrix case in root `ci.yaml`. That cost is not justified by the
  marginal value over Sentry.
- **Revisit trigger**: a downstream project actually asks for it.

The deliverable is documentation in two places: an operator recipe in the
GENERATED project's README, and a one-line decision in the root README so a
future audit treats this as settled rather than resurfacing "add OTel" (the
most generic suggestion an audit can make).

## Current state

This repo is a **cookiecutter template**. This plan edits two README files —
the root `README.md` (plain Markdown) and the generated
`{{cookiecutter.project_slug}}/README.md` (Jinja). No settings, deps, hooks,
or CI change. Verification for the generated file means baking a project,
because template source under `{{cookiecutter.project_slug}}/` is EXCLUDED from
root pre-commit — the baked project's own `markdownlint` is the only lint that
runs on it.

Grep at commit `16a12b3` confirms the template ships no metrics machinery:
`prometheus|otel|opentelemetry|statsd|metrics` appears only in the spike doc
itself and in two vendored `.agents/` skill reference docs
(`django-celery-expert/references/monitoring-observability.md`,
`postgres/references/monitoring.md`) — no `/metrics` route, no exporter, no
dependency.

**What Sentry already covers** —
`{{cookiecutter.project_slug}}/src/config/settings/components/sentry.py`
(boot-required: raises `ImproperlyConfigured` if `SENTRY_DSN` is unset):

```python
sentry_sdk.init(
    dsn=SENTRY_DSN,
    release=project_version,
    environment="prod",
    send_default_pii=False,
    ...
    traces_sample_rate=SENTRY_TRACES_SAMPLE_RATE,       # default 0.1
    profile_lifecycle="trace",
    profile_session_sample_rate=SENTRY_PROFILE_SESSION_SAMPLE_RATE,  # 0.1
    enable_logs=SENTRY_ENABLE_LOGS,
)
```

So operators get error rates and 10%-sampled traces/latency/profiles out of
the box. What they do NOT get: unsampled RED metrics, infra dashboards, or
Prometheus-ecosystem alerting — that is what the documented add-ons are for.
The observability probes are split by consumer:
`{{cookiecutter.project_slug}}/src/apps/api/routes/health.py` is liveness-only
(no DB/cache I/O) and `ready.py` is readiness (DB/cache reachability).

**Insertion point 1 — generated README, Production section.** In
`{{cookiecutter.project_slug}}/README.md`, the Production section ends with an
unconditional paragraph about restricting `/admin/`, immediately before the
`## Testing` heading:

```markdown
The admin at `/admin/` is exposed wherever the API is routed. Restrict it at
the proxy with an IP allowlist or route only `/api/` publicly.

## Testing
```

That paragraph and the `## Testing` heading both sit OUTSIDE any Jinja
conditional (the last `{%- endif %}` in Production closes the Redis prose well
above it), so a new `### Metrics` subsection inserted here renders for every
knob combination. The Sentry deploy prose earlier in Production is gated on
`use_sentry == "yes"`, so the new subsection must NOT assume Sentry is on —
the drafted text says "Sentry, when enabled, …" and names the public ingress
generically so it also reads correctly when `use_traefik=no`. Anchor the edit
on the `/admin/` paragraph and the `## Testing` heading, NOT on a line number:
plan 015 edits this same section and may shift line numbers first.

**Insertion point 2 — root README, Design Decisions.** In `README.md`, the
"Design Decisions" bulleted list currently records Sentry but nothing about
metrics:

```markdown
- Production Sentry is boot-required when enabled, so broken observability
  fails before traffic reaches the app.
- CORS is opt-in and requires explicit allowed browser origins; throttling is
  deliberately not enabled by default.
```

Add the new bullet immediately after the "Production Sentry is boot-required
…" bullet (observability-adjacent). Anchor on that bullet's text, not a line
number.

**Lint / pre-commit.** Both READMEs are linted by `markdownlint` with
`--disable=MD013` (root `.pre-commit-config.yaml:46-52`; generated
`{{cookiecutter.project_slug}}/.pre-commit-config.yaml:65-71`). MD013
(line-length) is off, so wrapping width is free — match the surrounding ~79-col
style for consistency. Every OTHER default rule still fires (MD022 blanks
around headings, MD032 blanks around lists, MD031/MD040 for fenced blocks). The
drafted blocks below were validated with `markdownlint --disable=MD013` and
pass. The root `README.md` IS linted by root pre-commit; the generated README
is NOT (template source is excluded) — only a bake exercises its lint. The plan
file itself lives in `plans/`, which is excluded from root pre-commit, so
nothing lints THIS file.

**Collision note.** Plans 003/004 (both DONE) added prose to the generated
README's Production area. The only live TODO plan touching that section is
plan 015 (media backup/restore parity), which edits the `postgres == "compose"`
block (roughly the middle of Production) — a different location from this
plan's end-of-Production insertion, so the conflict risk is low. If 015 lands
first, re-anchor on the `/admin/` paragraph rather than any line number.

## Commands you will need

| Purpose | Command | Expected on success |
|---------|---------|---------------------|
| Drift check | `git diff --stat 16a12b3..HEAD -- README.md '{{cookiecutter.project_slug}}/README.md' '{{cookiecutter.project_slug}}/src/config/settings/components/sentry.py'` | empty (no drift) |
| Bake a default project | `uvx cookiecutter . -o /tmp/verify-019 --no-input` | project at `/tmp/verify-019/my-project` |
| Confirm section renders | `grep -n "### Metrics" /tmp/verify-019/my-project/README.md` | one match |
| Confirm no stray Jinja | `grep -nE "\{\{|\{%" /tmp/verify-019/my-project/README.md` | empty |
| Baked README lint | `cd /tmp/verify-019/my-project && git init -q && git add -A && uv run pre-commit run markdownlint --all-files` | exit 0 |
| Root lint | `uvx pre-commit run --all-files` (repo root) | exit 0 |

## Scope

**In scope**:

- `{{cookiecutter.project_slug}}/README.md` (add one `### Metrics` subsection
  at the end of the Production section).
- `README.md` (add one bullet to Design Decisions).

**Out of scope** (do NOT touch):

- `cookiecutter.json`, `pyproject.toml`, any settings component,
  `hooks/post_gen_project.py`, `.github/workflows/ci.yaml` — Option A adds NO
  knob and NO machinery. If you find yourself editing any of these, stop: the
  decision is "document, don't build".
- `src/config/settings/components/sentry.py` — the Sentry config is read as
  evidence only; it does not change.
- The vendored `.agents/` skill docs that mention Prometheus — they are
  upstream skill content, not template observability policy.

## Git workflow

- Conventional commit, e.g. `docs: document the metrics add-on recipe; record
  the no-knob decision`.
- Do NOT push unless instructed.

## Steps

### Step 1: Add the `### Metrics` subsection to the generated README

In `{{cookiecutter.project_slug}}/README.md`, insert the following block so it
sits immediately BEFORE the `## Testing` heading and AFTER the paragraph ending
`…route only /api/ publicly.` (keep exactly one blank line above `### Metrics`
and one blank line between it and `## Testing`). Insert verbatim:

```markdown
### Metrics

The template ships no metrics endpoint or exporter. Sentry, when enabled,
already captures error rates and sampled request traces and latency, which
covers most single-operator needs. When you want RED/latency dashboards or
Prometheus-ecosystem alerting, add one of these at the project level:

- Scrape model: add
  [`django-prometheus`](https://github.com/korfuri/django-prometheus), which
  exposes a `/metrics` endpoint. Do NOT expose `/metrics` on the public
  ingress (the bundled Traefik router, or whatever proxy fronts the API);
  restrict it to an internal-only listener or an IP-allowlisted route, the
  same way `/admin/` is protected above.
- Push model: add
  [`opentelemetry-instrumentation-django`](https://opentelemetry.io/docs/languages/python/)
  with an OTLP exporter. It adds no scrape surface but needs a collector
  endpoint to push to.
```

The block contains no Jinja and no fenced code, so it is knob-independent by
construction. Do not add any `{% if %}` around or inside it.

**Verify**: the block is plain Markdown with no `{{`/`{%` markers; there is
exactly one blank line before `### Metrics` and one before `## Testing`.

### Step 2: Add the decision bullet to the root README

In `README.md`, in the "Design Decisions" list, insert this bullet immediately
AFTER the `- Production Sentry is boot-required when enabled, …` bullet, verbatim:

```markdown
- Metrics are a project-level add-on, not a template knob: Sentry already
  covers error rates and sampled latency, and a scraped `/metrics` endpoint
  would add an unauthenticated attack surface plus a full knob lifecycle to
  maintain, which is not worth it for single-operator deployments. The
  generated README documents the django-prometheus and OpenTelemetry recipes.
```

**Verify**: the bullet is a single list item at the same indentation as its
neighbors; `uvx pre-commit run markdownlint --all-files` at the repo root
exits 0.

### Step 3: Bake and confirm the generated section renders and lints

```shell
uvx cookiecutter . -o /tmp/verify-019 --no-input
grep -n "### Metrics" /tmp/verify-019/my-project/README.md          # one match
grep -nE "\{\{|\{%" /tmp/verify-019/my-project/README.md            # empty
cd /tmp/verify-019/my-project && git init -q && git add -A
uv run pre-commit run markdownlint --all-files                      # exit 0
```

(`markdownlint` needs the files tracked in git to see them; `git init && git
add -A` in the throwaway bake is enough — do not commit.)

**Verify**: `### Metrics` matches once, no Jinja markers leak, baked
`markdownlint` exits 0.

### Step 4: Root pre-commit

From the repo root: `uvx pre-commit run --all-files` → exit 0 (covers the root
`README.md` edit; the generated README is excluded here, which is why Step 3
bakes).

**Verify**: exit 0.

## Test plan

There is no code to unit-test — this is a docs-only, no-knob change. The
verification IS the test: a default bake must render the `### Metrics` section
with no leaked Jinja and pass the baked project's `markdownlint`, and the root
`README.md` edit must pass root `markdownlint`. Optionally bake one Sentry-off,
Traefik-off combo (`use_sentry=no use_traefik=no`) and re-read the rendered
`### Metrics` block to confirm the "when enabled" / generic-ingress wording
still reads correctly — the block is unconditional, so it renders identically,
but reading it confirms the phrasing does not assume either feature.

## Done criteria

- [ ] `{{cookiecutter.project_slug}}/README.md` has a `### Metrics` subsection
  at the end of Production, before `## Testing`, matching the verbatim block
- [ ] `README.md` Design Decisions has the new metrics bullet after the Sentry
  bullet
- [ ] Default bake renders `### Metrics` once with no `{{`/`{%` leakage
- [ ] Baked project `markdownlint` exits 0; root `uvx pre-commit run
  --all-files` exits 0
- [ ] No file outside the two READMEs changed (`git status` clean otherwise)
- [ ] `plans/README.md` status row updated (this "document, don't build"
  outcome marks the plan DONE — the documentation is the deliverable)

## STOP conditions

Stop and report back if:

- The drift check is non-empty and the live text no longer matches the "Current
  state" excerpts (the `/admin/` paragraph, the `## Testing` heading, the
  Sentry deploy bullet, or the Design Decisions bullets moved or changed) —
  re-anchor before editing.
- Plan 015 has already edited the generated README's Production section and the
  `/admin/` paragraph / `## Testing` boundary no longer looks as excerpted —
  re-anchor on whatever now ends Production, still before `## Testing`.
- A bake leaks Jinja into the rendered `### Metrics` block, or baked
  `markdownlint` fails — the block is meant to be pure Markdown; do not "fix"
  it by wrapping it in Jinja.
- You find any pre-existing metrics knob, dependency, or `/metrics` route
  (grep says none exists at `16a12b3`) — reconcile with it instead of
  documenting a recipe for something already built.

## Maintenance notes

- If a downstream project later asks for a first-class metrics surface (the
  recorded revisit trigger), that is a NEW build plan: it must cost the full
  optional-integration lifecycle (cookiecutter.json → gated dep → gated
  settings component → post-gen removal list → bake-matrix case) and the
  `/metrics` public-exposure gating (the shapes considered and deferred here:
  a django-prometheus scrape knob, or an OTLP-push exporter knob).
- Keep the two documented package names accurate if the ecosystem moves:
  `django-prometheus` (scrape / `/metrics`) and
  `opentelemetry-instrumentation-django` (OTLP push, needs a collector).
- The root README's Design Decisions entry is the durable record; the audit
  playbook treats recorded decisions as settled, so do not let a future audit
  re-open "add OTel" without a downstream request.
