# Plan 020 Design: async example endpoint

## Recommendation

Ship a small opt-in notes endpoint:

`POST /api/v1/notes/{note_id}/share`

The endpoint should fetch the note through the existing ownership scope
(`id=note_id, owner=request.user`) and enqueue `apps.core.tasks.send_email` with
the note body, the supplied recipient, and a simple subject. This teaches the
request-to-task pattern directly without making normal note creation produce a
surprising side effect.

Keep the "do nothing beyond prose" option open for the maintainer. The endpoint
is useful because it makes Celery copy-pasteable, but it also expands the
example API from CRUD into a small collaboration workflow.

## Design answers

1. **Example action**

   Prefer `POST /notes/{note_id}/share` over enqueueing on `create_note`.
   Sharing is explicit, easy to test, and preserves the current create endpoint's
   pure CRUD behavior. The endpoint returns `202 Accepted` after enqueueing.

2. **Knob gate and degradation**

   The endpoint, request schema, imports, and tests should be rendered only when
   the notes app exists and both async prerequisites exist.

   Exact Jinja gate inside the notes files:

   ```jinja
   {%- if cookiecutter.use_celery != "none" and cookiecutter.email_provider != "none" %}
   ```

   `use_example_api == "yes"` is implicit because `src/apps/notes` and
   `tests/notes` are removed when it is `no`.

3. **CI matrix**

   Existing `example-api` covers the all-on path:
   `use_example_api=yes`, `use_celery=worker+beat`, `email_provider=resend`.

   Add two generated-project bake cases so both halves of the gate are covered
   with notes enabled:

   - `example-api-no-celery`: `use_example_api=yes use_celery=none`
   - `example-api-no-email`: `use_example_api=yes email_provider=none`

   Existing `default` already covers celery/email present with notes absent.
   Existing `minimal` covers the all-off/no-notes path.

4. **Coverage**

   The share route adds `src/` lines only in the all-on render, where the
   integration test also renders and executes the task eagerly. In no-celery or
   no-email renders, the endpoint and test are absent, so there are no uncovered
   route lines or dangling imports.

5. **Schemathesis**

   The new route joins `/api/v1/openapi.json`. The PoC full test run passed the
   existing contract test. The route uses the same `django_auth` router as the
   other notes endpoints, so anonymous/auth error handling stays in the already
   covered pattern.

6. **Minimalism check**

   This is worth shipping if the maintainer wants Celery to be demonstrated as
   more than a background scheduler. If the template should keep the notes API
   strictly CRUD-only, reject the endpoint and instead keep the README prose
   around `send_email.delay(...)`.

## Knob matrix

| `use_example_api` | `use_celery` | `email_provider` | Rendered result |
|-------------------|--------------|------------------|-----------------|
| `yes` | `worker+beat` or `worker` | `resend` or `smtp` | Notes CRUD plus `POST /notes/{id}/share` |
| `yes` | `worker+beat` or `worker` | `none` | Notes CRUD only; no `send_email`, no share route |
| `yes` | `none` | any value | Notes CRUD only; no tasks module, no share route |
| `no` | any value | any value | No notes app or notes tests |

Scratch bakes confirmed these corners:

- `/tmp/bake-020-poc`: all-on, share endpoint present.
- `/tmp/bake-020-no-celery`: notes on, celery off, share endpoint absent.
- `/tmp/bake-020-no-email`: notes on, email off, share endpoint absent.
- `/tmp/bake-020-celery-no-notes`: celery/email on, notes off, notes app absent.
- `/tmp/bake-020-off`: notes on, celery off, email off, share endpoint absent.

## Build-plan file inventory

- `{{cookiecutter.project_slug}}/src/apps/notes/routes.py`
  - gated import of `send_email`
  - gated import of `NoteShareInSchema`
  - gated `share_note` route
- `{{cookiecutter.project_slug}}/src/apps/notes/schemas.py`
  - gated `NoteShareInSchema`
