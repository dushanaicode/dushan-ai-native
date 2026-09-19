from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from framework.common.dates.date_range_builder import DateRangeBuilder
from framework.common.dates.datetime_options import DateTimeOptions
from framework.common.enums.date_interval_enum import DateIntervalEnum


class DateUtils:
    """按实例配置处理日期、格式、时间戳和日历范围。

    DateUtils(options) 必须显式注入配置；naive 时间始终解释为配置时区。
    DST 跳时或重复时刻必须由调用方提供带偏移时间，不猜测实际发生的瞬间。
    可选日期仅在明确允许 None 的方法中保持 None，解析失败不会返回空值。
    """

    def __init__(self, options: DateTimeOptions):
        """保存当前应用自己的日期配置与时区对象。"""
        self._options = options
        self._timezone = ZoneInfo(options.timezone)

    def get_timezone_name(self) -> str:
        """返回配置中的 IANA 时区名。"""
        return self._options.timezone

    def get_datetime_format(self) -> str:
        """返回配置中的日期时间显示格式。"""
        return self._options.format

    def get_timezone(self) -> ZoneInfo:
        """返回本实例的时区对象。"""
        return self._timezone

    def get_timezone_offset(self) -> float:
        """返回当前 UTC 偏移小时数，保留半小时或四分之一小时偏移。"""
        return self.now().utcoffset().total_seconds() / 3600

    def now(self) -> datetime:
        """返回配置时区的带时区当前时间。"""
        return datetime.now(self._timezone)

    def now_naive(self) -> datetime:
        """显式移除配置时区标识，仅用于接收 naive 时间的调用边界。"""
        return self.now().replace(tzinfo=None)

    def localize(self, value: datetime | None) -> datetime | None:
        """将 naive 时间解释为本地时间，拒绝不存在或有歧义的 DST 时刻。"""
        if value is None or value.tzinfo is not None:
            return value
        localized = value.replace(tzinfo=self._timezone)
        roundtrip = localized.astimezone(UTC).astimezone(self._timezone).replace(tzinfo=None)
        if (
            roundtrip != value
            or localized.utcoffset() != localized.replace(fold=1 - localized.fold).utcoffset()
        ):
            raise ValueError("本地时间不存在或存在 DST 歧义，请提供带偏移的时间")
        return localized

    def to_timezone(self, value: datetime | None) -> datetime | None:
        """把时间转换为配置时区，naive 输入与 localize 使用相同解释。"""
        return None if value is None else self.localize(value).astimezone(self._timezone)

    def to_utc(self, value: datetime | None) -> datetime | None:
        """将本地或带时区的时间转换为 UTC。"""
        return None if value is None else self.localize(value).astimezone(UTC)

    def build_time(
        self, year: int, month: int, day: int, hour: int = 0, minute: int = 0, second: int = 0
    ) -> datetime:
        """用明确的日历分量构造本地时间，省略的时分秒表示零点。"""
        return self.localize(datetime(year, month, day, hour, minute, second))

    def build_between_time(
        self, year1: int, month1: int, day1: int, year2: int, month2: int, day2: int
    ) -> list[datetime]:
        """构造并校验两个本地零点组成的范围。"""
        start, end = self.build_time(year1, month1, day1), self.build_time(year2, month2, day2)
        if start > end:
            raise ValueError("开始日期不能晚于结束日期")
        return [start, end]

    def format_datetime(self, value: datetime | None, format_str: str | None = None) -> str | None:
        """转换到配置时区后格式化，调用方可明确指定本次格式。"""
        if value is None:
            return None
        return self.to_timezone(value).strftime(
            self._options.format if format_str is None else format_str
        )

    def format_datetime_iso(self, value: datetime | None) -> str | None:
        """输出含 UTC 偏移的 ISO 8601 日期文本。"""
        return None if value is None else self.to_timezone(value).isoformat()

    def parse_datetime(self, value: str, format_str: str | None = None) -> datetime:
        """按指定格式解析，未指定时使用注入的 YAML 格式。"""
        parsed = datetime.strptime(
            value, self._options.format if format_str is None else format_str
        )
        return self.to_timezone(parsed)

    def parse_isoformat(self, value: str | None) -> datetime | None:
        """解析 ISO 8601 并归一到配置时区，非法内容直接报错。"""
        return None if value is None else self.to_timezone(datetime.fromisoformat(value))

    def add_time(self, duration: timedelta) -> datetime:
        """按本地日历时间增加给定时长。"""
        return self.now() + duration

    def minus_time(self, duration: timedelta) -> datetime:
        """按本地日历时间减去给定时长。"""
        return self.now() - duration

    def now_plus_seconds(self, seconds: int) -> datetime:
        """按实际经过的秒数增加时间，跨 DST 时使用 UTC 计算。"""
        return (self.now().astimezone(UTC) + timedelta(seconds=seconds)).astimezone(self._timezone)

    def before_now(self, value: datetime) -> bool:
        """按实际瞬间判断是否早于现在。"""
        return self.to_utc(value) < self.now().astimezone(UTC)

    def after_now(self, value: datetime) -> bool:
        """按实际瞬间判断是否晚于现在。"""
        return self.to_utc(value) > self.now().astimezone(UTC)

    def is_expired(self, expiry_time: datetime | None) -> bool:
        """无有效期限视为过期，到期瞬间也视为过期。"""
        return expiry_time is None or self.to_utc(expiry_time) <= self.now().astimezone(UTC)

    def is_same_day(self, first: datetime, second: datetime) -> bool:
        """按配置时区判断两个时间是否属于同一天。"""
        return self.to_timezone(first).date() == self.to_timezone(second).date()

    def is_today(self, value: datetime) -> bool:
        """按配置时区判断是否是今天。"""
        return self.to_timezone(value).date() == self.now().date()

    def is_yesterday(self, value: datetime) -> bool:
        """按配置时区判断是否是昨天。"""
        return self.to_timezone(value).date() == self.now().date() - timedelta(days=1)

    def is_between(
        self, start_time: datetime, end_time: datetime, time_str: str | None = None
    ) -> bool:
        """按实际瞬间检查闭区间，文本采用已配置的日期格式。"""
        start, end = self.to_utc(start_time), self.to_utc(end_time)
        if start.astimezone(UTC) > end.astimezone(UTC):
            raise ValueError("开始时间不能晚于结束时间")
        target = self.now() if time_str is None else self.parse_datetime(time_str)
        return start <= target.astimezone(UTC) <= end

    def is_between_str(self, start_time: str, end_time: str) -> bool:
        """判断本地时刻是否落在每日窗口，结束早于开始时表示跨午夜。"""
        start = datetime.strptime(start_time, self._options.time_format).time()
        end = datetime.strptime(end_time, self._options.time_format).time()
        current = self.now().time()
        return start <= current <= end if start <= end else current >= start or current <= end

    @staticmethod
    def is_overlap(start1: time, end1: time, start2: time, end2: time) -> bool:
        """检查不跨午夜的两个闭区间是否相交，跨午夜范围需调用方拆分。"""
        if start1 > end1 or start2 > end2:
            raise ValueError("跨午夜时间段应先拆分")
        return start1 <= end2 and start2 <= end1

    def get_date_diff_days(self, first: datetime, second: datetime) -> int:
        """按本地日历日期计算绝对天数差，避免 DST 时长影响。"""
        return abs((self.to_timezone(first).date() - self.to_timezone(second).date()).days)

    def days_between(self, value: datetime | None) -> int | None:
        """返回指定本地日期至今天的有符号天数。"""
        return None if value is None else (self.now().date() - self.to_timezone(value).date()).days

    def to_date(self, value: datetime | None) -> date | None:
        """将时间转换为配置时区的日历日期。"""
        return None if value is None else self.to_timezone(value).date()

    def to_timestamp_millis(self, value: datetime | None) -> int | None:
        """转换为 Unix 毫秒，naive 输入按配置时区解释。"""
        if value is None:
            return None
        delta = self.to_utc(value) - datetime(1970, 1, 1, tzinfo=UTC)
        return delta.days * 86_400_000 + delta.seconds * 1000 + delta.microseconds // 1000

    def from_timestamp_millis(self, value: int) -> datetime:
        """将明确的整数毫秒时间戳转换为配置时区。"""
        if type(value) is not int:
            raise TypeError("毫秒时间戳必须是整数")
        return (datetime(1970, 1, 1, tzinfo=UTC) + timedelta(milliseconds=value)).astimezone(
            self._timezone
        )

    def to_timestamp_seconds(self, value: datetime | None) -> int | None:
        """转换为 Unix 秒，保留明确的空值。"""
        return None if value is None else self.to_timestamp_millis(value) // 1000

    @staticmethod
    def get_quarter_of_year(value: datetime) -> int:
        """按输入的日历月份返回季度。"""
        return (value.month - 1) // 3 + 1

    @staticmethod
    def week_of_year(value: datetime) -> int:
        """返回 ISO 周序号。"""
        return value.isocalendar().week

    def begin_of_day(self, value: datetime) -> datetime:
        """返回该本地日期的零点。"""
        return self.to_timezone(value).replace(hour=0, minute=0, second=0, microsecond=0)

    def end_of_day(self, value: datetime) -> datetime:
        """返回该本地日期最后一微秒。"""
        return self.begin_of_day(value) + timedelta(days=1, microseconds=-1)

    def today_start(self) -> datetime:
        """返回本地今天零点。"""
        return self.begin_of_day(self.now())

    def today_end(self) -> datetime:
        """返回本地今天最后一微秒。"""
        return self.end_of_day(self.now())

    def yesterday_start(self) -> datetime:
        """返回本地昨天零点。"""
        return self.today_start() - timedelta(days=1)

    def begin_of_month(self, value: datetime) -> datetime:
        """返回本地月份第一天零点。"""
        return self.begin_of_day(value).replace(day=1)

    def current_month_start(self) -> datetime:
        """返回配置时区本月第一天零点的 datetime。"""
        return self.begin_of_month(self.now())

    def end_of_month(self, value: datetime) -> datetime:
        """返回本地月份最后一微秒。"""
        return DateRangeBuilder.end_of_period(self.to_timezone(value), DateIntervalEnum.MONTH)

    def get_month_start_end(self, value: datetime) -> tuple[datetime, datetime]:
        """返回本地月份的起止边界。"""
        return self.begin_of_month(value), self.end_of_month(value)

    def current_year_start(self) -> datetime:
        """返回配置时区本年第一天零点的 datetime。"""
        return self.today_start().replace(month=1, day=1)

    def get_date_range_list(
        self, start_time: datetime, end_time: datetime, interval: DateIntervalEnum
    ) -> list[list[datetime]]:
        """按日历粒度切分指定日期，范围上限来自当前实例的配置。"""
        if self.to_utc(start_time) > self.to_utc(end_time):
            raise ValueError("开始时间不能晚于结束时间")
        return DateRangeBuilder.build(
            self.begin_of_day(start_time),
            self.end_of_day(end_time),
            interval,
            max_segments=self._options.max_range_segments,
        )

    def format_date_range(
        self, start_time: datetime, end_time: datetime, interval: DateIntervalEnum
    ) -> str:
        """按日期粒度生成范围标签，周和季度使用固定的机器可读格式。"""
        start, end = self.to_timezone(start_time), self.to_timezone(end_time)
        if start.astimezone(UTC) > end.astimezone(UTC):
            raise ValueError("开始时间不能晚于结束时间")
        if interval is DateIntervalEnum.DAY:
            return start.strftime(self._options.date_format)
        if interval is DateIntervalEnum.WEEK:
            iso = start.isocalendar()
            return f"{iso.year}-W{iso.week:02d}"
        if interval is DateIntervalEnum.MONTH:
            return start.strftime(self._options.month_format)
        if interval is DateIntervalEnum.QUARTER:
            return f"{start.year}-Q{self.get_quarter_of_year(start)}"
        if interval is DateIntervalEnum.YEAR:
            return start.strftime(self._options.year_format)
        raise TypeError("interval 必须是 DateIntervalEnum")
