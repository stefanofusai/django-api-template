# Plan 007: Make `use_csp=yes` real — self-hosted Swagger + drop `unsafe-inline` from `script-src`

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving to the
> next step. This plan applies template edits AND keeps a live browser gate
> (Step 6) that is expected to PASS; if any unexpected CSP violation appears,
> roll back the edits and report precisely (see "Rollback"). Do NOT try to
> silence violations by overriding vendored unfold/ninja templates — that is a
> STOP condition. When done, update the status row for this plan in
> `plans/README.md` — unless a reviewer dispatched you and told you they
> maintain the index.
>
> **Drift check (run first)**:
> `git diff --stat 16a12b3..HEAD -- '{{cookiecutter.project_slug}}/src/config/settings/components/apps.py' '{{cookiecutter.project_slug}}/src/config/settings/components/csp.py' '{{cookiecutter.project_slug}}/tests/api/integration/csp_test.py' 'README.md' '{{cookiecutter.project_slug}}/README.md' 'cookiecutter.json'`
> If any in-scope file changed since this plan was written, compare the
> "Current state" excerpts against the live code before proceeding; on a
> mismatch, treat it as a STOP condition.

## Status

- **Priority**: P2
- **Effort**: M
- **Risk**: MED (the change is verified safe; the residual risk is the browser
  gate and an executor forcing it green by editing vendored templates)
- **Depends on**: none
- **Category**: security / fix
- **Planned at**: commit `16a12b3`, 2026-07-09

## Why this matters

`use_csp=yes` ships broken today, and not in a way the header inspection or the
existing tests catch. In a browser, both surfaces this API-only template
renders are already degraded under the current policy
(`script-src 'self' 'unsafe-inline'`):

- **Swagger docs render blank.** django-ninja serves its *CDN* Swagger template
  (see "Current state"), so `swagger-ui-bundle.js` loads from
  `cdn.jsdelivr.net` — a host the policy does not allow — and the console shows
  `Uncaught ReferenceError: SwaggerUIBundle is not defined`. `/api/docs` and
  `/api/v1/docs` are unusable.
- **The admin chrome is degraded.** django-unfold 0.96 drives its theme
  toggle, sidebar, tabs, and modals with Alpine.js, which evaluates directive
  expressions as JavaScript and therefore needs `script-src 'unsafe-eval'`. The
  current policy has none, so the console fills with ~17 Alpine `EvalError`s and
  those controls don't work.

This plan fixes both and tightens the policy at the same time:

1. Add `"ninja"` to `INSTALLED_APPS` so django-ninja serves its **self-hosted**
   Swagger template (all assets same-origin), which works under a strict
   `script-src` with no CDN and no inline script.
2. Change `script-src` to `[CSP.SELF, CSP.UNSAFE_EVAL]` — **`unsafe-inline`
   removed**, `unsafe-eval` added.

