from typing import Literal

from ninja import Schema

ReadyError = Literal["cache", "database"]


class ReadyErrorSchema(Schema):
    status: Literal["error"]
    errors: list[ReadyError]


class ReadyOkSchema(Schema):
    status: Literal["ok"]
