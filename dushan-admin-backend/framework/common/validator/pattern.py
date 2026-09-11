import re

from pydantic_core import PydanticCustomError


class Pattern:
    """校验可信源码定义的正则；不执行请求方提供的任意正则表达式。"""

    @staticmethod
    def require_pattern(
        field_name: str, value: str | None, pattern: str, error_msg: str | None = None
    ) -> str | None:
        """匹配整个字符串，避免只匹配前缀而放过多余内容。"""
        if value is None:
            return None
        if not isinstance(value, str) or re.fullmatch(pattern, value) is None:
            raise PydanticCustomError(
                "value_error", error_msg if error_msg is not None else f"{field_name} 格式不正确"
            )
        return value
