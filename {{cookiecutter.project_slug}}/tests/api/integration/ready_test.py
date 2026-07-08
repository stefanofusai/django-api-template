from http import HTTPStatus
from typing import TYPE_CHECKING

import pytest
from django.db import DatabaseError
from redis.exceptions import RedisError

from apps.api.routes import ready as ready_route

if TYPE_CHECKING:
    from ninja.testing import TestClient
    from pytest_mock import MockerFixture


def test_ready_endpoint_returns_cache_error_when_cache_raises(
    internal_api_client: TestClient,
    mocker: MockerFixture,
) -> None:
    mocker.patch.object(ready_route, "_database_ready", return_value=True)
    cache_set = mocker.patch.object(ready_route.cache, "set", side_effect=RedisError)

    response = internal_api_client.get("/ready")

    assert response.status_code == HTTPStatus.SERVICE_UNAVAILABLE
    assert response.data == {"status": "error", "errors": ["cache"]}
    cache_set.assert_called_once_with("ready-check", "ok", timeout=1)


def test_ready_endpoint_returns_cache_error_when_cache_readback_mismatches(
    internal_api_client: TestClient,
    mocker: MockerFixture,
) -> None:
    mocker.patch.object(ready_route, "_database_ready", return_value=True)
    mocker.patch.object(ready_route.cache, "set", return_value=None)
    cache_get = mocker.patch.object(ready_route.cache, "get", return_value="stale")

    response = internal_api_client.get("/ready")

    assert response.status_code == HTTPStatus.SERVICE_UNAVAILABLE
    assert response.data == {"status": "error", "errors": ["cache"]}
    cache_get.assert_called_once_with("ready-check")


def test_ready_endpoint_returns_cache_error_when_cache_set_fails(
    internal_api_client: TestClient,
    mocker: MockerFixture,
) -> None:
    mocker.patch.object(ready_route, "_database_ready", return_value=True)
    cache_set = mocker.patch.object(ready_route.cache, "set", return_value=False)
    cache_get = mocker.patch.object(ready_route.cache, "get")

    response = internal_api_client.get("/ready")

    assert response.status_code == HTTPStatus.SERVICE_UNAVAILABLE
    assert response.data == {"status": "error", "errors": ["cache"]}
    cache_set.assert_called_once_with("ready-check", "ok", timeout=1)
    cache_get.assert_not_called()


def test_ready_endpoint_returns_database_error_when_connection_raises(
    internal_api_client: TestClient,
    mocker: MockerFixture,
) -> None:
    connection = ready_route.connections["default"]
    ensure_connection = mocker.patch.object(
        connection, "ensure_connection", side_effect=DatabaseError
    )

    response = internal_api_client.get("/ready")

    assert response.status_code == HTTPStatus.SERVICE_UNAVAILABLE
    assert response.data == {"status": "error", "errors": ["database"]}
    ensure_connection.assert_called_once_with()


{% if cookiecutter.use_celery != "none" -%}
def test_broker_ready_returns_true_when_broker_accepts_connection(
    mocker: MockerFixture,
) -> None:
    # The autouse `_broker_ready_default` fixture (conftest.py) replaces this
    # module's `_broker_ready` wholesale so unrelated tests default to a
    # healthy broker; undo it here to exercise the real implementation.
    mocker.stopall()
    connection = mocker.MagicMock()
    connection_context = mocker.MagicMock()
    connection_context.__enter__.return_value = connection
    connection_for_read = mocker.patch.object(
        ready_route.app, "connection_for_read", return_value=connection_context
    )

    assert ready_route._broker_ready() is True  # noqa: SLF001
    connection_for_read.assert_called_once_with()
    connection.ensure_connection.assert_called_once_with(max_retries=0, timeout=1)


def test_ready_endpoint_returns_broker_error_when_broker_is_unreachable(
    internal_api_client: TestClient,
    mocker: MockerFixture,
) -> None:
    # See the comment in test_broker_ready_returns_true_when_broker_accepts_
    # connection: undo the autouse default so the endpoint runs the real
    # _broker_ready() and surfaces the patched connection failure below.
    mocker.stopall()
    mocker.patch.object(ready_route, "_cache_ready", return_value=True)
    mocker.patch.object(ready_route, "_database_ready", return_value=True)
    connection_for_read = mocker.patch.object(
        ready_route.app,
        "connection_for_read",
        side_effect=ready_route.OperationalError("broker unreachable"),
    )

    response = internal_api_client.get("/ready")

    assert response.status_code == HTTPStatus.SERVICE_UNAVAILABLE
    assert response.data == {"status": "error", "errors": ["broker"]}
    connection_for_read.assert_called_once_with()


def test_ready_endpoint_returns_error_when_dependencies_are_unavailable(
    internal_api_client: TestClient, mocker: MockerFixture
) -> None:
    cache_ready = mocker.patch.object(ready_route, "_cache_ready", return_value=False)
    database_ready = mocker.patch.object(
        ready_route, "_database_ready", return_value=False
    )
    broker_ready = mocker.patch.object(ready_route, "_broker_ready", return_value=False)

    response = internal_api_client.get("/ready")

    assert response.status_code == HTTPStatus.SERVICE_UNAVAILABLE
    assert response.data == {
        "status": "error",
        "errors": ["broker", "cache", "database"],
    }
    cache_ready.assert_called_once_with()
    database_ready.assert_called_once_with()
    broker_ready.assert_called_once_with()


@pytest.mark.django_db
def test_ready_endpoint_returns_ok_when_dependencies_are_available(
    internal_api_client: TestClient,
) -> None:
    response = internal_api_client.get("/ready")

    assert response.status_code == HTTPStatus.OK
    assert response.data == {"status": "ok"}
{% else -%}
def test_ready_endpoint_returns_error_when_dependencies_are_unavailable(
    internal_api_client: TestClient, mocker: MockerFixture
) -> None:
    cache_ready = mocker.patch.object(ready_route, "_cache_ready", return_value=False)
    database_ready = mocker.patch.object(
        ready_route, "_database_ready", return_value=False
    )

    response = internal_api_client.get("/ready")

    assert response.status_code == HTTPStatus.SERVICE_UNAVAILABLE
    assert response.data == {"status": "error", "errors": ["cache", "database"]}
    cache_ready.assert_called_once_with()
    database_ready.assert_called_once_with()


@pytest.mark.django_db
def test_ready_endpoint_returns_ok_when_dependencies_are_available(
    internal_api_client: TestClient,
) -> None:
    response = internal_api_client.get("/ready")

    assert response.status_code == HTTPStatus.OK
    assert response.data == {"status": "ok"}
{% endif -%}
