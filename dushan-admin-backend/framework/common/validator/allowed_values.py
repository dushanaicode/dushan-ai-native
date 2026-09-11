from collections.abc import Callable, Collection, Hashable, Sequence
from typing import TypeVar

from pydantic_core import PydanticCustomError

T = TypeVar("T", bound=Sequence[Hashable])


class AllowedValues:
    """校验序列成员白名单；元素应已通过字段类型校验。"""

    @staticmethod
    def require_allowed_values(
        field_name: str,
        value: T | None,
        allowed_values: Collection[Hashable],
        error_msg_factory: Callable[[frozenset[Hashable]], str] | None = None,
    ) -> T | None:
        """拒绝白名单之外的成员，默认提示不回显输入内容。"""
        if value is None:
            return None
        unsupported = frozenset(value).difference(allowed_values)
        if unsupported:
            message = (
                error_msg_factory(unsupported)
                if error_msg_factory is not None
                else f"{field_name} 包含不允许的值"
            )
            raise PydanticCustomError("value_error", message)
        return value
