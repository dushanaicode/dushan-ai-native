from decimal import Decimal

from pydantic_core import PydanticCustomError

from framework.common.validator.range import Number


class DecimalMin:
    """按十进制比较有限数值；金额字段建议声明为 Decimal。"""

    @staticmethod
    def require_decimal_min(
        field_name: str,
        value: Number | None,
        min_value: Number,
        inclusive: bool = True,
        error_msg: str | None = None,
    ) -> Number | None:
        """按十进制文本表示比较，不接受数值字符串或修改输入类型。"""
        if type(min_value) not in (int, float, Decimal) or not Decimal(str(min_value)).is_finite():
            raise ValueError("最小值必须是有限数值")
        if value is None:
            return None
        # 先检查原始值，避免 bool 等非数值被 str 转换后蒙混过关。
        if type(value) not in (int, float, Decimal) or not Decimal(str(value)).is_finite():
            raise PydanticCustomError(
                "value_error",
                error_msg if error_msg is not None else f"{field_name} 必须是有限数值",
            )
        number, minimum = Decimal(str(value)), Decimal(str(min_value))
        if number < minimum or not inclusive and number == minimum:
            comparison = "大于或等于" if inclusive else "大于"
            raise PydanticCustomError(
                "value_error",
                error_msg
                if error_msg is not None
                else f"{field_name} 必须{comparison} {min_value}",
            )
        return value
