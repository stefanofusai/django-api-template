# Plan 012: Assert the OPTIONS throttle bypass and bake CORS+throttling together

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving to the
> next step. If anything in the "STOP conditions" section occurs, stop and
> report — do not improvise. When done, update the status row for this plan
> in `plans/README.md` — unless a reviewer dispatched you and told you they
> maintain the index.
>
> **Drift check (run first)**:
> `git diff --stat 75c4dce..HEAD -- '{{cookiecutter.project_slug}}/src/apps/api/throttling.py' '{{cookiecutter.project_slug}}/tests/api/unit/throttling_test.py' .github/workflows/ci.yaml`
> If any in-scope file changed since this plan was written, compare the
> "Current state" excerpts against the live code before proceeding; on a
> mismatch, treat it as a STOP condition.

## Status

- **Priority**: P3
- **Effort**: S
- **Risk**: LOW
- **Depends on**: none (coordinate with plan 011 if executing concurrently —
  011 edits ci.yaml's reject matrix, this plan edits the bake matrix;
  different blocks, execute sequentially to avoid merge conflicts)
- **Category**: tests
- **Planned at**: commit `75c4dce`, 2026-07-08

## Why this matters

The public-API throttle middleware deliberately exempts `OPTIONS` requests so
CORS preflights are never counted against — or blocked by — the anonymous IP
budget. If that carve-out regresses, browser clients get spurious 429s on
preflight and every cross-origin call breaks. Today no test sends an OPTIONS
request, and no CI bake combines `use_cors=yes` with `api_throttling=basic`,
so the interaction the carve-out exists for is exercised nowhere. One unit
test plus one bake-matrix row closes both gaps.

## Current state

This repo is a **cookiecutter template**. Files under
`{{cookiecutter.project_slug}}/` contain Jinja; verify by baking. Always
single-quote such paths in shell commands.

- `{{cookiecutter.project_slug}}/src/apps/api/throttling.py` — the carve-out:

```python
# throttling.py:93-101
def _should_throttle_public_api_anonymous_request(request: HttpRequest) -> bool:
    return all(
        (
            settings.API_THROTTLE_ANON_RATE is not None,
            not getattr(request.user, "is_authenticated", False),
            request.method != "OPTIONS",
            request.path_info.startswith("/api/v1/"),
        )
    )
```

`PublicAPIThrottleMiddleware.__call__` (lines 36-59) short-circuits to
`self.get_response(request)` when that predicate is false — so an OPTIONS
request must pass through untouched even with the anon budget exhausted.

- `{{cookiecutter.project_slug}}/tests/api/unit/throttling_test.py` — the
  test file to extend. Exemplar pattern (lines 149-160):

```python
@override_settings(API_THROTTLE_ANON_RATE="1/min", API_THROTTLE_USER_RATE=None)
def test_public_api_middleware_throttles_header_less_request_when_budget_exhausted() -> (
    None
):
    request = RequestFactory().get("/api/v1/notes")
    request.user = AnonymousUser()
    middleware = PublicAPIThrottleMiddleware(
        lambda _request: HttpResponse(status=HTTPStatus.OK),
    )

    assert middleware(request).status_code == HTTPStatus.OK
    assert middleware(request).status_code == HTTPStatus.TOO_MANY_REQUESTS
```

Throttle state lives in the cache; the test suite's autouse fixture clears
the cache between tests (see `tests/conftest.py`), so consuming the 1/min
budget inside one test is deterministic.

- `.github/workflows/ci.yaml` bake matrix (lines 33-109): cases are ordered
  alphabetically; `cors` (line 34, `use_cors=yes`) and `cors-csp` (line 38)
  never set `api_throttling`; `throttling-no-example` (line 94,
  `api_throttling=basic`) and `example-token-auth-throttling` (line 62)
  never set `use_cors`.

Knob interactions you must respect: `tests/api/unit/throttling_test.py`
exists only when `api_throttling=basic` (removed otherwise by
`hooks/post_gen_project.py`), and `use_cors=yes` requires nothing else —
so the new matrix case needs only those two knobs.

## Commands you will need

