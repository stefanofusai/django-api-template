from ninja import Schema


class ErrorSchema(Schema):
    detail: str


class ValidationErrorItem(Schema):
    ctx: dict[str, object] | None = None
    loc: list[str | int]
    msg: str
    type: str


class ValidationErrorSchema(Schema):
    detail: list[ValidationErrorItem]
