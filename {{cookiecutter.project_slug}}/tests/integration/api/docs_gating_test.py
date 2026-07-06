from http import HTTPStatus
from typing import TYPE_CHECKING

import pytest
from django.test import override_settings

from tests.factories import UserFactory

if TYPE_CHECKING:
    from django.test import Client

# This exercises the same decorator prod uses (staff_member_required, applied
# directly in protected_docs_urls.py), not `prod.py` itself: prod overlay
# settings modules are coverage-omitted and their decorator is resolved at
# import time in `apps/api/api.py`.


@pytest.mark.django_db
@override_settings(ROOT_URLCONF="tests.integration.api.protected_docs_urls")
def test_api_docs_redirect_anonymous_user_when_decorator_requires_staff(
    client: Client,
) -> None:
    response = client.get("/api/docs")

    assert response.status_code == HTTPStatus.FOUND
    assert response["Location"].startswith("/admin/login/")


@pytest.mark.django_db
@override_settings(ROOT_URLCONF="tests.integration.api.protected_docs_urls")
def test_api_docs_return_ok_for_staff_user_when_decorator_requires_staff(
    client: Client,
) -> None:
    staff_user = UserFactory.create(is_staff=True)
    client.force_login(staff_user)

    response = client.get("/api/docs")

    assert response.status_code == HTTPStatus.OK


@pytest.mark.django_db
@override_settings(ROOT_URLCONF="tests.integration.api.protected_docs_urls")
def test_openapi_schema_redirects_anonymous_user_when_decorator_requires_staff(
    client: Client,
) -> None:
    response = client.get("/api/openapi.json")

    assert response.status_code == HTTPStatus.FOUND
    assert response["Location"].startswith("/admin/login/")
