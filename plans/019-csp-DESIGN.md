# CSP Design Spike

## Recommendation

Do not ship CSP as a default in this plan. Keep the request-ID hardening as the
mergeable change and revisit CSP as an explicit follow-up after the maintainer
chooses between an opt-in knob and a narrow custom middleware.

The practical default is not obvious enough to add silently:

- The template intentionally avoids browser policy defaults without a concrete
  consumer policy.
- The only HTML surfaces are staff-gated admin and Django Ninja docs.
- Swagger UI needs script/style allowances that weaken a strict policy.
- `django-csp==4.0` currently advertises Django classifiers only through 5.2 and
  Python classifiers only through 3.13, while this template targets Django 6 and
  Python 3.14.

## Minimal Working Shape

The conservative policy to prototype for a future opt-in is:

```python
CSP_DEFAULT_SRC = ("'self'",)
CSP_IMG_SRC = ("'self'", "data:")
CSP_SCRIPT_SRC = ("'self'", "'unsafe-inline'")
CSP_STYLE_SRC = ("'self'", "'unsafe-inline'")
```

This is Swagger-compatible in shape because Django Ninja's docs UI relies on
inline script/style behavior. It is not strict enough to justify always-on
adoption without an operator policy.

## Implementation Options

Option A: `use_csp` bake knob, default `no`.

This preserves the template's current minimalism and gives operators a reviewed
starting point. It would add a dependency or a small custom middleware only when
requested.

Option B: custom middleware scoped to `/admin/` and `/api/docs`.

This avoids a dependency, but it creates local security-policy ownership and
must be re-tested on every Django admin or Django Ninja docs UI change.

Option C: always-on `django-csp`.

Rejected for now. The dependency metadata has not caught up to the template's
Django/Python targets, and an always-on Swagger-compatible policy still needs
inline allowances.

## Verification Notes

A future implementation should bake default and `use_example_api=yes`, create a
staff user, load `/admin/` and `/api/docs`, and verify the browser console has
no CSP violations. It should also run the full baked suite and pre-commit.

## Open Decision

Choose one direction before implementation:

- opt-in `use_csp` knob,
- custom scoped middleware,
- document-only posture until a real browser policy exists.
