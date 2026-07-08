# Plan 019: SPIKE — decide whether the template should own a metrics/OTel surface

> **Executor instructions**: This is a DESIGN/INVESTIGATION plan with an
> explicit "recommend NOT doing it" outcome on the table. The deliverable is
> a decision document at `plans/019-metrics-decision.md` — you must NOT
> modify any file outside `plans/`. When done, update the status row for
> this plan in `plans/README.md` — unless a reviewer dispatched you and told
> you they maintain the index.
>
> **Drift check (run first)**:
> `git diff --stat 75c4dce..HEAD -- '{{cookiecutter.project_slug}}/src/config/settings/components/' '{{cookiecutter.project_slug}}/src/apps/api/routes/'`
> On drift, re-read before writing.

## Status

- **Priority**: P3 (weakest finding of the 2026-07-08 deep audit — LOW
  confidence that this is worth owning; the spike exists to settle it)
- **Effort**: M for the spike
- **Risk**: LOW (no code changes)
- **Depends on**: none
- **Category**: direction
- **Planned at**: commit `75c4dce`, 2026-07-08

## Why this matters

The template's observability stack is deliberate: liveness/readiness split
(`src/apps/api/routes/health.py` + `ready.py` with DB/cache/broker checks),
boot-required Sentry (`components/sentry.py`), django-structlog request IDs,
JSON prod logging. Metrics is the missing leg — no `/metrics`, no OTel
exporter, no statsd (grep-verified at 75c4dce: only a vendored skill doc
mentions any of them). Operators wanting RED/latency dashboards hand-roll
it. BUT: Sentry already provides errors + sampled traces, the maintainer
runs single-operator deployments, and "add OTel" is the most generic
suggestion an audit can make. The honest question is whether the marginal
value over Sentry justifies a knob, a dependency, and a new unauthenticated
attack surface to secure — "no, document the recipe instead" is a fully
acceptable outcome.

## Current state

- Ops stack evidence: `{{cookiecutter.project_slug}}/src/apps/api/routes/`
  (health/ready), `src/config/settings/components/sentry.py` (boot-required
  in prod; sampling defaults lowered in commit `0bf5843`),
  django-structlog in `components/` + `prod.py` JSON logging.
- Design decisions on record (root README "Design Decisions"): Sentry
  boot-required when enabled; probes split by consumer. No decision about
  metrics exists — this spike creates one either way.
- Constraint pattern for optional integrations: knob in `cookiecutter.json`
  → gated dependency in `pyproject.toml` → gated settings component →
  removal-list entries in `hooks/post_gen_project.py` → bake-matrix case in
  root ci.yaml. Any "yes" recommendation must cost out ALL of these.

## Scope

**In scope**: `plans/019-metrics-decision.md` (create — only file).

**Out of scope**: any implementation; changing Sentry configuration.

## Steps

### Step 1: Establish what Sentry already covers

From the template's Sentry component (integrations, traces/profiles
sampling): list what an operator gets today (error rates, sampled latency)
and what they cannot get (unsampled RED metrics, infra dashboards,
Prometheus-ecosystem alerting).

### Step 2: Cost the candidate shapes

- **A. No knob — document the recipe**: a generated-README section pointing
  at django-prometheus / OTel instrumentation as an operator add-on. Zero
  template surface.
- **B. `/metrics` knob** (e.g. django-prometheus): endpoint exposure
  question is the crux — the API container is reachable via Traefik;
  `/metrics` must NOT ship unauthenticated on the public router. Cost the
  gating (internal-only port? staff-gated view? separate listener?).
- **C. OTel push (OTLP exporter) knob**: no scrape surface (push model),
  but requires a collector endpoint config and a heavier dependency set.

For each: full knob-lifecycle cost (see Current state constraint pattern),
new failure modes at boot (match the template's fail-fast philosophy), and
what the bake matrix must additionally cover.

### Step 3: Write the decision doc

`plans/019-metrics-decision.md`: Sentry-coverage table, options with costs,
a RECOMMENDATION (A, B, C, or "not now" with revisit trigger — e.g. "when a
downstream project actually asks"), and the implementation sketch ONLY for
the recommended option if it is B or C.

## Done criteria

- [ ] Decision doc exists with coverage table, costed options, and an
  unhedged recommendation
- [ ] No file outside `plans/` modified
- [ ] `plans/README.md` status row updated (a "recommend not doing it"
  outcome marks this plan DONE, not REJECTED — the decision is the
  deliverable)

## STOP conditions

- Evidence of an existing metrics decision (README Design Decisions entry,
  memory of a prior cycle) — reconcile with it instead of re-deciding.

## Maintenance notes

- If the recommendation is A/"not now", add one line to the root README's
  Design Decisions so the next audit doesn't resurface this (the audit
  playbook treats recorded decisions as settled).
