from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field

from framework.starter_auth.definitions.constants.auth_error_codes import AuthErrorCodes as Codes
from framework.starter_auth.exception.auth_exception import AuthException


@dataclass(frozen=True, slots=True)
class AuthCallback:
    state: str = field(repr=False)
    code: str = field(repr=False)
    denied: bool = False

    @classmethod
    def parse(cls, pairs: Iterable[tuple[str, str]], *, code_parameter: str, client_id: str):
        """接收 query/form 的 multi_items，拒绝重复参数与成功/失败混合响应。"""
        values = {}
        if not isinstance(pairs, Iterable) or isinstance(pairs, (Mapping, str, bytes)):
            raise AuthException(Codes.INPUT)
        for pair in pairs:
            if not isinstance(pair, (tuple, list)) or len(pair) != 2:
                raise AuthException(Codes.INPUT)
            key, value = pair
            if (
                not isinstance(key, str)
                or not isinstance(value, str)
                or key in values
                or len(values) >= 32
                or len(key) > 128
                or len(value) > 8192
            ):
                raise AuthException(Codes.INPUT)
            values[key] = value
        state = values.get("state", "")
        code = values.get(code_parameter, "")
        denied = "error" in values
        if denied and code or not denied and not code:
            raise AuthException(Codes.INPUT)
        if "app_id" in values and values["app_id"] != client_id:
            raise AuthException(Codes.BINDING)
        return cls(state=state, code=code, denied=denied)
