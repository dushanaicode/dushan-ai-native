from decimal import Decimal, localcontext

from framework.starter_excel.model.conversion_context import ConversionContext


class MoneyConverter:
    """整数分与元文本互转；拒绝不足一分的金额，不隐式四舍五入或截断。"""

    async def to_excel(self, value: int, context: ConversionContext) -> str:
        if type(value) is not int:
            raise ValueError("金额必须是整数分")
        with localcontext() as decimal_context:
            decimal_context.prec = max(28, len(str(abs(value))) + 10)
            return f"{Decimal(value) / 100:.{context.settings.money_decimal_places}f}"

    async def to_python(self, value: str | int | float, context: ConversionContext) -> int:
        if isinstance(value, bool):
            raise ValueError("布尔值不是金额")
        amount = Decimal(str(value))
        if not amount.is_finite():
            raise ValueError("金额必须是有限数值")
        if amount.is_zero():
            return 0
        # 在 Decimal 上下文运算前拒绝非零不足一分，避免极小指数下溢成零。
        if amount.adjusted() < -2:
            raise ValueError("金额精度不能小于一分")
        # 指数文本可能很短；先限制展开后的分位数，再创建整数。
        if amount.adjusted() + 3 > context.settings.max_cell_text_length:
            raise ValueError("金额展开后的位数超过单元格文本上限")
        with localcontext() as decimal_context:
            decimal_context.prec = max(28, len(amount.as_tuple().digits) + 2)
            cents = amount * 100
            if cents != cents.to_integral_value():
                raise ValueError("金额精度不能小于一分")
            return int(cents)
