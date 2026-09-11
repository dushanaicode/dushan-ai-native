from framework.common.validator.range import Number, Range


class PositiveOrZero:
    """校验非负数，布尔值不属于数值契约。"""

    @staticmethod
    def require_positive_or_zero(
        field_name: str, value: Number | None, error_msg: str | None = None
    ) -> Number | None:
        """确认数值大于或等于零。"""
        return Range.require_range(field_name, value, min_value=0, error_msg=error_msg)
