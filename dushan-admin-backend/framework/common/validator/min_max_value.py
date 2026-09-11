from framework.common.validator.range import Number, Range


class MinMaxValue:
    """校验必须同时指定上下限的数值闭区间。"""

    @staticmethod
    def require_min_max(
        field_name: str,
        value: Number | None,
        min_val: Number,
        max_val: Number,
        error_msg: str | None = None,
    ) -> Number | None:
        """确认数值处于给定的闭区间。"""
        return Range.require_range(field_name, value, min_val, max_val, error_msg)
