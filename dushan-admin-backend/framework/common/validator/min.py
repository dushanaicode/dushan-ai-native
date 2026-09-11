from framework.common.validator.range import Number, Range


class Min:
    """校验数值下限，不按边界类型截断或转换输入值。"""

    @staticmethod
    def require_min(
        field_name: str, value: Number | None, min_value: Number, error_msg: str | None = None
    ) -> Number | None:
        """确认数值不小于指定下限。"""
        return Range.require_range(field_name, value, min_value=min_value, error_msg=error_msg)
