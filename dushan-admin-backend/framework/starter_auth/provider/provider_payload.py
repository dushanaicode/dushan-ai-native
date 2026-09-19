from framework.starter_auth.definitions.constants.auth_error_codes import AuthErrorCodes as Codes
from framework.starter_auth.exception.auth_exception import AuthException


class ProviderPayload:
    """第三方响应是外部输入，按字段契约验证，不回显字段原值。"""

    @staticmethod
    def text(data: dict, name: str, *, required: bool = False) -> str | None:
        value = data.get(name)
        if value is None and not required:
            return None
        if not isinstance(value, str) or (required and not value):
            raise AuthException(Codes.RESPONSE, outcome="unknown")
        return value

    @staticmethod
    def identifier(data: dict, name: str) -> str:
        value = data.get(name)
        if type(value) is int or (isinstance(value, str) and value):
            return str(value)
        raise AuthException(Codes.RESPONSE, outcome="unknown")

    @staticmethod
    def integer(data: dict, name: str, *, required: bool = False) -> int | None:
        value = data.get(name)
        if value is None and not required:
            return None
        if type(value) is int:
            return value
        if isinstance(value, str) and value.isascii() and value.isdecimal():
            return int(value)
        raise AuthException(Codes.RESPONSE, outcome="unknown")

    @staticmethod
    def object(data: dict, name: str) -> dict:
        value = data.get(name)
        if not isinstance(value, dict):
            raise AuthException(Codes.RESPONSE, outcome="unknown")
        return value

    @staticmethod
    def reject_errors(data: dict) -> None:
        if any(data.get(name) is not None for name in ("error", "error_response", "NSP_STATUS")):
            raise AuthException(Codes.REJECTED, outcome="rejected")
        for field in ("error_code", "errcode"):
            if field in data and ProviderPayload.integer(data, field, required=True) != 0:
                raise AuthException(Codes.REJECTED, outcome="rejected")

    @staticmethod
    def boolean(data: dict, name: str) -> bool | None:
        value = data.get(name)
        if value is not None and type(value) is not bool:
            raise AuthException(Codes.RESPONSE, outcome="unknown")
        return value
