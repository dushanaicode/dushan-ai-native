from framework.common.enums.base_enum import BaseEnum


class DateIntervalEnum(BaseEnum):
    """日期范围使用的时间单位。"""

    DAY = (1, "天")
    WEEK = (2, "周")
    MONTH = (3, "月")
    QUARTER = (4, "季度")
    YEAR = (5, "年")
