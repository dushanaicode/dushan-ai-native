from pydantic_core import PydanticCustomError


class NotBlank:
    """校验非空白字符串，不替调用方清理或改变内容。"""

    @staticmethod
    def require_not_blank(field_name: str, value: str, error_msg: str | None = None) -> str:
        """拒绝非字符串、空串和纯空白字符串。"""
        if not isinstance(value, str) or not value.strip():
            raise PydanticCustomError(
                "value_error",
                error_msg if error_msg is not None else f"{field_name} 必须是非空白字符串",
            )
        return value
