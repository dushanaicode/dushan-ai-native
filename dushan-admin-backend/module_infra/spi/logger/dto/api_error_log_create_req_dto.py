from datetime import datetime
from typing import Annotated, Any

from pydantic import Field, field_validator

from framework.common.schemas.base_dto import BaseDTO
from framework.common.validator.not_null import NotNull


class ApiErrorLogCreateReqDTO(BaseDTO):
    """API 错误日志创建请求 DTO"""

    user_id: Annotated[int | None, Field(None, description="用户编号")]
    user_type: Annotated[int | None, Field(None, description="用户类型")]
    application_name: Annotated[str, Field(..., description="应用名")]
    request_method: Annotated[str, Field(..., description="请求方法名")]
    request_url: Annotated[str, Field(..., description="访问地址")]
    request_params: Annotated[dict[str, Any] | None, Field(None, description="请求参数")]
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

    @field_validator("application_name", mode="before")
    @classmethod
    def _validate_application_name(cls, v: Any) -> Any:
        return NotNull.require_not_null(
            field_name="applicationName", value=v, error_msg="应用名不能为空"
        )

    @field_validator("request_method", mode="before")
    @classmethod
    def _validate_request_method(cls, v: Any) -> Any:
        return NotNull.require_not_null(
            field_name="requestMethod", value=v, error_msg="http 请求方法不能为空"
        )

    @field_validator("request_url", mode="before")
    @classmethod
    def _validate_request_url(cls, v: Any) -> Any:
        return NotNull.require_not_null(
            field_name="requestUrl", value=v, error_msg="访问地址不能为空"
        )

    @field_validator("request_params", mode="before")
    @classmethod
    def _validate_request_params(cls, v: Any) -> Any:
        return NotNull.require_not_null(
            field_name="requestParams", value=v, error_msg="请求参数不能为空"
        )

    @field_validator("user_ip", mode="before")
    @classmethod
    def _validate_user_ip(cls, v: Any) -> Any:
        return NotNull.require_not_null(field_name="userIp", value=v, error_msg="ip 不能为空")

    @field_validator("user_agent", mode="before")
    @classmethod
    def _validate_user_agent(cls, v: Any) -> Any:
        return NotNull.require_not_null(
            field_name="userAgent", value=v, error_msg="User-Agent 不能为空"
        )

    @field_validator("exception_time", mode="before")
    @classmethod
    def _validate_exception_time(cls, v: Any) -> Any:
        return NotNull.require_not_null(
            field_name="exceptionTime", value=v, error_msg="异常时间不能为空"
        )

    @field_validator("exception_name", mode="before")
    @classmethod
    def _validate_exception_name(cls, v: Any) -> Any:
        return NotNull.require_not_null(
            field_name="exceptionName", value=v, error_msg="异常名不能为空"
        )

    @field_validator("exception_class_name", mode="before")
    @classmethod
    def _validate_exception_class_name(cls, v: Any) -> Any:
        return NotNull.require_not_null(
            field_name="exceptionClassName", value=v, error_msg="异常发生的类全名不能为空"
        )

    @field_validator("exception_file_name", mode="before")
    @classmethod
    def _validate_exception_file_name(cls, v: Any) -> Any:
        return NotNull.require_not_null(
            field_name="exceptionFileName", value=v, error_msg="异常发生的类文件不能为空"
        )

    @field_validator("exception_method_name", mode="before")
    @classmethod
    def _validate_exception_method_name(cls, v: Any) -> Any:
        return NotNull.require_not_null(
            field_name="exceptionMethodName", value=v, error_msg="异常发生的方法名不能为空"
        )

    @field_validator("exception_line_number", mode="before")
    @classmethod
    def _validate_exception_line_number(cls, v: Any) -> Any:
        return NotNull.require_not_null(
            field_name="exceptionLineNumber", value=v, error_msg="异常发生的方法所在行不能为空"
        )

    @field_validator("exception_stack_trace", mode="before")
    @classmethod
    def _validate_exception_stack_trace(cls, v: Any) -> Any:
        """验证并截断异常堆栈信息"""
        value = NotNull.require_not_null(
            field_name="exceptionStackTrace", value=v, error_msg="异常的栈轨迹不能为空"
        )
        if isinstance(value, str) and len(value) > EXCEPTION_STACK_TRACE_MAX_LENGTH:
            return value[:EXCEPTION_STACK_TRACE_MAX_LENGTH]
        return value

    @field_validator("exception_root_cause_message", mode="before")
    @classmethod
    def _validate_exception_root_cause_message(cls, v: Any) -> Any:
        """验证并截断异常的根消息"""
        value = NotNull.require_not_null(
            field_name="exceptionRootCauseMessage", value=v, error_msg="异常导致的根消息不能为空"
        )
        if isinstance(value, str) and len(value) > EXCEPTION_ROOT_CAUSE_MAX_LENGTH:
            return value[:EXCEPTION_ROOT_CAUSE_MAX_LENGTH]
        return value

    @field_validator("exception_message", mode="before")
    @classmethod
    def _validate_exception_message(cls, v: Any) -> Any:
        """验证并截断异常消息"""
        value = NotNull.require_not_null(
            field_name="exceptionMessage", value=v, error_msg="异常导致的消息不能为空"
        )
        if isinstance(value, str) and len(value) > EXCEPTION_MESSAGE_MAX_LENGTH:
            return value[:EXCEPTION_MESSAGE_MAX_LENGTH]
        return value


EXCEPTION_MESSAGE_MAX_LENGTH: int = 512
EXCEPTION_ROOT_CAUSE_MAX_LENGTH: int = 512
EXCEPTION_STACK_TRACE_MAX_LENGTH: int = 2048
