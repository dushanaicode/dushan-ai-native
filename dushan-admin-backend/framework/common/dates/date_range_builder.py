from calendar import monthrange
from datetime import UTC, datetime, timedelta

from framework.common.enums.date_interval_enum import DateIntervalEnum


class DateRangeBuilder:
    """将同一时区的时间范围切成日历闭区间，支持日、周、月、季和年。"""

    @classmethod
    def build(
        cls,
        start_time: datetime,
        end_time: datetime,
        interval: DateIntervalEnum,
        *,
        max_segments: int,
    ) -> list[list[datetime]]:
        """保留首尾精确边界；相等边界产生一段，倒置范围直接报错。"""
        if not isinstance(interval, DateIntervalEnum):
            raise TypeError("interval 必须是 DateIntervalEnum")
        if start_time.tzinfo is None or end_time.tzinfo != start_time.tzinfo:
            raise ValueError("范围两端必须带同一时区")
        if start_time.astimezone(UTC) > end_time.astimezone(UTC):
            raise ValueError("开始时间不能晚于结束时间")
        if type(max_segments) is not int or max_segments <= 0:
            raise ValueError("最大分段数必须是正整数")
        result = []
        current = start_time
        while current.astimezone(UTC) <= end_time.astimezone(UTC):
            if len(result) >= max_segments:
                raise ValueError("日期范围分段数超过上限")
            end = min(cls.end_of_period(current, interval), end_time)
            result.append([current, end])
            if end == end_time:
                break
            current = end + timedelta(microseconds=1)
        return result

    @staticmethod
    def end_of_period(value: datetime, interval: DateIntervalEnum) -> datetime:
        """计算日历周期的最后一微秒，不构造超出 datetime 上限的下一年。"""
        end = value.replace(hour=23, minute=59, second=59, microsecond=999999)
        if interval is DateIntervalEnum.DAY:
            return end
        if interval is DateIntervalEnum.WEEK:
            remaining = (datetime.max.date() - value.date()).days
            return end + timedelta(days=min(6 - value.weekday(), remaining))
        if interval is DateIntervalEnum.MONTH:
            month = value.month
        elif interval is DateIntervalEnum.QUARTER:
            month = ((value.month - 1) // 3 + 1) * 3
        elif interval is DateIntervalEnum.YEAR:
            month = 12
        else:
            raise TypeError("interval 必须是 DateIntervalEnum")
        return end.replace(month=month, day=monthrange(value.year, month)[1])
