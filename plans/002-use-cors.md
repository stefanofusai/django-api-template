# Plan 002: Add project-level `use_cors`

> **For agentic workers:** REQUIRED SUB-SKILL: Use
> superpowers:subagent-driven-development (recommended) or
> superpowers:executing-plans to implement this plan task-by-task. Steps use
> checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an opt-in CORS configuration for browser clients without enabling
permissive cross-origin access by default.

**Architecture:** Add `use_cors = ["no", "yes"]`. When enabled, include
`django-cors-headers==4.9.0`, add `corsheaders` and `CorsMiddleware`, read
`CORS_ALLOWED_ORIGINS` from the environment, and test allowed and disallowed
origins. Disabled bakes contain no CORS dependency or settings.

**Tech Stack:** Cookiecutter, django-cors-headers 4.9.0, Django middleware,
pytest, uv, pre-commit.

---

## Status

- **Priority**: P1
- **Effort**: M
- **Risk**: MED
- **Depends on**: none
- **Category**: direction
- **Planned at**: commit `9d129c1`, 2026-07-08

## Current Dependency Evidence

PyPI lists `django-cors-headers` 4.9.0, released September 18, 2025. Its metadata
supports Python 3.9 through 3.14 and Django 4.2 through 6.0. Its documentation
requires `CorsMiddleware` before middleware that can generate responses, such as
`CommonMiddleware`.

## Drift Check

```shell
git diff --stat 9d129c1..HEAD -- cookiecutter.json "{{cookiecutter.project_slug}}/pyproject.toml" "{{cookiecutter.project_slug}}/.env.example" "{{cookiecutter.project_slug}}/src/config/settings/components/apps.py" "{{cookiecutter.project_slug}}/src/config/settings/components/middleware.py"
```

Stop if the settings layout has changed.

## Scope

**In scope**:
- `cookiecutter.json`
- `.github/workflows/ci.yaml`
- `README.md`
- `{{cookiecutter.project_slug}}/README.md`
- `{{cookiecutter.project_slug}}/.env.example`
- `{{cookiecutter.project_slug}}/pyproject.toml`
- `{{cookiecutter.project_slug}}/src/config/settings/components/apps.py`
- `{{cookiecutter.project_slug}}/src/config/settings/components/core.py`
- `{{cookiecutter.project_slug}}/src/config/settings/components/middleware.py`
- `{{cookiecutter.project_slug}}/tests/config/unit/prod_settings_test.py`
- `{{cookiecutter.project_slug}}/tests/api/integration/cors_test.py` (create)

**Out of scope**:
- `CORS_ALLOW_ALL_ORIGINS=True`
- regex origin configuration
- database-backed origin policy
- tying CORS to `api_auth` or `use_example_api`

## Steps

### Task 1: Add the knob and dependency

- [ ] Add `use_cors = ["no", "yes"]` to `cookiecutter.json`, default `no`.
- [ ] Add prompt text explaining that `yes` enables explicit browser origins.
- [ ] In `pyproject.toml`, add:

```toml
{%- if cookiecutter.use_cors == "yes" %}
    "django-cors-headers==4.9.0",
{%- endif %}
```

- [ ] Verify:

```shell
rtk uvx cookiecutter . -o /tmp/bake-cors-default --no-input
rtk uvx cookiecutter . -o /tmp/bake-cors-enabled --no-input use_cors=yes
```

Expected: both bakes succeed; only enabled bake has `django-cors-headers`.

### Task 2: Add app and middleware only when enabled

- [ ] In `components/apps.py`, add `"corsheaders"` under the `use_cors=yes`
      gate.
- [ ] In `components/middleware.py`, add the middleware before
      `SecurityMiddleware`:

```python
{%- if cookiecutter.use_cors == "yes" %}
    "corsheaders.middleware.CorsMiddleware",
{%- endif %}
    "django.middleware.security.SecurityMiddleware",
```

- [ ] Verify in enabled bake:

```shell
rtk uv run python manage.py check
```

Expected: exit 0.

### Task 3: Add explicit origin settings

- [ ] In `components/core.py`, add under the CORS gate:

```python
CORS_ALLOWED_ORIGINS = env.list("CORS_ALLOWED_ORIGINS")
CORS_ALLOW_CREDENTIALS = env.bool("CORS_ALLOW_CREDENTIALS", default=False)
```

- [ ] In `.env.example`, add a `# Browser clients/CORS` block only when
      `use_cors=yes`:

```dotenv
# Comma-separated browser origins allowed to call this API cross-origin.
CORS_ALLOWED_ORIGINS=https://app.{{ cookiecutter.domain_name }}
# Optional cross-origin cookie/header credential support.
# CORS_ALLOW_CREDENTIALS=False
```

- [ ] Keep env keys alphabetized inside the block.

### Task 4: Add production safety checks

- [ ] In `tests/config/unit/prod_settings_test.py`, add tests that production
      with `use_cors=yes` rejects empty `CORS_ALLOWED_ORIGINS`.
- [ ] Add the matching boot guard in the production settings/check path already
      used for `SECRET_KEY`, `ALLOWED_HOSTS`, and required provider settings.
- [ ] Do not reject localhost origins in dev or ci.

**Verify**:

```shell
rtk uv run pytest --no-cov tests/config/unit/prod_settings_test.py
```

Expected: prod settings tests pass.

### Task 5: Add CORS behavior tests

- [ ] Create `tests/api/integration/cors_test.py` under the CORS gate.
- [ ] Test an allowed origin:

```python
response = client.get("/api/health", headers={"origin": "https://app.example.com"})
assert response.headers["access-control-allow-origin"] == "https://app.example.com"
```

- [ ] Test a disallowed origin does not receive the allow-origin header.
- [ ] Test an `OPTIONS` preflight to `/api/v1/` returns CORS headers for an
      allowed origin.

**Verify**:

```shell
rtk uv run pytest --no-cov tests/api/integration/cors_test.py
```

Expected: CORS tests pass.

### Task 6: Document and add CI coverage

- [ ] Update README feature list and variable table.
- [ ] Add a CI bake case:

```yaml
- case: cors
  project_name: My Project
  extra-args: use_cors=yes
  slug: my-project
```

- [ ] Keep matrix cases sorted alphabetically by `case`.

## Test Plan

- Default bake: no CORS dependency, no CORS settings, full tests pass.
- `use_cors=yes`: CORS dependency is present, middleware order is correct,
  allowed/disallowed/preflight tests pass, generated pre-commit passes.

## Done Criteria

- [ ] `use_cors` defaults to `no`.
- [ ] Enabled bakes use `django-cors-headers==4.9.0`.
- [ ] Disabled bakes contain no `corsheaders` references.
- [ ] Production refuses enabled CORS with no allowed origins.
- [ ] CORS behavior tests cover allowed, disallowed, and preflight requests.
- [ ] Root and generated checks pass.

## STOP Conditions

- `django-cors-headers==4.9.0` fails under Django 6/Python 3.14 in a bake.
- Safe behavior requires wildcard origins.
- Middleware ordering conflicts with existing request logging or security
  middleware.

## Maintenance Notes

CORS and CSRF are separate. Do not auto-copy CORS origins into
`CSRF_TRUSTED_ORIGINS`; document that cross-origin session writes need deliberate
CSRF configuration.
