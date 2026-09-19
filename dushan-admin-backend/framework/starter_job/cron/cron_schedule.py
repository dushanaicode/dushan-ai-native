import re
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from croniter import croniter

from framework.starter_job.definitions.constants.job_error_codes import JobErrorCodes
from framework.starter_job.exception.job_exception import JobException


class CronSchedule:
    """标准五段，日/星期使用 Vixie OR；DST 跳过不存在时间，重复时间只取第一次。"""

    MONTHS = frozenset("jan feb mar apr may jun jul aug sep oct nov dec".split())
    DAYS = frozenset("sun mon tue wed thu fri sat".split())

    def __init__(self, expression: str, timezone: str):
        fields = expression.lower().split()
        if len(fields) != 5:
            raise JobException(JobErrorCodes.CRON)
        for index, field in enumerate(fields):
            if not re.fullmatch(r"[0-9a-z*/,-]+", field):
                raise JobException(JobErrorCodes.CRON)
            names = set(re.findall("[a-z]+", field))
            allowed = self.MONTHS if index == 3 else self.DAYS if index == 4 else frozenset()
            if not names <= allowed:
                raise JobException(JobErrorCodes.CRON)
        self.expression = " ".join(fields)
        try:
            self.timezone = ZoneInfo(timezone)
            croniter(
                self.expression,
                datetime(2000, 1, 1, tzinfo=UTC),
                day_or=True,
                max_years_between_matches=8,
            ).get_next(datetime)
        except (ValueError, KeyError) as error:
            raise JobException(JobErrorCodes.CRON, cause=error) from error

    def _find(self, base, direction):
        if base.tzinfo is None:
            raise ValueError("Cron 边界时间必须带时区")
        iterator = croniter(
            self.expression,
            base.astimezone(self.timezone),
            day_or=True,
            max_years_between_matches=8,
        )
        try:
            for _ in range(3000):
                candidate = (
                    iterator.get_next(datetime) if direction > 0 else iterator.get_prev(datetime)
                )
                actual = candidate.astimezone(UTC).astimezone(self.timezone)
                if actual.replace(tzinfo=None) != candidate.replace(tzinfo=None) or actual.fold:
                    continue
                if not croniter.match(self.expression, actual.replace(tzinfo=None), day_or=True):
                    continue
                return actual.astimezone(UTC)
            raise JobException(JobErrorCodes.CRON)
        except (ValueError, KeyError) as error:
            raise JobException(JobErrorCodes.CRON, cause=error) from error

    def next(self, after):
        return self._find(after, 1)

    def previous(self, at):
        return self._find(at + timedelta(microseconds=1), -1)

    def preview(self, after, count):
        if type(count) is not int or not 1 <= count <= 100:
            raise ValueError("预览条数须为 1 到 100")
        results = []
        for _ in range(count):
            after = self.next(after)
            results.append(after)
        return results
