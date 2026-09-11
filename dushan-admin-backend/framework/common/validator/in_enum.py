from enum import Enum
from typing import TypeVar

from pydantic_core import PydanticCustomError

T = TypeVar("T")


class InEnum:
    """按枚举成员的实际值校验；转换由 Pydantic 完成，不猜测首成员类型。"""

    @staticmethod
    def require_in_enum(
        field_name: str, value: T | None, enum_class: type[Enum], error_msg: str | None = None
    ) -> T | None:
        """按类型和值同时匹配枚举编码，不把 True、1.0 或 '1' 当作整数 1。"""
        if value is None:
            return None
        if not any(
            type(value) is type(member.value) and value == member.value for member in enum_class
        ):
            raise PydanticCustomError(
                "value_error",
                error_msg if error_msg is not None else f"{field_name} 必须使用允许的枚举值",
            )
        return value
