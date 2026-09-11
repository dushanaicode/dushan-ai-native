from pydantic_core import PydanticCustomError

from framework.common.validator.size import Size


class Length:
    """校验字符串长度，保留原始字符串。"""

    @staticmethod
    def require_length(
        field_name: str,
        value: str | None,
        min_length: int,
        max_length: int,
        error_msg: str | None = None,
    ) -> str | None:
        """按字符数校验闭区间，字节长度应由调用方另行定义。"""
        if value is not None and not isinstance(value, str):
            raise PydanticCustomError(
                "value_error", error_msg if error_msg is not None else f"{field_name} 必须是字符串"
            )
        return Size.require_size(field_name, value, min_length, max_length, error_msg)
