from typing import Protocol

from framework.starter_web.context.error_log_record import ErrorLogRecord


class ErrorLogProvider(Protocol):
    """由业务模块持久化框架已脱敏的异常诊断。"""

    async def write(self, record: ErrorLogRecord) -> None: ...
