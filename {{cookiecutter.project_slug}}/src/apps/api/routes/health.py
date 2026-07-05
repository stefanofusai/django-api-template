from django.http import HttpRequest
from ninja import Router, Status

from apps.api.schemas import HealthOkSchema

router = Router(tags=["health"])


# Liveness only, by design: no database or cache I/O. The container
# healthcheck restarts on failure here, so dependency outages must NOT fail
# this route — that is /ready's job (load balancers, not restarts).
@router.get("/health", response={200: HealthOkSchema})
def health(
    request: HttpRequest,  # noqa: ARG001
) -> Status[HealthOkSchema]:
    return Status(200, HealthOkSchema(status="ok"))
