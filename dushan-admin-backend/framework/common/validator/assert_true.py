from pydantic_core import PydanticCustomError


class AssertTrue:
    """校验明确的布尔同意值，不把数字或非空字符串当作 True。"""

    @staticmethod
    def require_true(field_name: str, value: bool, error_msg: str | None = None) -> bool:
        """只允许布尔值 True。"""
        if value is not True:
            raise PydanticCustomError(
                "value_error", error_msg if error_msg is not None else f"{field_name} 必须为 True"
            )
        return value
