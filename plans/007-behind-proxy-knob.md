# Plan 007: Gate HTTPS-trust settings on a `behind_proxy` knob so non-proxied prod deploys don't trust a spoofable header

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving to the
> next step. If anything in the "STOP conditions" section occurs, stop and
> report — do not improvise. **Read the "Design decision" note in Steps before
> writing code.** When done, update the status row for this plan in
> `plans/README.md` — unless a reviewer dispatched you and told you they
> maintain the index.
>
> **Drift check (run first)**:
> `git diff --stat ae42991..HEAD -- "{{cookiecutter.project_slug}}/src/config/settings/environments/prod.py" "{{cookiecutter.project_slug}}/.docker/compose/prod.yaml" cookiecutter.json "{{cookiecutter.project_slug}}/README.md" "{{cookiecutter.project_slug}}/.env.example" .github/workflows/ci.yaml`
> If any in-scope file changed since this plan was written, compare the
> "Current state" excerpts against the live code before proceeding; on a
> mismatch, treat it as a STOP condition.

## Status

- **Priority**: P2
- **Effort**: M
- **Risk**: MED (touches prod security settings; default bake must stay byte-identical)
- **Depends on**: none (but coordinates with plan 010 — both add a case to the root `ci.yaml` bake matrix; land one, then re-check the matrix)
- **Category**: security
- **Planned at**: commit `ae42991`, 2026-07-07 (all excerpts re-verified against live code same day)

## Repository context (read before anything else)

This is a **Cookiecutter template**. Project source is under the literal
directory `{{cookiecutter.project_slug}}/` — **quote it in shell**. Files
inside contain Jinja (`{{ cookiecutter.* }}`, `{%- if ... %}`) that must stay
valid.

- `cookiecutter.json` (repo root) defines the bake variables and the
  `__prompts__` help text.
- `hooks/pre_gen_project.py` and `hooks/post_gen_project.py` run at bake time;
  `post_gen` deletes knob-disabled files. This plan does **not** need a hook
  change (it gates settings inline, deletes no files) — confirm that during
  execution.
- **`.github/workflows/*` and `.agents/*` inside `{{cookiecutter.project_slug}}/`
  are copied WITHOUT rendering.** But the **repo-root** `.github/workflows/ci.yaml`
  is the *template's own* CI and IS a normal rendered-at-author-time YAML file
  you may edit (it drives the bake matrix). Do not confuse the two.
- **Verification means baking and running the deploy check.** Bake:
  `uvx cookiecutter . --no-input -o /tmp/bake [key=value ...]`.

## Why this matters

