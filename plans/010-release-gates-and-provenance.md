# Plan 010: Gate release images and publish verifiable provenance

> **Executor instructions**: Follow every step and update the index. Workflow
> permissions are security-sensitive; stop instead of broadening them casually.
>
> **Drift check (run first)**: `rtk git diff --stat b367191..HEAD -- '{{cookiecutter.project_slug}}/.github/workflows/' '{{cookiecutter.project_slug}}/README.md' '{{cookiecutter.project_slug}}/AGENTS.md'`

## Status

- **Priority**: P2
- **Effort**: M
- **Risk**: MED
- **Depends on**: none
- **Category**: security, dx
- **Planned at**: commit `b367191`, 2026-07-10

## Why this matters

A semver tag currently runs only pytest before publishing a GHCR image. Tags
can point at commits that never passed migration, deployment, dependency,
pre-commit, or Docker smoke gates. The resulting image also has no provenance
attestation, despite the template's reproducibility goals.

## Current state

- `release.yaml:11-16` depends only on reusable `tests.yaml`.
- Other generated workflows do not expose `workflow_call`.
- `docker/build-push-action` returns an image digest that can be attested.
- Repository policy intentionally uses Dependabot-managed action version tags;
  do not convert all actions to commit SHAs in this plan.

## Commands you will need

| Purpose | Command | Expected |
|---|---|---|
| Workflow lint | `rtk uv run pre-commit run check-github-workflows --all-files` | exit 0 |
| Action lint | `rtk uv run pre-commit run actionlint --all-files` | exit 0 |
| Security lint | `rtk uv run pre-commit run zizmor --all-files` | exit 0 |

## Scope

**In scope**:
- `{{cookiecutter.project_slug}}/.github/workflows/release.yaml`
- generated dependency, deployment, Docker, migration, pre-commit, and test workflows
- `{{cookiecutter.project_slug}}/README.md`
- `{{cookiecutter.project_slug}}/AGENTS.md` branch-protection/release notes

**Out of scope**:
- Automatic deployment to a host.
- Changing action tag-pinning policy.
- Publishing a `latest` image tag.

## Git workflow

Do not commit or push unless explicitly requested.

## Steps

### Step 1: Make production gates reusable

Add `workflow_call` to dependency audit, deployment checks, Docker checks,
migration checks, and pre-commit without changing their pull-request/push
triggers or rendered job names. Confirm reusable workflows require no secrets
that are unavailable on tag runs.

**Verify**: workflow schema and actionlint pass.

### Step 2: Gate publication on all checks

Call the reusable workflows from `release.yaml`. Make the publish job `needs`
all required gate jobs, including tests. Keep job names concise and document
any downstream required-check implications.

**Verify**: a local workflow graph inspection shows no publish path when any
gate fails.

### Step 3: Emit provenance for the pushed digest

Give the publish step an `id`, capture its digest, and add the current stable
`actions/attest` action, which GitHub recommends for new v4 implementations,
with only the permissions it needs: `id-token: write`, `attestations: write`,
`packages: write`, and read-only contents. Set `create-storage-record: false`
so the action does not require the unrelated `artifact-metadata: write`
permission. Attest the exact GHCR subject name and digest and push the
attestation to the registry.

**Verify**: zizmor passes with no broader repository permissions.

### Step 4: Document verification

Add a release verification example using `gh attestation verify` against the
repository identity and immutable version tag. Explain that deploys should use
only images whose tag, project version, and attestation agree.

**Verify**: markdownlint passes.

### Step 5: Exercise a real test release safely

Use a disposable generated repository or non-production package namespace to
push a test tag, verify every prerequisite runs, and verify the OCI
attestation. Delete only the disposable tag/package afterward.

**Verify**: `gh attestation verify` exits 0 for the produced image and fails
for an unrelated repository identity.

## Test plan

Static workflow checks plus one disposable end-to-end tag run. Confirm publish
is skipped when a prerequisite is intentionally failed.

## Done criteria

- [ ] Release publication needs every production gate.
- [ ] Published digest has verifiable provenance.
- [ ] Permissions are minimal and zizmor passes.
- [ ] Verification instructions work verbatim.

## STOP conditions

- A reusable workflow requires write permissions or secrets not appropriate
  for tag-triggered releases.
- Attestation would require making the repository or package public.
- Job renames would silently change downstream required checks without docs.

## Maintenance notes

Update the attestation action through existing Dependabot policy. Review the
workflow graph whenever a new production gate is added.
