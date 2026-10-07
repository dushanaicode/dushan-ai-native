from typing import Protocol

from framework.starter_web.context.access_log_record import AccessLogRecord


class AccessLogProvider(Protocol):
    """由业务模块接收框架生成的访问日志记录。"""

    async def write(self, record: AccessLogRecord) -> None: ...
