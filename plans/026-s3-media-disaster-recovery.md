# Plan 026: Define a disaster-recovery contract for S3 media

> **Executor instructions**: Prefer provider-neutral requirements and verified
> restore drills. Never include real bucket names, keys, or credentials.
>
> **Drift check (run first)**: `rtk git diff --stat b367191..HEAD -- '{{cookiecutter.project_slug}}/src/config/settings/environments/prod.py' '{{cookiecutter.project_slug}}/README.md' 'README.md'`

## Status

- **Priority**: P3
- **Effort**: M
- **Risk**: LOW
- **Depends on**: none
- **Category**: direction, docs
- **Planned at**: commit `b367191`, 2026-07-10

## Why this matters

Local media has backup, restore, retention, and verification scripts. S3 is the
default production store but has no equivalent recovery contract; object
storage durability is not the same as protection from application deletion,
credential compromise, or operator error.

## Current state

- S3 storage uses private objects, versioned names (`file_overwrite=False`),
  signed URLs, and optional custom endpoint/region.
- README requires a bucket but does not require versioning, lifecycle,
  replication, retention, or restore drills.
- Providers differ substantially; a universal backup script may be misleading.

## Commands you will need

| Purpose | Command | Expected |
|---|---|---|
| Docs lint | `rtk uv run pre-commit run markdownlint --all-files` | exit 0 |
| Disposable listing | `aws s3api list-object-versions --bucket "$SOURCE_BUCKET"` | versions visible |
| Versioning check | `aws s3api get-bucket-versioning --bucket "$SOURCE_BUCKET"` | `Status` is `Enabled` |

## Scope

**In scope**:
- provider-neutral RPO/RTO and recovery requirements
- AWS S3 reference commands plus S3-compatible caveats
- `{{cookiecutter.project_slug}}/README.md` and root feature summary
- optional configuration checks only if portable

**Out of scope**:
- Embedding cloud credentials.
- Assuming every S3-compatible provider supports AWS replication/object lock.
- Copying all media through the application container.

## Git workflow

Do not commit provider credentials, generated inventories, or live identifiers.
Use only disposable buckets/accounts for the drill.

## Steps

### Step 1: Define threat model and recovery objectives

Cover accidental deletion/overwrite, compromised application credentials,
bucket loss/region loss, ransomware, and provider outage. State that projects
must choose RPO/RTO and off-account/off-provider requirements.

### Step 2: Document a baseline control set

For AWS, document bucket versioning, least-privilege application credentials,
MFA/delete or object-lock tradeoffs, lifecycle retention, replication or
independent copy, audit logging, and recovery from a prior version. For generic
S3, label each capability as provider-dependent and require an equivalent.

### Step 3: Add a restore-drill recipe

Using `.test`/placeholder names only, document restoring selected objects to a
separate recovery prefix/bucket, verifying counts/checksums/metadata, and
switching only after validation. Never recommend destructive in-place restore
as the first step.

### Step 4: Decide whether a template check is portable

Prototype a Django deployment check for clearly unsafe settings only if it can
operate without provider network calls. Otherwise keep provider controls in
the production checklist and explain why.

**Verify**: markdownlint passes and an operator can execute the reference drill
against a disposable bucket without undocumented steps.

## Test plan

Run the documented versioning, delete, recovery-to-separate-location, checksum,
and cutover-readiness sequence against disposable AWS S3; separately review
which steps apply to one non-AWS S3-compatible provider.

## Done criteria

- [ ] S3 media has explicit threat, RPO/RTO, retention, copy, and restore guidance.
- [ ] AWS-specific features are not presented as universal.
- [ ] Recovery uses a separate location before cutover.
- [ ] No credentials or live identifiers appear.

## STOP conditions

- A proposed check requires production provider access during Django startup.
- Guidance assumes a capability absent from common S3-compatible providers.

## Maintenance notes

Review the recovery section whenever storage options or default provider
behavior changes.