| Purpose | Command | Expected on success |
|---------|---------|---------------------|
| Bake the new combo | `uvx cookiecutter . -o /tmp/verify-011 --no-input use_cors=yes api_throttling=basic` | exit 0 |
| Install | `cd /tmp/verify-011/my-project && uv sync --locked` | exit 0 |
| Targeted tests (need Postgres for the suite's DB fixture setup — start it first) | `cp .env.example .env && docker compose -f .docker/compose/dev.yaml --env-file=.env up -d --wait postgres && uv run pytest tests/api/unit/throttling_test.py --no-cov` | all pass |
| Full gate | `uv run pytest` then `git init -q && git add -A && uv run pre-commit run --all-files` | exit 0, coverage 100% |
| Workflow lint | `uvx pre-commit run actionlint --all-files` (repo root) | exit 0 |

## Scope

**In scope**:

- `{{cookiecutter.project_slug}}/tests/api/unit/throttling_test.py`
- `.github/workflows/ci.yaml` — ONLY inserting one bake-matrix entry

**Out of scope** (do NOT touch):

- `{{cookiecutter.project_slug}}/src/apps/api/throttling.py` — behavior is
  correct; this plan only asserts it. (A separate plan 008 documents its
  cache coupling — don't add comments here.)
- `{{cookiecutter.project_slug}}/tests/api/integration/throttling_test.py` —
  integration OPTIONS coverage would need CORS headers wired into the test
  client and is deliberately deferred (see Maintenance notes).
- The `reject-invalid-input` matrix in ci.yaml (plan 011's territory).

## Git workflow

- Conventional commits, e.g.
  `test: assert the OPTIONS throttle bypass and bake cors+throttling`.
- Do NOT push unless instructed.

## Steps

### Step 1: Add the OPTIONS bypass unit test

In `{{cookiecutter.project_slug}}/tests/api/unit/throttling_test.py`, next to
the existing `test_public_api_middleware_*` tests, add:

```python
@override_settings(API_THROTTLE_ANON_RATE="1/min", API_THROTTLE_USER_RATE=None)
def test_public_api_middleware_allows_options_request_when_budget_exhausted() -> (
    None
):
    get_request = RequestFactory().get("/api/v1/notes")
    get_request.user = AnonymousUser()
    options_request = RequestFactory().options("/api/v1/notes")
    options_request.user = AnonymousUser()
    middleware = PublicAPIThrottleMiddleware(
        lambda _request: HttpResponse(status=HTTPStatus.OK),
    )

    assert middleware(get_request).status_code == HTTPStatus.OK
    assert middleware(get_request).status_code == HTTPStatus.TOO_MANY_REQUESTS
    assert middleware(options_request).status_code == HTTPStatus.OK
```

The first two asserts prove the budget is genuinely exhausted (same
technique as the exemplar); the third proves OPTIONS bypasses the exhausted
budget. Place the test respecting the file's existing ordering conventions
(the middleware tests cluster together — insert alphabetically within that
cluster if the surrounding tests are alphabetized, otherwise append to the
cluster).

**Verify** (after step 3's bake): targeted pytest run passes.

### Step 2: Add the bake-matrix row

In `.github/workflows/ci.yaml`, insert into `jobs.bake.strategy.matrix.include`
between `cors-csp` and `csp` (alphabetical order):

```yaml
          - case: cors-throttling
            project_name: My Project
            extra-args: use_cors=yes api_throttling=basic
            slug: my-project
```

**Verify**: `uvx pre-commit run actionlint --all-files` → exit 0;
`uvx pre-commit run check-github-workflows --all-files` → exit 0.

### Step 3: Bake the combo and run its suite

```shell
uvx cookiecutter . -o /tmp/verify-011 --no-input use_cors=yes api_throttling=basic
cd /tmp/verify-011/my-project
uv sync --locked
cp .env.example .env
docker compose -f .docker/compose/dev.yaml --env-file=.env up -d --wait postgres
uv run pytest
git init -q && git add -A
uv run pre-commit run --all-files
docker compose -f .docker/compose/dev.yaml --env-file=.env down -v
```

**Verify**: full suite passes at 100% coverage INCLUDING the new test;
pre-commit exits 0. This rehearses exactly what the new CI case will run.

## Test plan

One new unit test (step 1): OPTIONS request is served 200 while the same
anon budget returns 429 to a GET. Pattern:
`test_public_api_middleware_throttles_header_less_request_when_budget_exhausted`.
The bake-matrix row is itself a standing integration test of the
CORS+throttling knob combination.

## Done criteria

- [ ] New unit test present in the template file and passing in the
  `use_cors=yes api_throttling=basic` bake
- [ ] `cors-throttling` case present in ci.yaml, alphabetically placed;
  actionlint + check-github-workflows pass
- [ ] Full suite + pre-commit green on the combo bake (step 3)
- [ ] `git status` shows only the two in-scope files modified
- [ ] `plans/README.md` status row updated

## STOP conditions

Stop and report back if:

- The OPTIONS assert fails (the third one) — that is a REAL BUG in the
  carve-out, not a test problem; report it as a finding instead of changing
  the middleware.
- The combo bake fails pytest/pre-commit on anything unrelated to your test
  (would mean the cors+throttling combination has a pre-existing defect —
  exactly what this bake row exists to catch; report it).
- `RequestFactory().options(...)` requests don't reach the middleware
  predicate as `method == "OPTIONS"` (would contradict the excerpt).

## Maintenance notes

- Deferred: an integration-level preflight test (real `OPTIONS` with
  `Origin` + `Access-Control-Request-Method` headers through the full
  middleware stack) would also pin the CORS middleware ordering; it needs
  `use_cors=yes`-gated Jinja in an integration file that is currently
  removed in some combos — worth doing only if a preflight regression ever
  actually occurs.
- If the throttle design changes (e.g. per-endpoint budgets), keep the
  OPTIONS exemption and this test in sync with plan 008's documentation
  comment.
