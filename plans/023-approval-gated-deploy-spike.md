# Plan 023: Design an approval-gated remote Compose deployment

> **Executor instructions**: This is a high-risk design spike. Do not add host
> credentials or a production deployment workflow without explicit approval.
>
> **Drift check (run first)**: `rtk git diff --stat b367191..HEAD -- '{{cookiecutter.project_slug}}/.github/workflows/release.yaml' '{{cookiecutter.project_slug}}/.docker/scripts/deploy.sh' '{{cookiecutter.project_slug}}/README.md'`

## Status

- **Priority**: P3
- **Effort**: L
- **Risk**: HIGH
- **Depends on**: plan 010
- **Category**: direction
- **Planned at**: commit `b367191`, 2026-07-10

## Why this matters

Image publication is automated, but deployment requires an operator shell on
the host. Some single-operator users may benefit from an auditable GitHub
Environment approval and serialized promotion, but host connectivity and
Docker authority make an unsafe default worse than manual deployment.

## Current state

- `deploy.sh` is already the canonical deployment primitive and rollback path.
- Release workflow publishes versioned GHCR images.
- No remote host, runner, environment, or secret topology is defined.

## Commands you will need

| Purpose | Command | Expected |
|---|---|---|
| Workflow lint | `rtk uv run pre-commit run actionlint --all-files` | exit 0 for any prototype |
| Security lint | `rtk uv run pre-commit run zizmor --all-files` | no new high findings |
| Attestation | `gh attestation verify "oci://$IMAGE" --repo="$REPO"` | exit 0 |

## Scope

**In scope**:
- threat model and disposable prototype
- `docs/decisions/approval-gated-deploy.md` (create)
- comparison of restricted self-hosted runner vs restricted SSH

**Out of scope**:
- Default production credentials in the template.
- Running a general-purpose runner as root.
- Reimplementing deployment logic in YAML.

## Git workflow

Prototype only in a disposable private repository/host. Do not commit secrets,
push a production workflow, or register a runner against the real repository.

## Steps

### Step 1: Define security and recovery requirements

Document actor permissions, environment approval, host identity verification,
secret storage, concurrency, image provenance verification, audit logs,
rollback, runner updates, and compromise containment.

**Verify**: each threat has a preventive or detective control.

### Step 2: Prototype two connectivity models

In disposable infrastructure, compare a dedicated repository-scoped
self-hosted runner with restricted SSH executing only `deploy.sh <tag>`. In
both cases require GitHub Environment approval, serialize deployments, verify
the image attestation from plan 010, and prohibit arbitrary workflow command
input.

**Verify**: unauthorized branches/actors cannot deploy; concurrent dispatches
serialize; rollback uses an earlier immutable tag.

### Step 3: Render a verdict

Choose adopt-self-hosted, adopt-SSH, or keep-manual. Record operational burden,
required secrets, exact permissions, failure recovery, and a decision trigger.
Do not ship a workflow on a keep-manual verdict.

### Step 4: Implement only after approval

If approved, add an optional workflow disabled until the repository owner
creates the named Environment and secrets. It must call `deploy.sh`, not copy
its logic.

## Test plan

Attempt approved, unapproved, concurrent, rollback, wrong-attestation, and
pull-request-origin deployments in disposable infrastructure. Capture audit
events and verify secrets never reach logs.

## Done criteria

- [ ] Threat model and two prototypes are documented.
- [ ] Approval, serialization, provenance, and rollback are proven.
- [ ] No credentials are committed or logged.
- [ ] Adopt/defer verdict is explicit.

## STOP conditions

- The only viable runner requires broad organization/repository access.
- Host credentials would be available to pull-request code.
- Deployment cannot be restricted to the existing script and validated tag.

## Maintenance notes

Remote deployment is optional operational surface. Manual `deploy.sh` remains
the supported fallback even if automation is adopted.
