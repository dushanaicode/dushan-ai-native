from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class AccessLogRecord:
    """记录请求完成时的框架事实，不携带正文或业务身份类型。"""

    trace_id: str
    account_id: str | int | None
    tenant_id: str | int | None
    method: str
    route: str
    client_ip: str
    user_agent: str
    operate_module: str
    operate_name: str
    operate_type: int
    begin_time: datetime
    end_time: datetime
    duration_ms: int
    result_code: int
