# Plan 005: Make CI smoke-test the shipped prod compose file, unpatched

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving to the
> next step. If anything in the "STOP conditions" section occurs, stop and
> report — do not improvise. When done, update the status row for this plan
> in `plans/README.md` — unless a reviewer dispatched you and told you they
> maintain the index.
>
> **Drift check (run first)**:
> `git diff --stat d333a73..HEAD -- .github/workflows/ci.yaml`
> If the file changed since this plan was written, compare the "Current
> state" excerpts against the live code before proceeding; on a mismatch,
> treat it as a STOP condition. (Plans 001/002 add steps to OTHER jobs in
> this file — that drift is expected.)

## Status

- **Priority**: P2
- **Effort**: S–M
- **Risk**: MED — depends on runner tooling; has an explicit rollback
- **Depends on**: 004 preferred first (so CI validates the final stop
  semantics); hard dependency: none
- **Category**: tests
- **Planned at**: commit `d333a73`, 2026-07-05

## Why this matters

The template's Compose files advertise `pre_start` lifecycle hooks as a
core contract (the root README lists "Docker Compose >= 5.3.0 for
`pre_start` lifecycle hooks" as a requirement, and `post_gen_project.py`
warns when the user's Compose is older). But the CI smoke test rewrites
`prod.yaml` before booting it — replacing the `pre_start` hook with a
shell-wrapper `command:` — because GitHub-hosted runners ship an older
Compose. So the single most distinctive production behavior is proven
only in a patched form; the file users actually deploy is never booted
by CI as shipped. External review called this out explicitly. The fix:
install a modern Compose CLI plugin on the runner and delete the patch
step.

## Current state

- `.github/workflows/ci.yaml:138-241` — the `docker-compose-smoke` job
  (matrix: `default`, `minimal`). Relevant steps in order: "Show compose
  version", "Bake project", env-file preparation, then:

  ```yaml
        - name: Adapt pre_start for GitHub runner Compose
          working-directory: /tmp/smoke/my-project
          run: |
            # Temporary CI-only compatibility patch: GitHub-hosted runners reject
            # the Compose pre_start lifecycle hook that the template ships with.
            # Remove this step once runner Compose accepts that modern hook.
            python - <<'PY'
            from pathlib import Path

            compose = Path(".docker/compose/prod.yaml")
            text = compose.read_text()
            pre_start = """    pre_start:
                  - command:
                      - /app/.docker/scripts/migrations.sh
            """
            command = """    command:
                  - /bin/sh
                  - -c
                  - /app/.docker/scripts/migrations.sh && exec /app/.docker/scripts/gunicorn.sh
            """
            if pre_start not in text:
                raise SystemExit("expected api pre_start hook not found")
            compose.write_text(text.replace(pre_start, command))
            PY
  ```

  (Its own comment says to remove it once runner Compose supports the
  hook.)

- The boot step:
  `docker compose -f .docker/compose/prod.yaml --env-file=.env up -d --build --wait --wait-timeout=300`.

- Repo requirement: Compose **>= 5.3.0** (`hooks/post_gen_project.py:6`
  `COMPOSE_MIN_VERSION = (5, 3, 0)`).

- The Compose CLI is a standalone plugin binary
  (`docker-compose`) installed under `~/.docker/cli-plugins/`; releases
  at <https://github.com/docker/compose/releases>. Installing a newer
  plugin does not require replacing the Docker Engine.

- Repo conventions: workflow steps pin exact action/tool versions; YAML
  extended block style; alphabetized where order doesn't matter.

## Commands you will need

| Purpose | Command | Expected on success |
|---------|---------|---------------------|
| Local compose version | `docker compose version --short` | prints version |
| Bake | `uvx cookiecutter . --no-input -o /tmp/plan005` | baked |
| Local smoke rehearsal | the smoke job's steps run by hand (env prep sed lines from ci.yaml:165-170, then `up -d --build --wait`) | stack healthy WITHOUT the patch |
| actionlint | `uvx --from actionlint actionlint .github/workflows/ci.yaml` | exit 0 |
| Root pre-commit | `pre-commit run --all-files` | exit 0 |

## Scope

**In scope**:

- `.github/workflows/ci.yaml` — the `docker-compose-smoke` job only.

**Out of scope** (do NOT touch):

- The template's compose files — they are already correct; CI adapts to
  them, not vice versa.
- `hooks/post_gen_project.py` version warning.
- Other jobs in `ci.yaml`.

## Git workflow

- Work directly on `main`; do not create or switch to a plan branch unless the
  operator explicitly asks.
- Do NOT commit, push, or open a PR unless the operator explicitly instructs it.
- If asked to commit, use a conventional commit such as
  `ci: smoke-test the shipped prod compose file unpatched`.

## Steps

### Step 1: Determine the Compose version to install

Find the latest Compose release satisfying the template's requirement
(>= 5.3.0) at <https://github.com/docker/compose/releases>. Record the
exact version and the sha256 of the `docker-compose-linux-x86_64` asset
(the release page publishes `checksums.txt`).

**Verify**: you have a version string and a checksum; the version is
>= 5.3.0.

### Step 2: Add an install step to the smoke job

Insert after "Set up uv" and before "Show compose version":

```yaml
      - name: Install Docker Compose with pre_start support
        run: |
          mkdir -p ~/.docker/cli-plugins
          curl -fsSL \
            https://github.com/docker/compose/releases/download/v<VERSION>/docker-compose-linux-x86_64 \
            -o ~/.docker/cli-plugins/docker-compose
          echo "<SHA256>  $HOME/.docker/cli-plugins/docker-compose" | sha256sum -c -
          chmod +x ~/.docker/cli-plugins/docker-compose
          docker compose version
```

(`<VERSION>`/`<SHA256>` from Step 1; keep the checksum — CI downloads
must be integrity-pinned.)

**Verify**: actionlint passes.

### Step 3: Delete the patch step

Remove the entire "Adapt pre_start for GitHub runner Compose" step.

**Verify**: `grep -n "pre_start" .github/workflows/ci.yaml` → no matches.

### Step 4: Local rehearsal

If your local `docker compose version --short` is >= 5.3.0 (expected on
the maintainer's machine), run the smoke sequence by hand against a
default bake WITHOUT any patching: env prep (sed lines mirroring
ci.yaml:165-170), `up -d --build --wait --wait-timeout=300`, the two
in-container probes (ci.yaml:204-208), then `down -v`.

**Verify**: stack reaches healthy; `/api/health` and `/api/ready` return
200; the api container ran its `pre_start` migrations (visible in
`docker compose ... logs api` or via the lifecycle-hook container in
`docker compose ps -a` output, depending on Compose version).

### Step 5: CI proof

The change can only be fully proven on a GitHub runner. Run root
`pre-commit run --all-files`. If the operator explicitly authorizes a
commit and push, push from `main` and confirm the `docker-compose-smoke`
matrix (both variants) is green. Otherwise hand the working tree to the
operator with Step 4's local evidence and note that CI green is the
remaining gate.

**Verify**: pre-commit exit 0; CI green (or explicitly handed off).

## Test plan

No pytest changes. The verification artifact is the smoke job booting
the byte-identical shipped `prod.yaml` (assert: the workflow no longer
contains the string `pre_start`).

## Done criteria

- [ ] `ci.yaml` smoke job installs a pinned, checksum-verified Compose
      >= 5.3.0
- [ ] The "Adapt pre_start" step is gone; the patch logic no longer
      appears: `grep -c "expected api pre_start hook not found" .github/workflows/ci.yaml` → 0
      (NOTE: do not grep bare `pre_start` — the Step 2 install step's own
      name "Install Docker Compose with pre_start support" contains that
      substring by design, so a bare grep returns 1, not 0.)
- [ ] Local rehearsal (Step 4) booted the unpatched prod stack to
      healthy with probes passing
- [ ] actionlint + root pre-commit exit 0
- [ ] CI smoke matrix green, or handoff to operator recorded
- [ ] `plans/README.md` status row updated

## STOP conditions

- No published Compose release >= 5.3.0 provides a standalone linux
  x86_64 plugin binary — report; the alternative (upgrading Docker
  Engine on the runner) is out of scope.
- The runner's Docker Engine rejects the newer plugin or `pre_start`
  still errors with it installed (engine-side incompatibility): restore
  the patch step exactly as excerpted above, and report the exact error
  output — the patch remains the documented fallback.
- Local rehearsal fails on a machine with Compose >= 5.3.0 — that means
  the shipped file itself has a problem; report immediately (this would
  be a release-blocking finding, not something to patch in CI).

## Maintenance notes

- The pinned Compose version/checksum in the workflow is a manual bump —
  Dependabot does not track it. Consider bumping it whenever the
  `COMPOSE_MIN_VERSION` in `hooks/post_gen_project.py` changes.
- Once GitHub runners ship Compose >= 5.3.0 by default, the install step
  can be deleted too (leave a comment on the step saying so).
- Reviewer: confirm the checksum matches the official `checksums.txt`
  for the pinned release.
