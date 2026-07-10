import runpy
from pathlib import Path
from typing import TYPE_CHECKING

from config.settings import env

if TYPE_CHECKING:
    from pytest_mock import MockerFixture

CACHE_SETTINGS = Path("src/config/settings/components/cache.py")


def test_cache_settings_bounds_django_redis_network_io(
    mocker: MockerFixture,
) -> None:
    mocker.patch.object(
        env,
        "cache",
        return_value={"BACKEND": "django_redis.cache.RedisCache"},
    )

    settings = runpy.run_path(str(CACHE_SETTINGS))

    assert settings["CACHES"]["default"]["OPTIONS"] == {
        "SOCKET_CONNECT_TIMEOUT": 1,
        "SOCKET_TIMEOUT": 1,
    }
