from datetime import datetime
from typing import Annotated, Any

from pydantic import Field, field_validator

from framework.common.schemas import BaseDTO


class ApiErrorLogCreateReqDTO(BaseDTO):
    """API 错误日志创建请求 DTO"""

    user_id: Annotated[int | None, Field(None, description="用户编号")]
    user_type: Annotated[int | None, Field(None, description="用户类型")]
    application_name: Annotated[str, Field(..., description="应用名")]
    request_method: Annotated[str, Field(..., description="请求方法名")]
    request_url: Annotated[str, Field(..., description="访问地址")]
    request_params: Annotated[dict[str, Any], Field(..., description="请求参数")]
    user_ip: Annotated[str, Field(..., description="用户 IP")]
    user_agent: Annotated[str, Field(..., description="浏览器 UA")]
    exception_time: Annotated[datetime, Field(..., description="异常发生时间")]
    exception_name: Annotated[str, Field(..., description="异常名")]
    exception_message: Annotated[str, Field(..., description="异常导致的消息")]
    exception_root_cause_message: Annotated[str, Field(..., description="异常导致的根消息")]
    exception_stack_trace: Annotated[str, Field(..., description="异常的栈轨迹")]
    exception_class_name: Annotated[str, Field(..., description="异常发生的类全名")]
    exception_file_name: Annotated[str, Field(..., description="异常发生的类文件")]
    exception_method_name: Annotated[str, Field(..., description="异常发生的方法名")]
    exception_line_number: Annotated[int, Field(..., description="异常发生的方法所在行")]
    trace_id: Annotated[str, Field(..., description="链路追踪编号")]
    tenant_id: Annotated[str | None, Field(None, description="租户编号")]

    @field_validator("exception_stack_trace")
    @classmethod
    def _validate_exception_stack_trace(cls, value: str) -> str:
        """按存储上限截断异常堆栈。"""
        return value[:EXCEPTION_STACK_TRACE_MAX_LENGTH]

    @field_validator("exception_root_cause_message")
    @classmethod
    def _validate_exception_root_cause_message(cls, value: str) -> str:
        """按存储上限截断异常根消息。"""
        return value[:EXCEPTION_ROOT_CAUSE_MAX_LENGTH]

    @field_validator("exception_message")
    @classmethod
    def _validate_exception_message(cls, value: str) -> str:
        """按存储上限截断异常消息。"""
        return value[:EXCEPTION_MESSAGE_MAX_LENGTH]


EXCEPTION_MESSAGE_MAX_LENGTH: int = 512
EXCEPTION_ROOT_CAUSE_MAX_LENGTH: int = 512
EXCEPTION_STACK_TRACE_MAX_LENGTH: int = 2048
