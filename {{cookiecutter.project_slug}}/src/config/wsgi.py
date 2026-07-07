# Retained only as the entrypoint for the API contract test
# (tests/api/integration/schema_test.py). Production serves ASGI via
# config.asgi; this WSGI app is never used at runtime. The OpenAPI schema
# is identical under either protocol, and Schemathesis' ASGI transport runs
# the ASGI lifespan protocol, which Django's ASGIHandler rejects — so the
# schema test loads this WSGI app instead.
from django.core.wsgi import get_wsgi_application

application = get_wsgi_application()
