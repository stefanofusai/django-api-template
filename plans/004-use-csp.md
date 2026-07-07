# Plan 004: Add project-level `use_csp` with Django native CSP

> **For agentic workers:** REQUIRED SUB-SKILL: Use
> superpowers:subagent-driven-development (recommended) or
> superpowers:executing-plans to implement this plan task-by-task. Steps use
> checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an opt-in Content Security Policy for generated browser surfaces
without adding a third-party CSP dependency.

**Architecture:** Add `use_csp = ["no", "yes"]`. When enabled, use Django 6's
native `ContentSecurityPolicyMiddleware` and `SECURE_CSP` settings. Apply a
Swagger-compatible starter policy to admin and API docs, with tests asserting
headers are emitted. Keep the default disabled.

**Tech Stack:** Django 6 native CSP, Django middleware, pytest, uv, pre-commit.

---

## Status

- **Priority**: P3
- **Effort**: M
- **Risk**: MED
- **Depends on**: none
- **Category**: direction
- **Planned at**: commit `9d129c1`, 2026-07-08

## Current Dependency Evidence

Django 6 introduced native CSP support. The docs describe
`ContentSecurityPolicyMiddleware`, `SECURE_CSP`, `SECURE_CSP_REPORT_ONLY`, CSP
constants, and decorators. `django-csp` 4.0 is older and its PyPI classifiers do
not list Django 6 or Python 3.14, so this plan uses Django native CSP.

## Drift Check

```shell
git diff --stat 9d129c1..HEAD -- cookiecutter.json "{{cookiecutter.project_slug}}/src/config/settings/components/middleware.py" "{{cookiecutter.project_slug}}/src/config/settings/components/core.py" "{{cookiecutter.project_slug}}/src/apps/api/docs.py" "{{cookiecutter.project_slug}}/pyproject.toml"
```

Stop if middleware or docs access changed substantially.

## Scope

**In scope**:
- `cookiecutter.json`
- `.github/workflows/ci.yaml`
- `README.md`
- `{{cookiecutter.project_slug}}/README.md`
- `{{cookiecutter.project_slug}}/src/config/settings/components/core.py`
- `{{cookiecutter.project_slug}}/src/config/settings/components/middleware.py`
- `{{cookiecutter.project_slug}}/tests/api/integration/csp_test.py` (create)
- `{{cookiecutter.project_slug}}/tests/config/unit/prod_settings_test.py`

**Out of scope**:
- `django-csp` dependency.
- CSP report collection endpoints.
- Strict no-inline CSP for Swagger UI.
- Per-tenant or database-configured CSP.

## Steps

### Task 1: Add the knob

- [ ] Add `use_csp = ["no", "yes"]`, default `no`.
- [ ] Add prompt text: `yes` enables Django native CSP for browser-rendered
      surfaces.
- [ ] Verify default bake succeeds and has no CSP middleware.

### Task 2: Add Django native middleware and policy

- [ ] In `components/middleware.py`, add under the CSP gate after
      `SecurityMiddleware`:

```python
"django.middleware.csp.ContentSecurityPolicyMiddleware",
```

- [ ] In `components/core.py`, add:

```python
from django.utils.csp import CSP

SECURE_CSP = {
    "default-src": [CSP.SELF],
    "img-src": [CSP.SELF, "data:"],
    "script-src": [CSP.SELF, CSP.UNSAFE_INLINE],
    "style-src": [CSP.SELF, CSP.UNSAFE_INLINE],
}
```

- [ ] Keep imports alphabetized and Jinja-valid.

### Task 3: Add header tests

- [ ] Create `tests/api/integration/csp_test.py` under the CSP gate.
- [ ] Test `/api/docs` returns `Content-Security-Policy`.
- [ ] Test `/admin/login/` returns `Content-Security-Policy`.
- [ ] Assert the header includes `default-src 'self'`, `img-src 'self' data:`,
      `script-src 'self' 'unsafe-inline'`, and
      `style-src 'self' 'unsafe-inline'`.
- [ ] Verify:

```shell
rtk uv run pytest --no-cov tests/api/integration/csp_test.py
```

Expected: CSP tests pass.

### Task 4: Confirm disabled render

- [ ] Bake with default settings.
- [ ] Confirm no `SECURE_CSP` setting, no CSP middleware, and no CSP tests
      remain.
- [ ] Verify:

```shell
rtk uv run pytest
```

Expected: full generated suite passes.

### Task 5: Document and add CI coverage

- [ ] Update README feature list and variable table.
- [ ] Document that the policy is Swagger-compatible and intentionally allows
      inline scripts/styles.
- [ ] Add CI bake case:

```yaml
- case: csp
  project_name: My Project
  extra-args: use_csp=yes
  slug: my-project
```

- [ ] Keep matrix cases sorted by `case`.

## Test Plan

- Default bake: no CSP code, full tests and pre-commit pass.
- `use_csp=yes`: CSP header tests pass, full tests pass, pre-commit passes.
- Smoke docs manually if practical: run dev server and load `/api/docs` to
  confirm Swagger UI renders with the starter policy.

## Done Criteria

- [ ] `use_csp` defaults to `no`.
- [ ] Enabled bakes use Django native CSP, not `django-csp`.
- [ ] CSP headers are emitted for API docs and admin login.
- [ ] The policy is documented as a starter policy with inline allowances.
- [ ] Root and generated checks pass.

## STOP Conditions

- Django's native CSP middleware path differs from the documented
  `django.middleware.csp.ContentSecurityPolicyMiddleware`.
- Swagger UI cannot render with the planned starter policy.
- CSP requires a third-party dependency to pass tests.

## Maintenance Notes

CSP is not CORS. Keep plan 002 and this plan independent. If future frontend
assets remove inline script/style requirements, tighten this policy in a later
plan rather than expanding this first implementation.
