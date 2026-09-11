from pydantic_core import PydanticCustomError

from framework.common.utils.validation.validation_utils import ValidationUtils


class Mobile:
    """校验中国大陆手机号基本格式，不推断运营商或是否已开户。"""

    @staticmethod
    def require_mobile(
        field_name: str, value: str | None, error_msg: str | None = None
    ) -> str | None:
        """允许可选值 None，其余值必须是符合契约的字符串。"""
        if value is None:
            return None
        if not isinstance(value, str) or not ValidationUtils.validate_mobile(value):
            raise PydanticCustomError(
                "value_error",
                error_msg if error_msg is not None else f"{field_name} 必须是中国大陆手机号格式",
            )
        return value
