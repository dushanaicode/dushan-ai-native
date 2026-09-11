from datetime import datetime

from pydantic_core import PydanticCustomError


class DateTimeFormat:
    """按调用方明确提供的格式校验日期，不创建全局日期工具或使用隐藏默认格式。"""

    @staticmethod
    def require_datetime_format(
        field_name: str, value: str | None, patterns: list[str], error_msg: str | None = None
    ) -> str | None:
        """允许显式列出的多种输入格式，全部失败才报告字段错误。"""
        if not patterns:
            raise ValueError("日期格式列表不能为空")
        if value is None:
            return None
        if isinstance(value, str):
            for pattern in patterns:
                try:
                    datetime.strptime(value, pattern)
                except ValueError:
                    continue
                return value
        raise PydanticCustomError(
            "value_error", error_msg if error_msg is not None else f"{field_name} 日期格式不正确"
        )

    @staticmethod
    def parse_comma_separated_range(
        input_value: str | None, *, pattern: str
    ) -> list[datetime] | None:
        """用明确格式解析两个时间点并验证顺序；无时区格式产生 naive datetime。"""
        if input_value is None:
            return None
        if not isinstance(input_value, str):
            raise PydanticCustomError("value_error", "时间范围必须是字符串")
        parts = input_value.split(",")
        if len(parts) != 2:
            raise PydanticCustomError("value_error", "时间范围必须包含两个时间点")
        try:
            start, end = (datetime.strptime(part.strip(), pattern) for part in parts)
        except ValueError as exc:
            raise PydanticCustomError("value_error", "时间范围格式不正确") from exc
        if start > end:
            raise PydanticCustomError("value_error", "开始时间不能晚于结束时间")
        return [start, end]
