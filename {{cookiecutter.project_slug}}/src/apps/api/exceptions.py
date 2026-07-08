from http import HTTPStatus

from ninja_extra.exceptions import APIException


class InvalidTokenError(APIException):
    status_code = HTTPStatus.UNAUTHORIZED
    default_detail = "Invalid token"