- `{{cookiecutter.project_slug}}/tests/notes/integration/notes_test.py`
  - gated mail/Faker imports
  - gated `test_share_note_returns_202_when_authenticated_owner`
- `.github/workflows/ci.yaml`
  - add `example-api-no-celery`
  - add `example-api-no-email`
- `{{cookiecutter.project_slug}}/README.md`
  - document the endpoint only inside the same notes+celery+email gate

No dependency changes are needed. The PoC used `recipient: str` rather than
Pydantic `EmailStr` to avoid adding `email-validator`.

## PoC diff summary

Representative throwaway changes applied under `/tmp/bake-020-template`:

```diff
+from apps.core.tasks import send_email
-from .schemas import NoteInSchema, NoteOutSchema
+from .schemas import NoteInSchema, NoteOutSchema, NoteShareInSchema
+
+@router.post(
+    "/{note_id}/share",
+    response={202: None, 401: ErrorSchema, 403: ErrorSchema, 404: ErrorSchema},
+)
+def share_note(
+    request: HttpRequest, note_id: uuid.UUID, payload: NoteShareInSchema
+) -> Status[None]:
+    note = get_object_or_404(Note, id=note_id, owner=request.user)
+    send_email.delay(
+        message=note.body,
+        recipient_list=[payload.recipient],
+        subject=f"Note shared: {note.title}",
+    )
+    return Status(202, None)
```

```diff
+class NoteShareInSchema(Schema):
+    recipient: str
```

```diff
+def test_share_note_returns_202_when_authenticated_owner(
+    authenticated_v1_api_client: AuthenticatedTestClient,
+    faker: Faker,
+    note_factory: type[NoteFactory],
+) -> None:
+    note = note_factory.create(owner=authenticated_v1_api_client.user)
+    recipient = faker.email()
+
+    response = authenticated_v1_api_client.post(
+        f"/notes/{note.id}/share", json={"recipient": recipient}
+    )
+
+    assert response.status_code == HTTPStatus.ACCEPTED
+    assert len(mail.outbox) == 1
+    assert mail.outbox[0].body == note.body
+    assert mail.outbox[0].subject == f"Note shared: {note.title}"
+    assert mail.outbox[0].to == [recipient]
```

The build plan should wrap each diff hunk in the exact gate from this document.

## Verification evidence

Drift check:

```text
git diff --stat ae42991..HEAD -- "{{cookiecutter.project_slug}}/src/apps/notes/routes.py" "{{cookiecutter.project_slug}}/src/apps/core/tasks.py" "{{cookiecutter.project_slug}}/tests/core/unit/tasks_test.py" "{{cookiecutter.project_slug}}/README.md"
# no output
```

All required bakes used `/tmp/bake-020-*` paths. The specified
`localhost:5432` database URL was attempted first and failed because that local
port is owned by a different Postgres configuration. Verification used the
available `postgres:18.4` container (`bake-014-postgres`) on host port `55432`
with the same `postgres/postgres` credentials.

PoC tests:

```text
DATABASE_URL=postgres://postgres:postgres@localhost:55432/postgres uv run pytest
42 passed in 14.47s
Required test coverage of 100% reached. Total coverage: 100.00%
```

Gate-off tests:

```text
DATABASE_URL=postgres://postgres:postgres@localhost:55432/postgres uv run pytest
38 passed in 10.14s
Required test coverage of 100% reached. Total coverage: 100.00%
```

PoC pre-commit:

```text
git add -A && uv run pre-commit run --all-files
all hooks passed
```

## Open questions for the maintainer

1. Should the template ship this endpoint, or keep the async request pattern as
   README prose only?
2. Is `/notes/{id}/share` the right teaching action, or would `/notify` be less
   product-specific?
3. Is a plain `recipient: str` acceptable for an example, or is email validation
   worth an additional dependency or custom validator?
4. Are two extra CI bake cases acceptable for guarding the celery/email Jinja
   split with notes enabled?
5. If this endpoint ships, should `/ready` start checking the broker because
   request handlers can now enqueue tasks?
