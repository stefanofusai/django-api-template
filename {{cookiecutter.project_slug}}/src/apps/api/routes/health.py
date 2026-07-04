from django.http import HttpRequest
from ninja import Router, Status

from apps.api.schemas import HealthOkSchema

router = Router(tags=["health"])


@router.get("/health", response={200: HealthOkSchema})
def health(
    request: HttpRequest,  # noqa: ARG001
) -> Status[HealthOkSchema]:
    return Status(200, HealthOkSchema(status="ok"))
