from ninja import Schema


class ValidationErrorItemSchema(Schema):
    type: str
    loc: list[int | str]
    msg: str


class ValidationErrorSchema(Schema):
    detail: list[ValidationErrorItemSchema]
