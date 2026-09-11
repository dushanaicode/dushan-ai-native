from pydantic_core import PydanticCustomError

from framework.common.utils.validation.validation_utils import ValidationUtils


class URL:
    """校验完整 HTTP(S) URL；主机名不是 URL，语法通过也不代表可安全发起网络请求。"""

    @staticmethod
    def require_url(field_name: str, value: str | None, error_msg: str | None = None) -> str | None:
        """允许可选值 None，其余值必须是符合契约的字符串。"""
        if value is None:
            return None
        if not isinstance(value, str) or not ValidationUtils.is_url(value):
            raise PydanticCustomError(
                "value_error",
                error_msg if error_msg is not None else f"{field_name} 必须是完整 HTTP(S) URL",
            )
        return value
