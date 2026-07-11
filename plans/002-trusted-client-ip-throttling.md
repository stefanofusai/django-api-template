# Plan 002: Make anonymous throttling use a trusted client IP boundary

> **Executor instructions**: Run every gate and stop on the conditions below.
> Update `plans/README.md` when complete unless instructed otherwise.
>
> **Drift check (run first)**: `rtk git diff --stat 20ec7c5..HEAD -- '{{cookiecutter.project_slug}}/src/config/settings/components/throttling.py' '{{cookiecutter.project_slug}}/tests/api/integration/throttling_test.py' '{{cookiecutter.project_slug}}/.env.example' '{{cookiecutter.project_slug}}/README.md'`

## Status

- **Priority**: P1
- **Effort**: M
- **Risk**: MED
- **Depends on**: none
- **Category**: security
- **Planned at**: commit `20ec7c5`, 2026-07-10

## Why this matters

`django-ninja-extra==0.31.5` identifies anonymous callers through its own
`NINJA_EXTRA["NUM_PROXIES"]` setting, while Django Ninja separately reads
`NINJA_NUM_PROXIES`. When the django-ninja-extra value is `None`, an arbitrary
`X-Forwarded-For` value becomes the cache key. The current integration test
uses caller-supplied headers to obtain separate counters, so a client can
rotate the header and bypass the advertised anonymous throttle.

## Current state

- `components/throttling.py` defines rates only; it sets neither
  `NINJA_NUM_PROXIES` nor `NINJA_EXTRA["NUM_PROXIES"]`.
- Django Ninja and django-ninja-extra each implement `get_ident()` and read
  separate settings. Both use `REMOTE_ADDR` when proxy count is zero and
  select from `X-Forwarded-For` only when an explicit positive proxy count is
  configured. Keep the two values identical so future use of either throttle
  implementation preserves the same trust boundary.
- `throttling_test.py:61-80` treats two untrusted XFF values as two clients.
- Bundled Traefik is one trusted application proxy. Bring-your-own ingress may
  use a different count; that is deployment topology and may be configured.

## Commands you will need

| Purpose | Command | Expected |
|---|---|---|
| Bake direct | `rtk uvx cookiecutter . -o /tmp/plan-002-direct --no-input api_throttling=basic use_example_api=yes use_traefik=no behind_proxy=no` | created |
| Bake Traefik | `rtk uvx cookiecutter . -o /tmp/plan-002-proxy --no-input api_throttling=basic use_example_api=yes` | created |
| Tests | `rtk uv run pytest tests/api -q` | pass |
| Full suite | `rtk uv run pytest` | pass, coverage 100% |

## Scope

**In scope**:
- `{{cookiecutter.project_slug}}/src/config/settings/components/throttling.py`
- `{{cookiecutter.project_slug}}/tests/api/integration/throttling_test.py`
- `{{cookiecutter.project_slug}}/tests/api/unit/throttling_test.py`
- `{{cookiecutter.project_slug}}/.env.example`
- `{{cookiecutter.project_slug}}/README.md`

**Out of scope**:
- Changing throttle rates or cache algorithms.
- Treating application throttling as DDoS protection.
- Reworking django-axes client-IP policy in this plan.

## Git workflow

Do not commit or push unless explicitly requested.

## Steps

### Step 1: Add failing identity-boundary tests

For a direct deployment with proxy count zero, send repeated requests with the
same `REMOTE_ADDR` but changing XFF and assert they share one budget. For a
one-proxy deployment, use a realistic comma-separated chain and assert the
trusted position identifies the actual client while changes to untrusted
earlier entries do not mint a new budget. Retain a test proving genuinely
different clients get separate counters.

**Verify**: the spoof-resistance tests fail with current settings.

### Step 2: Configure the proxy count explicitly

Derive one validated proxy count in the rendered throttling settings, then set
both `NINJA_NUM_PROXIES` and `NINJA_EXTRA["NUM_PROXIES"]` to that value. Use a
fixed default of `1` for bundled Traefik and `0` for a direct no-proxy
deployment. For `behind_proxy=yes` without bundled Traefik, read an optional
`TRUSTED_PROXY_COUNT` integer whose documented default is one. Reject negative
values during settings import with `ImproperlyConfigured`.

Document `TRUSTED_PROXY_COUNT` as topology configuration, not a security
secret, and warn that it is safe only when the ingress overwrites or correctly
appends forwarding headers.

**Verify**: focused tests pass in both bakes.

### Step 3: Test rendered defaults

Extend the subprocess settings test pattern in `throttling_test.py` to assert
the direct bake renders zero and the bundled-Traefik bake renders one in both
settings locations, and that the values remain equal. Add a negative-value
failure assertion if the validation lives in settings.

**Verify**: full suites pass at 100% coverage.

### Step 4: Run full checks

Run pytest and pre-commit in both bakes and root pre-commit.

**Verify**: all commands exit 0.

## Test plan

The essential regression is same socket peer plus varying untrusted XFF. Also
cover no XFF, one proxy, multiple proxy entries, different legitimate clients,
and invalid negative configuration.

## Done criteria

- [ ] No deployment leaves either proxy-count setting as `None` when
  throttling exists; `NINJA_NUM_PROXIES` and
  `NINJA_EXTRA["NUM_PROXIES"]` are equal.
- [ ] Changing an untrusted XFF component cannot reset the budget.
- [ ] Direct and bundled-proxy defaults are documented and tested.
- [ ] Both baked suites pass with coverage 100%.

## STOP conditions

- Traefik's actual forwarded-header order contradicts the assumed rightmost
  trusted-proxy semantics; capture a real request and report before changing
  indexes.
- Supporting BYO ingress requires trusting an arbitrary header without an
  explicit proxy count.

## Maintenance notes

Recheck both Django Ninja's and django-ninja-extra's `get_ident()` whenever
either dependency changes major version. Proxy count, settings wiring, and
header overwrite behavior must be reviewed as a single security boundary.
