from collections.abc import Sized
from typing import TypeVar

from pydantic_core import PydanticCustomError

T = TypeVar("T", bound=Sized)


class NotEmpty:
    """校验字符串或集合至少包含一个元素，空白字符串交给 NotBlank。"""

    @staticmethod
    def require_not_empty(field_name: str, value: T, error_msg: str | None = None) -> T:
        """拒绝 None、非容器和长度为零的值，不吞掉容器自身的异常。"""
        if not isinstance(value, Sized) or len(value) == 0:
            raise PydanticCustomError(
                "value_error",
                error_msg if error_msg is not None else f"{field_name} 不能为空集合或空串",
            )
        return value
