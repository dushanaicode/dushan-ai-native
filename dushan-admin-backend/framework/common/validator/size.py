from collections.abc import Sized
from typing import TypeVar

from pydantic_core import PydanticCustomError

T = TypeVar("T", bound=Sized)


class Size:
    """校验容器长度；None 表示未提供可选值，空串仍参与长度校验。"""

    @staticmethod
    def require_size(
        field_name: str,
        value: T | None,
        min_length: int | None = None,
        max_length: int | None = None,
        error_msg: str | None = None,
    ) -> T | None:
        """按明确的长度上下限校验字符串或集合。"""
        if min_length is None and max_length is None:
            raise ValueError("至少指定一个长度边界")
        if min_length is not None and min_length < 0 or max_length is not None and max_length < 0:
            raise ValueError("长度边界不能为负数")
        if min_length is not None and max_length is not None and min_length > max_length:
            raise ValueError("最小长度不能大于最大长度")
        if value is None:
            return None
        if not isinstance(value, Sized):
            raise PydanticCustomError(
                "value_error",
                error_msg if error_msg is not None else f"{field_name} 必须是字符串或集合",
            )
        length = len(value)
        if min_length is not None and length < min_length:
            raise PydanticCustomError(
                "value_error",
                error_msg if error_msg is not None else f"{field_name} 长度不能小于 {min_length}",
            )
        if max_length is not None and length > max_length:
            raise PydanticCustomError(
                "value_error",
                error_msg if error_msg is not None else f"{field_name} 长度不能超过 {max_length}",
            )
        return value
