# Plan 009: Pin django-axes protection on the JWT token endpoint

> **Executor instructions**: This is a characterization-test plan, not a new
> authentication implementation. Run every gate and update the index.
>
> **Drift check (run first)**: `rtk git diff --stat b367191..HEAD -- '{{cookiecutter.project_slug}}/src/apps/api/api.py' '{{cookiecutter.project_slug}}/tests/api/integration/jwt_test.py' '{{cookiecutter.project_slug}}/tests/core/integration/axes_test.py'`

## Status

- **Priority**: P2
- **Effort**: S
- **Risk**: LOW
- **Depends on**: none
- **Category**: security, tests
- **Planned at**: commit `b367191`, 2026-07-10

## Why this matters

Prior source inspection established that django-ninja-jwt passes the request
through Django authentication and django-axes protects `/token/pair`, but the
generated suite pins lockout behavior only for `/admin/login/`. A dependency
upgrade could remove the JWT integration without any local regression test.
This plan proves the existing security behavior; it must not claim the endpoint
is currently unlimited.

## Current state

- `api.py:37-38` registers `NinjaJWTDefaultController` and blacklist routes.
- `axes_test.py` covers repeated admin login failures.
- `jwt_test.py` covers token issuance/refresh/blacklist but no failure-limit
  behavior.
- Tests use cache-backed Axes and clear shared cache through existing fixtures.

## Commands you will need

| Purpose | Command | Expected |
|---|---|---|
| Bake | `rtk uvx cookiecutter . -o /tmp/plan-009 --no-input use_example_api=yes api_auth=jwt` | created |
| Focused | `rtk uv run pytest tests/api/integration/jwt_test.py -q` | pass |
| Full | `rtk uv run pytest` | pass, coverage 100% |

## Scope

**In scope**:
- `{{cookiecutter.project_slug}}/tests/api/integration/jwt_test.py`

**Out of scope**:
- Custom JWT credential controllers.
- Changing Axes lockout parameters or response codes.
- Modifying third-party authentication code.

## Git workflow

Do not commit or push unless explicitly requested.

## Steps

### Step 1: Add a token-pair lockout integration test

Using `override_settings(AXES_FAILURE_LIMIT=2)`, create a real active user and
POST incorrect credentials to `/api/v1/token/pair` until the configured
threshold is reached. Use Django's full-stack test client, not Ninja's direct
`TestClient`: the direct client bypasses `AxesMiddleware` and therefore cannot
exercise the public lockout response contract. Assert the first failure is 401,
the threshold failure is 429, and a subsequent correct password from the same
client identity remains locked at 429 until reset/cooloff. Set `REMOTE_ADDR`
explicitly so IP extraction follows the production path.

**Verify**: the test passes against the current pinned dependencies. If it
fails, stop; that converts this from a test-gap plan into a security bug.

### Step 2: Prove identity separation

If existing Axes fixtures make it cheap, add one assertion that a different
client IP is not locked for the same username under the configured
`[username, ip_address]` combination. Do not duplicate the full admin test
matrix.

**Verify**: focused tests pass without timing sleeps or real network calls.

### Step 3: Run full verification

Run the baked full suite, migrations check, and pre-commit.

**Verify**: all exit 0 at 100% coverage.

## Test plan

The essential assertion is failure threshold on the actual library-owned token
pair route followed by rejection of correct credentials while locked.

## Done criteria

- [ ] JWT credential guessing is covered by an Axes integration test.
- [ ] Test uses real authentication flow, not a mocked backend.
- [ ] Full JWT bake verification passes.

## STOP conditions

- The full-stack lockout test fails on pinned dependencies. A 401 from Ninja's
  direct `TestClient` is not evidence for this STOP condition because that
  harness bypasses `AxesMiddleware`.
- The endpoint path or error contract differs from committed OpenAPI output.
- Passing requires patching django-ninja-jwt internals.

## Maintenance notes

Revisit this test on django-axes or django-ninja-jwt major upgrades. Keep it
focused on the integration boundary rather than library implementation detail.
