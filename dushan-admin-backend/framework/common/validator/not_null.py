from typing import TypeVar

from pydantic_core import PydanticCustomError

T = TypeVar("T")


class NotNull:
    """校验必填值；可在 Pydantic field_validator 中调用，保留字段错误位置。"""

    @staticmethod
    def require_not_null(field_name: str, value: T | None, error_msg: str | None = None) -> T:
        """拒绝 None，保留 0、False 和空集合的原值。"""
        if value is None:
            raise PydanticCustomError(
                "value_error", error_msg if error_msg is not None else f"{field_name} 不能为空"
            )
        return value
