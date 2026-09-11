from typing import TypeVar

from pydantic_core import PydanticCustomError

T = TypeVar("T")


class DictKeys:
    """校验动态字典的键白名单，固定请求字段优先使用 Pydantic 模型。"""

    @staticmethod
    def require_allowed_keys(
        field_name: str,
        value: dict[str, T] | None,
        allowed_keys: frozenset[str],
        error_msg: str | None = None,
    ) -> dict[str, T] | None:
        """拒绝非字典以及白名单之外的字段，不回显未知字段值。"""
        if value is None:
            return None
        if not isinstance(value, dict) or not set(value).issubset(allowed_keys):
            raise PydanticCustomError(
                "value_error",
                error_msg if error_msg is not None else f"{field_name} 必须是只包含允许字段的对象",
            )
        return value
