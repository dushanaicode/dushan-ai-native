from pydantic_core import PydanticCustomError

from framework.common.utils.validation_utils import ValidationUtils


class Email:
    """校验常用 ASCII 邮箱格式，不校验地址真实性。"""

    @staticmethod
    def require_email(
        field_name: str, value: str | None, error_msg: str | None = None
    ) -> str | None:
        """允许可选值 None，其余值必须是符合契约的字符串。"""
        if value is None:
            return None
        if not isinstance(value, str) or not ValidationUtils.validate_email(value):
            raise PydanticCustomError(
                "value_error",
                error_msg if error_msg is not None else f"{field_name} 必须是有效的邮箱格式",
            )
        return value
