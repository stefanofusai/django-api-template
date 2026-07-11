# Plan 025: Decide whether authentication should exist without the example API

> **Executor instructions**: Respect the current documented decision unless a
> new design is explicitly approved. This is not a bug-fix plan.
>
> **Drift check (run first)**: `rtk git diff --stat b367191..HEAD -- 'cookiecutter.json' 'README.md' 'hooks/post_gen_project.py' '{{cookiecutter.project_slug}}/src/apps/api/' '{{cookiecutter.project_slug}}/README.md'`

## Status

- **Priority**: P3
- **Effort**: M
- **Risk**: MED
- **Depends on**: none
- **Category**: direction
- **Planned at**: commit `b367191`, 2026-07-10

## Why this matters

Today `api_auth` explicitly affects only the optional notes example; without
that example all JWT wiring is pruned. This is documented, not a silent bug,
but users may reasonably want token issuance infrastructure before adding
their first real resource. Decoupling would broaden the knob contract and
dependency surface.

## Current state

- Root variable docs say `api_auth` only takes effect with
  `use_example_api=yes`.
- Post-gen removes JWT auth/settings/tests unless both conditions are true.
- `v1_api` has no global authentication; resource routers opt in explicitly.

## Commands you will need

| Purpose | Command | Expected |
|---|---|---|
| Current no-op bake | `rtk uvx cookiecutter . -o /tmp/plan-025-current --no-input api_auth=jwt use_example_api=no` | succeeds as documented |
| Prototype tests | `rtk uv run pytest` | pass, coverage 100% |
| Schema drift | `rtk uv run pre-commit run --all-files` | exit 0 |

## Scope

**In scope**:
- user/workflow evidence gathering
- disposable auth-only bakes
- `docs/decisions/auth-without-example-api.md` (create)

**Out of scope**:
- Treating the current no-op as an undocumented defect.
- Making all APIs globally authenticated.
- Adding signup/account-management product features.

## Git workflow

Keep auth-only prototype changes on a disposable local branch. Commit only the
decision document unless the maintainer approves a contract change.

## Steps

### Step 1: Define candidate contracts

Compare: keep current coupled behavior; make `api_auth=jwt` always install
token endpoints; or split a new `use_jwt_auth` infrastructure knob from an
example-resource auth choice. For each, map prompts, dependencies, files,
OpenAPI, docs, security defaults, and migration impact.

### Step 2: Prototype auth-only output

In a disposable template branch, bake without notes but with JWT token
pair/refresh/verify/blacklist endpoints and required cleanup guidance. Confirm
no business endpoint is accidentally protected and schemas/tests remain clear.

**Verify**: auth-only bake passes pytest, schema drift, deployment checks, and
pre-commit.

### Step 3: Assess user value and maintenance cost

Look for real downstream requests or repeated manual wiring. Estimate matrix
growth, dependency cost, documentation complexity, and security review burden.

### Step 4: Record verdict

Choose keep-coupled, always-JWT, or split-knob. Record migration behavior for
existing Cookiecutter invocations and a revisit trigger. Do not implement a
new knob without maintainer approval.

## Test plan

For the prototype, cover token pair/refresh/verify/blacklist, Axes lockout,
inactive users, schema export, no notes imports, and no accidental global auth.

## Done criteria

- [ ] Three contracts are compared with concrete file/matrix impact.
- [ ] Auth-only prototype passes full checks.
- [ ] Current documented behavior is preserved unless approval changes it.
- [ ] Verdict and migration story are explicit.

## STOP conditions

- No maintainer/user demand exists and the new knob only adds surface.
- Auth-only output implies global protection contrary to the resource policy.
- Existing option values cannot migrate without surprising users.

## Maintenance notes

Revisit when multiple downstream projects add the same auth infrastructure
after baking without the notes example.
