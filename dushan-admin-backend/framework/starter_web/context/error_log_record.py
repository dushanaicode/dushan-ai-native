from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class ErrorLogRecord:
    """保存框架已规范化的请求与安全异常事实，不携带请求或异常对象。"""

    trace_id: str
    account_id: str | int | None
    tenant_id: str | int | None
    method: str
    route: str
    client_ip: str
    user_agent: str
    exception_time: datetime
    exception_name: str
    exception_message: str
    exception_stack_trace: str
    exception_class_name: str
    exception_file_name: str
    exception_method_name: str
    exception_line_number: int
    result_code: int
