from typing import Literal

from ninja import Schema

{% if cookiecutter.use_celery != "none" -%}
ReadyError = Literal["broker", "cache", "database"]
{% else -%}
ReadyError = Literal["cache", "database"]
{% endif %}

class ReadyErrorSchema(Schema):
    status: Literal["error"]
    errors: list[ReadyError]


class ReadyOkSchema(Schema):
    status: Literal["ok"]