`{{cookiecutter.project_slug}}/src/config/settings/environments/prod.py` sets
`SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")`
**unconditionally**, for every bake. That tells Django to treat any request
carrying `X-Forwarded-Proto: https` as a secure request. It is only safe behind
a proxy that *overwrites* the client-supplied header (the README documents
this). But the template can be baked with `use_traefik=no` ("bring your own
ingress"), and in that mode the app is exposed directly on a host port
(the CI smoke test probes `http://127.0.0.1:8000` directly). Anything able to
reach that port can send `X-Forwarded-Proto: https` over plain HTTP and make
Django believe the connection is secure — defeating `SECURE_SSL_REDIRECT`,
leaking `Secure` cookies over HTTP, and mis-driving HSTS logic.

The fix: make "there is a trusted TLS-terminating proxy in front that sets
`X-Forwarded-Proto`" an explicit, gated assumption instead of an unconditional
one. Bundled Traefik (`use_traefik=yes`) always is that proxy; for
`use_traefik=no` deployments the operator declares it via a new `behind_proxy`
knob (default `yes`, preserving today's behavior).

## Current state

`{{cookiecutter.project_slug}}/src/config/settings/environments/prod.py`
(full file today):

```python
from django.core.exceptions import ImproperlyConfigured

from config.settings import env

if SECRET_KEY.startswith("django-insecure-"):  # noqa: F821  # ty: ignore[unresolved-reference]
    msg = "SECRET_KEY must be replaced with a securely generated value in production."
    raise ImproperlyConfigured(msg)
{%- if cookiecutter.email_provider == "resend" %}
# ... email backends (unchanged by this plan) ...
{%- endif %}
API_DOCS_DECORATOR = "django.contrib.admin.views.decorators.staff_member_required"
CSRF_COOKIE_SECURE = True
CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS")
# ... email settings ...
LOGGING["handlers"]["console"]["formatter"] = "json"  # noqa: F821  # ty: ignore[unresolved-reference]
MIDDLEWARE.insert(  # noqa: F821  # ty: ignore[unresolved-reference]
    1,
    "whitenoise.middleware.WhiteNoiseMiddleware",
)
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_HSTS_SECONDS = 31536000
# X-Forwarded-Proto is trusted here, which is only safe behind a proxy that
# overwrites the client-supplied header (see README, Production). The
# redirect-exempt patterns match request.path.lstrip("/") — no leading
# slash — and keep the plain-HTTP container healthchecks reachable.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_REDIRECT_EXEMPT = [r"^api/health$", r"^api/ready$"]
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
{%- if cookiecutter.use_s3_media == "yes" %}
# ... STORAGES default (unchanged) ...
{%- endif %}
STORAGES["staticfiles"] = {  # noqa: F821  # ty: ignore[unresolved-reference]
    "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
}
```

`cookiecutter.json` (relevant shape — knobs are string-choice lists, first
value is the default; each has a `__prompts__` entry):

```json
"traefik_tls": ["letsencrypt", "external"],
"use_celery": ["worker+beat", "worker", "none"],
"use_example_api": ["no", "yes"],
"use_s3_media": ["yes", "no"],
"use_sentry": ["yes", "no"],
"use_traefik": ["yes", "no"],
```

The runtime serves plain HTTP: `.docker/scripts/gunicorn.sh` binds
`--bind=0.0.0.0:8000` with no TLS. So TLS is always terminated upstream; the
only question this knob answers is whether that upstream is *trusted to set
`X-Forwarded-Proto`*.

**Conventions (from `AGENTS.md` and existing code)**:
- Knob names use the `use_*` / snake_case style; `traefik_tls` shows non-`use_`
  knobs are fine. `behind_proxy` fits.
- `.env.example`: "Empty uncommented values are required in production";
  comments own-line only; grouped by concern, alphabetized within a block.
  This plan adds **no** env var (the knob is a bake-time choice, not a runtime
  env var — matches "Add environment variables only for secrets, deployment
  topology, or resource sizing" and "Keep operational constants fixed in
  code").
- prod.py `noqa: F821  # ty: ignore[unresolved-reference]` markers exist
  because settings share one namespace via `django-split-settings`; keep them
  on any mutation of a name defined in a component.
- YAML uses extended block style; JSON knob lists are compact arrays (match
  the existing `cookiecutter.json` formatting exactly).

## Commands you will need

| Purpose | Command | Expected |
|---------|---------|----------|
| Bake default (proxy on) | `uvx cookiecutter . --no-input -o /tmp/bake-default` | `behind_proxy` defaults yes; prod.py unchanged from today |
| Bake no-proxy | `uvx cookiecutter . --no-input -o /tmp/bake-np use_traefik=no behind_proxy=no` | prod.py omits `SECURE_PROXY_SSL_HEADER` etc. |
| Deploy security check | `cd /tmp/bake-*/my-project && <env> uv run --group=ci --locked --no-default-groups manage.py check --deploy --fail-level=WARNING --tag=security` | see Step 5 |
| Baked pre-commit | `cd /tmp/bake-*/my-project && git add -A && uv run pre-commit run --all-files` | exit 0 |
| Baked tests | `cd /tmp/bake-*/my-project && DATABASE_URL=postgres://postgres:postgres@localhost:5432/postgres uv run pytest` | 100% cov, all pass (needs a running postgres:18.4) |
| Root pre-commit | (repo root) `uvx pre-commit run --all-files` | exit 0 |

The exact env prefix for the deploy check is the one baked into
`{{cookiecutter.project_slug}}/.github/scripts/deploy-check.sh` — read that file
and reuse its variable set verbatim for manual runs.

## Scope

**In scope**:
- `cookiecutter.json` — add the `behind_proxy` knob and its `__prompts__` entry.
- `{{cookiecutter.project_slug}}/src/config/settings/environments/prod.py` —
  gate the HTTPS-trust block on the new condition.
- `{{cookiecutter.project_slug}}/.docker/compose/prod.yaml` — gate the
  `FORWARDED_ALLOW_IPS` env var on the same condition (see Step 5b). This dir is
  **rendered** (only `.github/workflows/*` and `.agents/*` are copied unrendered),
  so Jinja is allowed here.
- `{{cookiecutter.project_slug}}/README.md` — document the knob and the
  no-proxy mode in the Production/Design-Decisions section.
- `.github/workflows/ci.yaml` (repo root) — add one bake-matrix case exercising
  `use_traefik=no behind_proxy=no` (see Step 6).

**Out of scope**:
- `hooks/*.py` — no file is added/removed by this knob; do not touch unless
  Step 4's verify shows an unexpected need (then STOP).
- `.env.example` — the knob is bake-time, not a runtime env var; adding an env
  var here would violate the documented `.env.example` contract.
- The `dev.py`/`ci.py` overlays — they never set these HTTPS settings.
- Any `{{cookiecutter.project_slug}}/.github/workflows/*` file (copied without
  rendering; cannot hold knob-conditional Jinja).

## Git workflow

- Work directly on `main`. Do NOT branch, commit, push, or open a PR unless the
  operator explicitly says so. If asked to commit, use Conventional Commits
  (e.g. `feat: gate prod HTTPS-trust settings on a behind_proxy knob`).

## Steps

### Design decision (confirm intent before coding)

This plan defines `behind_proxy=no` to mean **"prod is served over plain HTTP
with no trusted TLS-terminating proxy in front"** (e.g. an internal API on a
private/mesh network). In that mode the template drops *all* HTTPS-enforcement
settings, not just the header trust, because with no HTTPS reaching the app
`SECURE_SSL_REDIRECT` would loop and `Secure` cookies would never be sent.

If the maintainer's intent is that this template must **only ever** support
proxied HTTPS deployments (no plain-HTTP prod mode at all), then a knob is the
wrong fix and the finding should instead be closed by hardening docs + network
exposure. **If you cannot confirm the intended semantics, STOP and report the
two options rather than guessing.** Otherwise proceed.

### Step 1: Add the `behind_proxy` knob to `cookiecutter.json`

The file groups metadata keys first (`project_name` … `domain_name`), then the
choice knobs in alphabetical order (`email_provider`, `postgres`, `redis`,
`traefik_tls`, `use_*`). `behind_proxy` sorts alphabetically **before
`email_provider`**, so insert it as the FIRST choice knob — immediately after
the `"domain_name"` line — and insert its `__prompts__` entry immediately
before the `email_provider` prompt entry. Add:

```json
"behind_proxy": ["yes", "no"],
```

and a matching `__prompts__` entry:

```json
"behind_proxy": {
    "__prompt__": "Production trusts an upstream proxy's X-Forwarded-Proto header",
    "yes": "A reverse proxy terminates TLS and sets X-Forwarded-Proto (required for bundled Traefik)",
    "no": "App is served over plain HTTP with no trusted proxy (internal/private network only)"
},
```

Match the exact indentation and quoting style already in `cookiecutter.json`.

**Verify**: `uvx cookiecutter . --no-input -o /tmp/bake-default` succeeds and
`python -c "import json; json.load(open('cookiecutter.json'))"` exits 0.

### Step 2: Gate the HTTPS-trust settings in `prod.py` — TWO separate gates

The file orders top-level assignments alphabetically, and Step 3 requires the
default render to be byte-identical to today's file. Both constraints together
mean you must NOT move any line: wrap each scheme-dependent region **in place**
with the same condition. That yields **two** `{% if %}` gates:

**Gate 1** — around `CSRF_COOKIE_SECURE = True` alone (it sits at its
alphabetical position between `API_DOCS_DECORATOR` and `CSRF_TRUSTED_ORIGINS`;
do not move it):

```python
{%- if cookiecutter.use_traefik == "yes" or cookiecutter.behind_proxy == "yes" %}
CSRF_COOKIE_SECURE = True
{%- endif %}
```

**Gate 2** — around the contiguous block from `SECURE_HSTS_INCLUDE_SUBDOMAINS`
through `SESSION_COOKIE_SECURE` (live lines 31-41: the three `SECURE_HSTS_*`
lines, the 4-line X-Forwarded-Proto comment, `SECURE_PROXY_SSL_HEADER`,
`SECURE_REDIRECT_EXEMPT`, `SECURE_SSL_REDIRECT`, `SESSION_COOKIE_SECURE`):

```python
{%- if cookiecutter.use_traefik == "yes" or cookiecutter.behind_proxy == "yes" %}
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_HSTS_SECONDS = 31536000
# X-Forwarded-Proto is trusted here, which is only safe behind a proxy that
# overwrites the client-supplied header (see README, Production). The
# redirect-exempt patterns match request.path.lstrip("/") — no leading
# slash — and keep the plain-HTTP container healthchecks reachable.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_REDIRECT_EXEMPT = [r"^api/health$", r"^api/ready$"]
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
{%- endif %}
```

Rationale for gating the cookie flags too: without HTTPS reaching the app the
browser will never send `Secure` cookies, breaking admin login in a
deliberately-plain-HTTP deployment.

Keep **unconditional**: `SECURE_CONTENT_TYPE_NOSNIFF = True`, the whitenoise
middleware insert, `CSRF_TRUSTED_ORIGINS`, the JSON logging formatter, and the
staticfiles storage — these are scheme-independent.

**Note on lint markers**: none of the gated lines carries a
`# noqa: F821  # ty: ignore[...]` marker today (those markers live only on
lines that *reference* component-defined names, e.g. `LOGGING`, `MIDDLEWARE`,
`STORAGES` — all of which stay unconditional). Do not add markers to the gated
lines, and do not touch the existing ones.

**Verify**:
```
uvx cookiecutter . --no-input -o /tmp/bake-np use_traefik=no behind_proxy=no
grep -c "SECURE_PROXY_SSL_HEADER" /tmp/bake-np/my-project/src/config/settings/environments/prod.py
```
→ `0` for the no-proxy bake. Then confirm the default bake still contains it:
```
uvx cookiecutter . --no-input -o /tmp/bake-default
grep -c "SECURE_PROXY_SSL_HEADER" /tmp/bake-default/my-project/src/config/settings/environments/prod.py
```
→ `1`. And `use_traefik=yes behind_proxy=no` must STILL contain it:
```
uvx cookiecutter . --no-input -o /tmp/bake-ty use_traefik=yes behind_proxy=no
grep -c "SECURE_PROXY_SSL_HEADER" /tmp/bake-ty/my-project/src/config/settings/environments/prod.py
```
→ `1` (Traefik is a trusted proxy regardless of the knob).

### Step 3: Byte-identity check for existing bakes

The default (`behind_proxy=yes`) render of `prod.py` must be **byte-identical**
to what a default bake produced before your edits. Compare rendered output to
rendered output — do NOT diff against the raw template file from git, because
the template contains *other* Jinja (email/S3 blocks) that renders differently
from its source and would produce spurious diffs.

**Before touching any file** (do this first if you have not already):

```
uvx cookiecutter . --no-input -o /tmp/bake-before
cp /tmp/bake-before/my-project/src/config/settings/environments/prod.py /tmp/prod-before.py
```

After Steps 1-2:

```
uvx cookiecutter . --no-input -o /tmp/bake-default
diff /tmp/prod-before.py /tmp/bake-default/my-project/src/config/settings/environments/prod.py
```

**Verify**: `diff` prints nothing (exit 0). If you forgot the before-snapshot,
`git stash` your edits, bake, snapshot, `git stash pop`, and diff.

### Step 4: Confirm no hook change is needed

```
grep -n "behind_proxy\|BEHIND_PROXY" hooks/pre_gen_project.py hooks/post_gen_project.py
```

**Verify**: no matches — the knob deletes no files, so the hooks need no edit.
If you find yourself wanting to edit a hook, STOP and report.

### Step 5: Run the deploy security check both ways

Read `{{cookiecutter.project_slug}}/.github/scripts/deploy-check.sh` for the
exact env-var prefix. Run its `manage.py check --deploy ... --tag=security`
against both bakes (install deps first with `uv sync --group=ci --locked
--no-default-groups`):

- **Default bake** (`behind_proxy=yes`): the deploy check must still pass with
  no new security warnings (it passed before this plan).
- **No-proxy bake** (`use_traefik=no behind_proxy=no`): Django's deploy check
  emits `security.W008` (SECURE_SSL_REDIRECT) / `W012`/`W016` (secure cookies)
  when those are off. Because `deploy-check.sh` uses `--fail-level=WARNING`,
  the no-proxy bake's deploy check **will now warn/fail** — that is *expected
  and correct* for a deliberately-plain-HTTP deployment.

**This is a decision point**: the shipped `deploy-check.sh` should not hard-fail
a valid no-proxy bake. Choose the minimal handling and record it in your report:
either (a) leave `deploy-check.sh` as-is and document that no-proxy operators
must scope/adjust it, or (b) make the check's `--fail-level`/tag selection
knob-aware. **Prefer (a)** unless the maintainer asks otherwise — do not silently
weaken the security gate for the default (proxied) deployment. If you cannot
decide, STOP and report.

**Verify**: default bake deploy check exits 0; document the no-proxy behavior.

### Step 5b: Gate the ASGI-layer proxy-header trust in `prod.yaml`

`{{cookiecutter.project_slug}}/.docker/compose/prod.yaml` currently sets, on the
`api` service, **unconditionally** (today's file):

```yaml
    environment:
      DJANGO_ENV: prod
      FORWARDED_ALLOW_IPS: "*"
```

`FORWARDED_ALLOW_IPS: "*"` is the ASGI-server (uvicorn/gunicorn) companion to
`SECURE_PROXY_SSL_HEADER`: it tells the server to trust `X-Forwarded-*` headers
(client IP, scheme) from **any** upstream. It has the same trust-boundary
problem as the settings-level header trust — gating one without the other leaves
the no-proxy bake trusting spoofable forwarded headers on its `127.0.0.1:8000`
port. Gate it on the same condition as Step 2:

```yaml
    environment:
      DJANGO_ENV: prod
{%- if cookiecutter.use_traefik == "yes" or cookiecutter.behind_proxy == "yes" %}
      FORWARDED_ALLOW_IPS: "*"
{%- endif %}
```

When the gate is false the line is omitted entirely, so the ASGI server falls
back to its safe default (trust only `127.0.0.1`).

**Verify**:
```
uvx cookiecutter . --no-input -o /tmp/bake-np use_traefik=no behind_proxy=no
grep -c "FORWARDED_ALLOW_IPS" /tmp/bake-np/my-project/.docker/compose/prod.yaml
```
→ `0`. Default bake and `use_traefik=yes behind_proxy=no` bake → `1`. Confirm
the rendered `environment:` block still has valid YAML indentation in both
states (the `DJANGO_ENV: prod` line must always remain).

### Step 6: Add a CI bake-matrix case for the no-proxy mode

In the repo-root `.github/workflows/ci.yaml`, in the `bake` job's
`strategy.matrix.include` list, add one case (keep the list alphabetized by
`case:` — insert after `minimal`, before `smtp`):

```yaml
          - case: no-proxy
            project_name: My Project
            extra-args: use_traefik=no behind_proxy=no
            slug: my-project
```

Note that this bake's baked pytest and pre-commit still run (they don't depend
on the HTTPS block). Do NOT add this case to the `docker-compose-smoke` job.

**Verify**: `uvx actionlint .github/workflows/ci.yaml` (or the repo-root
`uvx pre-commit run actionlint --all-files`) exits 0.

### Step 7: Document the knob

In `{{cookiecutter.project_slug}}/README.md`, in the Design Decisions and/or
Production section, add a short paragraph: the template trusts
`X-Forwarded-Proto` only behind a proxy; `behind_proxy=yes` (default, and
implied by `use_traefik=yes`) enables full HTTPS enforcement; `behind_proxy=no`
is for internal/private-network deployments served over plain HTTP and disables
SSL redirect, HSTS, secure cookies, and the proxy-header trust.

**Verify**: repo-root `uvx pre-commit run markdownlint --all-files` exits 0.

## Test plan

- No new pytest test is strictly required (settings-only change; the suite runs
  under `DJANGO_ENV=ci`, not `prod`, so `prod.py` is coverage-omitted per
  `pyproject.toml`). Do **not** add a test that only asserts configuration
  values — `AGENTS.md` forbids it.
- Verification is the multi-bake grep matrix (Step 2), the byte-identity check
  (Step 3), and the deploy check (Step 5).
- Run the full baked suite on the default and no-proxy bakes to prove nothing
  else broke (needs a running `postgres:18.4`):
  `DATABASE_URL=postgres://postgres:postgres@localhost:5432/postgres uv run pytest`
  → all pass, 100% coverage.

## Done criteria

ALL must hold:

- [ ] `cookiecutter.json` has a `behind_proxy` key (default `yes`) and a `__prompts__` entry; `json.load` succeeds.
- [ ] Default bake and `use_traefik=yes behind_proxy=no` bake: `grep -c SECURE_PROXY_SSL_HEADER prod.py` == 1.
- [ ] `use_traefik=no behind_proxy=no` bake: `grep -c SECURE_PROXY_SSL_HEADER prod.py` == 0, and `grep -c "SECURE_SSL_REDIRECT\|SESSION_COOKIE_SECURE\|SECURE_HSTS_SECONDS\|CSRF_COOKIE_SECURE" prod.py` == 0 (all four gated names absent).
- [ ] `FORWARDED_ALLOW_IPS` gating (Step 5b): default bake and `use_traefik=yes behind_proxy=no` bake → `grep -c FORWARDED_ALLOW_IPS prod.yaml` == 1; `use_traefik=no behind_proxy=no` bake → == 0. Rendered `environment:` block is valid YAML in all three.
- [ ] Default bake `prod.py` is byte-identical to the pre-edit rendered snapshot (Step 3).
- [ ] Default bake deploy security check exits 0; baked pytest 100% pass; baked pre-commit exit 0.
- [ ] `.github/workflows/ci.yaml` has the `no-proxy` matrix case and actionlint passes.
- [ ] README documents the knob.
- [ ] No out-of-scope files modified (`git status`); no hook edited.
- [ ] `plans/README.md` status row updated.

## STOP conditions

Stop and report (do not improvise) if:

- The "Design decision" intent (whether a plain-HTTP prod mode should exist)
  cannot be confirmed.
- The live `prod.py` no longer matches the "Current state" excerpt.
- Gating the cookie/redirect settings would require touching `dev.py`/`ci.py`
  or a component file (it should not).
- The default (`behind_proxy=yes`) render is NOT byte-identical to the
  pre-edit rendered snapshot (Step 3).
- Making `deploy-check.sh` pass for the no-proxy bake would require weakening
  the security gate for the default proxied deployment.

## Maintenance notes

- **Alternative design considered**: gating purely on `use_traefik` (no new
  knob). Rejected because `use_traefik=no` legitimately includes operators who
  run their *own* TLS-terminating proxy that sets `X-Forwarded-Proto` and must
  keep the header trust; a dedicated `behind_proxy` knob expresses the real
  invariant precisely.
- **Branch-protection follow-up**: the new `no-proxy` bake matrix case creates a
  new required status check ("Bake no-proxy"). If CI runs on a protected branch,
  the repo owner must add it to the required-checks list (this repo's history
  shows that convention: commit `60b1aab`).
- Reviewer should scrutinize that the **default** (proxied) deployment is
  byte-for-byte unchanged and still passes `check --deploy --tag=security`, and
  that no `Secure`/HSTS/redirect setting leaked out of the gate for the default.
- If a future runtime change makes gunicorn terminate TLS directly, revisit the
  gate — the "app always sees plain HTTP" assumption would no longer hold.