Removing `unsafe-inline` from `script-src` is the real security win: an injected
inline `<script>` no longer executes, which is the primary XSS vector a CSP
exists to stop. Be honest about the residual, though — `unsafe-eval` still
permits `eval()`/`new Function()`, so this is **not** a full `script-src`
lockdown. It is strictly better than the status quo, with one named residual
(`unsafe-eval`, required by unfold 0.96's Alpine). The residual is acceptable
because reaching an eval sink generally requires either injecting a script (now
blocked) or a first-party eval-of-untrusted-input bug, which this template does
not have. When unfold ships an eval-free Alpine build, `unsafe-eval` can be
dropped (Maintenance notes).

**No nonce.** Django 6 emits the CSP nonce into the header *lazily* — only when
a rendered template or view reads `request.csp_nonce`. Neither Django 6's admin
templates, django-unfold 0.96, nor django-ninja's Swagger templates reference
it (verified by grep of the installed packages), so `CSP.NONCE` would never
appear in the header and no inline script would consume it. It would be dead
weight; the self-hosted Swagger template needs no inline script at all.

## Current state

This repo is a **cookiecutter template**; verify by baking (always
single-quote `{{cookiecutter.project_slug}}` paths). This plan supersedes and
re-scopes the former 007 design spike (since removed from `plans/`): the spike
proposed a nonce-based `script-src` gated on both surfaces; browser
verification showed the nonce approach cannot certify (the surfaces were
already broken for reasons orthogonal to inline scripts), so the decision was
revised to the fix in this plan.

Versions in the `use_csp=yes` bake at this commit (from `uv.lock`): Django
`6.0.6`, django-ninja `1.6.2`, django-ninja-extra `0.31.5`, django-unfold
`0.96.0`. `CSP.UNSAFE_EVAL` exists in `django/utils/csp.py`
(`UNSAFE_EVAL = "'unsafe-eval'"`), verified in the bake.

`{{cookiecutter.project_slug}}/src/config/settings/components/csp.py`
(entire file; renders only for `use_csp=yes`, deleted otherwise by the
post-gen hook):

```python
from django.utils.csp import CSP

SECURE_CSP = {
    "default-src": [CSP.SELF],
    "img-src": [CSP.SELF, "data:"],
    "script-src": [CSP.SELF, CSP.UNSAFE_INLINE],
    "style-src": [CSP.SELF, CSP.UNSAFE_INLINE],
}
```

`{{cookiecutter.project_slug}}/src/config/settings/components/apps.py`
third-party block (verbatim, note the alphabetical grouping):

```python
    # Third-party
    "anymail",
    "axes",
    "django_celery_beat",
    "django_celery_results",
    "django_structlog",
    "extra_checks",
    "ninja_extra",
    # Project
```

`"ninja"` is NOT registered — only `"ninja_extra"`. This is exactly what makes
django-ninja fall back to the CDN docs template: `ninja/openapi/docs.py`'s
`render_template` uses the self-hosted `swagger.html` only when
`"ninja" in settings.INSTALLED_APPS`, else it renders `swagger_cdn.html`. Both
`internal_api` (`NinjaAPI`, docs at `/api/docs`) and `v1_api` (`NinjaExtraAPI`,
docs at `/api/v1/docs`) in
`{{cookiecutter.project_slug}}/src/apps/api/api.py` use ninja's default
`Swagger` docs class, so both go through this same gate. **`/api/v1/docs` is
mechanically identical to `/api/docs`** (same `Swagger` class, same
INSTALLED_APPS gate — `NinjaExtraAPI` defaults to `Swagger()`), so verifying one
covers both.

Middleware (`django.middleware.csp.ContentSecurityPolicyMiddleware`) is wired
in `middleware.py:7` after `SecurityMiddleware`, guarded by the same knob (out
of scope).

Tests: `{{cookiecutter.project_slug}}/tests/api/integration/csp_test.py`
asserts the current directive strings appear on `/admin/login/` and the
`internal:openapi-view` response:

```python
EXPECTED_CSP_DIRECTIVES = [
    "default-src 'self'",
    "img-src 'self' data:",
    "script-src 'self' 'unsafe-inline'",
    "style-src 'self' 'unsafe-inline'",
]
```

Doc mentions (record line numbers before editing): `README.md:101` (the
`use_csp` Variables-table row — carries the false "allows inline scripts and
styles"), the What-You-Get bullet at `README.md:27` ("Optional Django native
Content Security Policy for browser-rendered surfaces" — already accurate, no
inline-scripts claim; verify, don't force a reword),
`{{cookiecutter.project_slug}}/README.md:253-255` (the CSP paragraph), and
`cookiecutter.json:81` (the `use_csp` `"yes"` prompt).

### Header behavior verified in a booted `use_csp=yes use_example_api=yes` bake

Current header on every surface (`/api/docs`, `/admin/login/`, `/api/health`):

```
Content-Security-Policy: default-src 'self'; img-src 'self' data:; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'
```

After the two edits (add `"ninja"`; `script-src = [CSP.SELF, CSP.UNSAFE_EVAL]`),
the header on ALL surfaces is deterministic and byte-identical (no nonce):

```
Content-Security-Policy: default-src 'self'; img-src 'self' data:; script-src 'self' 'unsafe-eval'; style-src 'self' 'unsafe-inline'
```

### Before/after browser violation inventory (this is the gate evidence)

Loaded in Chrome with DevTools console open in the bake:

| Surface | BEFORE (current policy) | AFTER (this plan's edits) |
|---------|-------------------------|---------------------------|
| `/api/docs` (== `/api/v1/docs`) | CDN `swagger-ui-bundle.js` blocked by `script-src` → `SwaggerUIBundle is not defined`; CDN `swagger-ui.css` blocked by `style-src`; `django-ninja.dev` favicons blocked by `img-src`. Blank page. | Swagger UI renders; endpoints expandable; "Try it out" → Execute returns `200 {"status": "ok"}`. **Zero CSP violations.** |
| `/admin/` (login, notes changelist, add-note form) | ~17 Alpine `Expression Error` / `EvalError` (`unsafe-eval` not allowed); theme/sidebar/modals dead. | Alpine chrome works; **zero CSP violations** (only unrelated non-CSP notices: an "unload event listener deprecated" warning from Django's `RelatedObjectLookups.js`, and one a11y form-field warning). |

After self-hosting, the docs favicons are served from `{% static 'ninja/favicon.svg' %}`
(same-origin), so the `img-src` favicon violation is gone too — no docs
violation survives.

### Static assets: dev and prod

The self-hosted `swagger.html` references only same-origin assets:
`{% static 'ninja/swagger-ui.css' %}`, two `<script src="{% static 'ninja/...' %}">`
(`swagger-ui-bundle.js`, `swagger-ui-init.js`), same-origin favicons, and a
single non-executable `<script type="application/json" id="swagger-settings">`
data island (CSP does not govern non-executable script types).

- **Dev**: `runserver_plus` serves static from source via the staticfiles app;
  with `"ninja"` in `INSTALLED_APPS`, `AppDirectoriesFinder` serves
  `/static/ninja/...`. Verified: the served `/api/docs` HTML points at
  `/static/ninja/swagger-ui-bundle.js` (not jsdelivr) and the bundle loads.
- **Prod**: `.docker/Dockerfile` runs `collectstatic` at build time and
  WhiteNoise (`CompressedManifestStaticFilesStorage`) serves the collected,
  hashed files from the app's own origin. Verified in the bake: prod-settings
  `collectstatic --no-input` exits 0 with `"ninja"` added, and ninja's assets
  are collected and hashed under `staticfiles/ninja/` (`swagger-ui-bundle.js`,
  `swagger-ui.css`, `favicon.svg/png`). collectstatic printed
  "2 skipped due to conflict" — non-fatal (exit 0); the swagger assets are
  namespaced under `ninja/` and are unaffected. Because WhiteNoise serves these
  from the same origin under `/static/`, the CSP semantics in prod are
  origin-identical to the dev gate — **no separate prod boot is owed**; the dev
  browser gate plus the collectstatic check covers it.

### Dev stack reload behavior

`{{cookiecutter.project_slug}}/.docker/compose/dev.yaml` bind-mounts
`../../src:/app/src` (line 38), so editing the baked `apps.py`/`csp.py` and
running `docker compose ... restart api` picks them up — no image rebuild.

## Commands you will need

Run inside the bake (`/tmp/verify-007/my-project`). If host port `5432` is
occupied on your machine, add an override that remaps only the Postgres
*published* port (used solely by host-run pytest; the api reaches Postgres over
the compose network) and pass it as a second `-f`; this is an environment
workaround, not part of the deliverable.

| Purpose | Command | Expected on success |
|---------|---------|---------------------|
| Bake | `uvx cookiecutter . -o /tmp/verify-007 --no-input use_csp=yes use_example_api=yes` | project at `/tmp/verify-007/my-project` |
| Boot dev stack | `cp .env.example .env && docker compose -f .docker/compose/dev.yaml --env-file=.env up -d --build --wait` | all services healthy; api on :8000 |
| Create staff user | `docker compose -f .docker/compose/dev.yaml --env-file=.env exec -e DJANGO_SUPERUSER_PASSWORD=Admin12345! api python manage.py createsuperuser --no-input --username=admin --email=admin@example.test` | `Superuser created successfully.` |
| CSP header probe | `curl -s -D - -o /dev/null http://localhost:8000/api/docs \| grep -i content-security-policy` | the header line |
| Docs template probe | `curl -fsS http://localhost:8000/api/docs \| grep -iE '/static/ninja\|jsdelivr'` | `/static/ninja/...` refs, NO jsdelivr |
| Restart api after edits | `docker compose -f .docker/compose/dev.yaml --env-file=.env restart api` | api restarts; header reflects edits |
| Prod collectstatic check | run `.venv/bin/python manage.py collectstatic --no-input` with the Dockerfile's mock prod env (`DJANGO_ENV=prod`, `PYTHONPATH=src`, and the mock `SECRET_KEY`/`DATABASE_URL`/`REDIS_PASSWORD`/… from `.docker/Dockerfile`) after `uv sync --locked --group prod` | exit 0; `staticfiles/ninja/` populated |
| Suite (in bake) | `uv sync --locked && uv run pytest` | all pass |
| Ruff (repo root) | `uvx ruff@0.15.16 format --check . && uvx ruff@0.15.16 check .` | exit 0 |
| Teardown | `docker compose -f .docker/compose/dev.yaml --env-file=.env down -v` | volumes/network removed |

Manual browser verification is REQUIRED for the gate (Step 6): load `/admin/`
and `/api/docs` with the DevTools console open. `curl` proves which template is
served and the header shape, but cannot prove absence of runtime violations.

## Scope

**In scope**:

- `{{cookiecutter.project_slug}}/src/config/settings/components/apps.py`
  (add `"ninja"` to the third-party block)
- `{{cookiecutter.project_slug}}/src/config/settings/components/csp.py`
- `{{cookiecutter.project_slug}}/tests/api/integration/csp_test.py`
- `README.md` (root — the `use_csp` Variables row at line 101; the
  What-You-Get bullet at line 27 is already accurate, verify only)
- `{{cookiecutter.project_slug}}/README.md` (the CSP paragraph, lines 253-255)
- `cookiecutter.json` (the `use_csp` `"yes"` prompt, line 81)

**Out of scope** (do NOT touch):

- `style-src` — stays `'self' 'unsafe-inline'`; inline styles are pervasive in
  both surfaces and style injection is far lower risk than script injection.
- Any vendored template overrides for unfold or django-ninja. If clearing a
  violation appears to need one, that is a gate FAILURE — report, don't fork.
- The CSP middleware wiring/order (`middleware.py`).

## Git workflow

- Branch: `advisor/007-nonce-csp`.
- Conventional commits: a single
  `feat: self-host Swagger and drop unsafe-inline from the CSP script-src`
  covering all six files.
- Do NOT push or open a PR unless the operator instructed it.

## Steps

### Step 1: Bake, boot, capture baseline

Bake with `use_csp=yes use_example_api=yes`, boot the dev stack, create the
staff user. Record the current header on `/api/docs`, `/admin/login/`,
`/api/health`, and confirm `/api/docs` is CDN-served
(`curl ... | grep jsdelivr` matches).

**Verify**: header matches the current-policy string in "Current state";
`/api/docs` HTML contains `cdn.jsdelivr.net`.

### Step 2: Capture the baseline browser violations

With the console open, load `/api/docs` and `/admin/login/`, then log in and
open the notes changelist. Record the violations — you should see the
`SwaggerUIBundle is not defined` / CDN blocks on docs and the ~17 Alpine
`EvalError`s on admin (the BEFORE column).

**Verify**: baseline violation set recorded, matching "Current state". This is
the reference so post-edit you can tell pre-existing-fixed from newly-introduced.

### Step 3: Apply the two settings edits to the BAKED copy

- `apps.py`: add `"ninja"` to the third-party block, immediately before
  `"ninja_extra"` (keeps the block's alphabetical grouping). Unconditional — no
  Jinja guard: ninja is always installed (a dependency of ninja-extra) and both
  APIs exist for every knob combination.
- `csp.py`: set `"script-src": [CSP.SELF, CSP.UNSAFE_EVAL],` (keep every other
  directive identical; `style-src` unchanged).

Then `docker compose -f .docker/compose/dev.yaml --env-file=.env restart api`.

**Verify**:
- `curl -s -D - -o /dev/null http://localhost:8000/api/docs | grep -i content-security-policy`
  shows exactly
  `default-src 'self'; img-src 'self' data:; script-src 'self' 'unsafe-eval'; style-src 'self' 'unsafe-inline'`.
- `curl -fsS http://localhost:8000/api/docs | grep -iE '/static/ninja|jsdelivr'`
  shows `/static/ninja/...` and NO jsdelivr.

### Step 4: Update the test assertions

Rewrite `csp_test.py`. The header is now nonce-free and fully deterministic, so
the strongest, simplest assertion is **full-string equality** against the
expected header — this proves both that the new directives are present AND that
nothing extra (notably `'unsafe-inline'` on `script-src`) is appended:

```python
EXPECTED_CSP = (
    "default-src 'self'; img-src 'self' data:; "
    "script-src 'self' 'unsafe-eval'; style-src 'self' 'unsafe-inline'"
)
```

Assert `response.headers["Content-Security-Policy"] == EXPECTED_CSP` on both an
admin response (`/admin/login/`) and a docs response
(`reverse("internal:openapi-view")`), keeping the two existing test functions'
shape. If you prefer the directive-list style for file consistency, keep it but
ADD an explicit `assert "'unsafe-inline'" not in <the script-src directive>` —
`all(directive in policy)` alone would pass even if `unsafe-inline` were
appended, which does not encode the negative this change is about.

**Verify**: `uv sync --locked && uv run pytest` — all pass (csp_test.py
included).

### Step 5: Update the doc wording

All three surfaces must become true: the policy now blocks inline SCRIPTS,
allows inline STYLES only, and Swagger genuinely works. Draft replacements:

- `README.md:101` (Variables row) →
  `| \`use_csp\` | \`no\` | Enable Django native CSP headers: \`script-src\` blocks inline scripts (self-hosted Swagger UI, \`unsafe-eval\` retained for the admin theme); inline styles are still allowed. |`
- `README.md:27` What-You-Get bullet → already accurate ("Optional Django
  native Content Security Policy for browser-rendered surfaces"); confirm it
  carries no stale inline-scripts claim and leave it unless you want a light
  refresh.
- `{{cookiecutter.project_slug}}/README.md:253-255` → replace
  "The starter policy is compatible with Swagger UI and intentionally allows
  inline scripts and styles." with e.g. "The starter policy blocks inline
  scripts — Swagger UI is served from self-hosted static assets, and
  `unsafe-eval` is retained because the django-unfold admin theme requires it —
  while still allowing inline styles."
- `cookiecutter.json:81` (`use_csp` `"yes"` prompt) → replace
  "Enable a Swagger-compatible starter CSP for browser-rendered surfaces" with
  e.g. "Enable a starter CSP that blocks inline scripts across browser-rendered
  surfaces".

**Verify**: `grep -rn "unsafe-inline\|Swagger-compatible\|allows inline scripts"`
across the four doc locations returns nothing stale.

### Step 6: DECISION GATE — live browser trial (expected to PASS)

With the console open:
- `/api/docs`: confirm Swagger UI renders (endpoints listed), expand the health
  operation, click "Try it out" → "Execute", confirm a `200 {"status": "ok"}`
  response. Zero CSP violations. (This also covers `/api/v1/docs` — mechanically
  identical.)
- `/admin/`: log in, open the notes changelist and the add-note form, exercise
  the theme toggle / sidebar. Zero CSP violations (unrelated non-CSP notices
  like the unload-deprecation warning are fine — see "Current state").

**Gate passes** iff zero CSP violations on both surfaces and both are fully
functional (this matches the planning trial). 

**Rollback**: if any CSP violation appears, revert all edits (`git checkout` the
in-scope files / discard the branch), record the exact violation (surface,
blocked resource, source), and report — do NOT edit vendored templates to
silence it (STOP condition).

### Step 7: Final verification on fresh bakes and report

- Fresh `use_csp=yes use_example_api=yes` and `use_csp=yes use_cors=yes` bakes:
  `uv sync --locked && uv run pytest` all pass; run the prod collectstatic
  check (Commands table) → exit 0.
- `uvx ruff@0.15.16 format --check . && uvx ruff@0.15.16 check .` exit 0 at repo
  root (the format gate bakes `use_csp=yes` — see `scripts/check_generated_format.py`).
- Repeat the Step 6 browser trial once on the final bake.
- Record the outcome in the completion report and the `plans/README.md` status
  row.

## Test plan

The rewritten `csp_test.py` asserts the exact post-change header on both an
admin response and a docs response — which simultaneously proves the new
`script-src 'self' 'unsafe-eval'` is present, `unsafe-inline` is absent from
`script-src`, and `style-src` still carries `'self' 'unsafe-inline'`. The
browser gate (Step 6) is the runtime-execution check that headers cannot give:
Swagger actually renders and the admin Alpine chrome actually works. No nonce
assertion exists by design (Django emits none on these surfaces).

## Done criteria

- [ ] Step 6 browser trial clean on both surfaces, with evidence (Swagger
  renders + try-it-out `200`; admin Alpine works; zero CSP violations).
- [ ] `apps.py` registers `"ninja"`; `csp.py` uses `[CSP.SELF, CSP.UNSAFE_EVAL]`.
- [ ] `csp_test.py` asserts the exact new header (proving `unsafe-inline` absent
  from `script-src`); both bakes green (`pytest`), prod collectstatic exit 0.
- [ ] Doc wording updated in `README.md:101`, the generated README, and
  `cookiecutter.json` (README.md:27 verified accurate); no stale
  "unsafe-inline"/"Swagger-compatible"/"allows inline scripts" left in scope.
- [ ] Root ruff format+check exit 0.
- [ ] `git status` clean outside the six in-scope files.
- [ ] Bake torn down (`down -v`), `/tmp/verify-007` removed.
- [ ] `plans/README.md` status row updated to DONE (policy fixed and tightened).

## STOP conditions

Stop and report back if:

- You cannot perform or delegate the browser verification — `curl`-only evidence
  is insufficient for the gate.
- The Step 6 gate shows any CSP violation that clearing would require overriding
  an unfold/ninja template — report and let the maintainer decide; do NOT fork a
  template.
- Your baseline (Step 2) does NOT reproduce the "Current state" violations (e.g.
  Swagger already renders, or admin Alpine works) — dependency versions or
  vendored templates changed since planning; re-verify "Current state" first.
- The dev stack fails to boot for reasons unrelated to CSP (e.g. an
  unresolvable host port conflict) — pre-existing issue; report.
- `collectstatic` exits non-zero with `"ninja"` added (would indicate a
  manifest/asset problem this plan did not see) — report before shipping.

## Maintenance notes

- **`unsafe-eval` is a named, temporary residual.** It exists only because
  django-unfold 0.96's Alpine.js evaluates directive expressions at runtime.
  When unfold ships an eval-free Alpine build (or nonce-aware templates), drop
  `unsafe-eval` and re-run the Step 6 admin gate — that would make `script-src`
  a full `'self'` lockdown. Watch the unfold changelog; a Dependabot bump could
  also silently change this, and the csp test asserts header shape, not runtime
  execution, so the residual detection risk is accepted and documented here.
- **Why `"ninja"` in `INSTALLED_APPS` is the fix, not a template override.**
  It flips django-ninja's own `render_template` from the CDN fallback to its
  self-hosted `swagger.html`; no vendored file is touched. If a future
  django-ninja release changes this gate, re-verify the docs surface.
- Future template additions that render HTML must not introduce inline
  executable `<script>` blocks (they would be blocked by `script-src 'self'`);
  use external same-origin scripts or, if an inline script becomes truly
  necessary, revisit the nonce approach (a template consuming `request.csp_nonce`
  is what makes Django emit the nonce token).
