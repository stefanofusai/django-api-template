from typing import Literal

from ninja import Schema


class HealthOkSchema(Schema):
    status: Literal["ok"]
