from decimal import Decimal
from math import isfinite

from pydantic_core import PydanticCustomError

type Number = int | float | Decimal


class Range:
    """校验有限数值的边界；字符串转换由 Pydantic 字段类型负责。"""

    @staticmethod
    def require_range(
        field_name: str,
        value: Number | None,
        min_value: Number | None = None,
        max_value: Number | None = None,
        error_msg: str | None = None,
    ) -> Number | None:
        """校验闭区间，拒绝 bool、NaN 和无穷大。"""
        if min_value is None and max_value is None:
            raise ValueError("至少指定一个数值边界")
        for bound in (min_value, max_value):
            if bound is not None and (
                type(bound) not in (int, float, Decimal)
                or isinstance(bound, float)
                and not isfinite(bound)
                or isinstance(bound, Decimal)
                and not bound.is_finite()
            ):
                raise ValueError("数值边界必须是有限数值")
        if min_value is not None and max_value is not None and min_value > max_value:
            raise ValueError("最小值不能大于最大值")
        if value is None:
            return None
        if (
            type(value) not in (int, float, Decimal)
            or isinstance(value, float)
            and not isfinite(value)
            or isinstance(value, Decimal)
            and not value.is_finite()
        ):
            raise PydanticCustomError(
                "value_error",
                error_msg if error_msg is not None else f"{field_name} 必须是有限数值",
            )
        if min_value is not None and value < min_value:
            raise PydanticCustomError(
                "value_error",
                error_msg if error_msg is not None else f"{field_name} 不能小于 {min_value}",
            )
        if max_value is not None and value > max_value:
            raise PydanticCustomError(
                "value_error",
                error_msg if error_msg is not None else f"{field_name} 不能大于 {max_value}",
            )
        return value
