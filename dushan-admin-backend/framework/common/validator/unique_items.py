from collections.abc import Hashable, Sequence
from typing import TypeVar

from pydantic_core import PydanticCustomError

T = TypeVar("T", bound=Sequence[Hashable])


class UniqueItems:
    """校验可哈希元素的序列唯一性，保留输入顺序和容器。"""

    @staticmethod
    def require_unique(field_name: str, value: T, error_msg: str | None = None) -> T:
        """发现重复元素时报告字段错误。"""
        if len(value) != len(set(value)):
            raise PydanticCustomError(
                "value_error",
                error_msg if error_msg is not None else f"{field_name} 的元素不能重复",
            )
        return value
