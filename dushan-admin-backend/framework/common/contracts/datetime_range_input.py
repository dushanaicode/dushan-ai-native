from datetime import UTC, datetime
from typing import Any, Self

from pydantic import GetCoreSchemaHandler
from pydantic_core import CoreSchema, core_schema


class DateTimeRangeInput(tuple[datetime, datetime]):
    """校验两端日期闭区间，保持 JSON 数组和重复查询参数的输入形式。

    无时区输入按 UTC 解释；带偏移输入转为数据库使用的 UTC naive 时间。
    继承 tuple 使 FastAPI 能在可空字段中识别并收集重复查询参数。
    """

    @classmethod
    def __get_pydantic_core_schema__(
        cls, source_type: Any, handler: GetCoreSchemaHandler
    ) -> CoreSchema:
        """让 Pydantic 先校验恰好两个日期，再统一时区和检查顺序。"""
        return core_schema.no_info_after_validator_function(
            cls.validate, handler(tuple[datetime, datetime])
        )

    @classmethod
    def validate(cls, value: tuple[datetime, datetime]) -> Self:
        """按实际时刻比较起止时间，允许两端相等。"""
        try:
            start, end = (
                item.astimezone(UTC).replace(tzinfo=None) if item.tzinfo is not None else item
                for item in value
            )
        except OverflowError as error:
            raise ValueError("时间范围超出 UTC 日期支持范围") from error
        if start > end:
            raise ValueError("开始时间不能晚于结束时间")
        return cls((start, end))
