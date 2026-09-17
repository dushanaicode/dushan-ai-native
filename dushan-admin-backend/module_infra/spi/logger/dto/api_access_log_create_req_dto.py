from datetime import datetime
from typing import Annotated, Any

from pydantic import Field, field_validator

from framework.common.schemas.base_dto import BaseDTO
from framework.common.validator.not_null import NotNull


class ApiAccessLogCreateReqDTO(BaseDTO):
    """API 访问日志创建请求 DTO"""

    trace_id: Annotated[str | None, Field(None, description="链路追踪编号")]
    user_id: Annotated[int | None, Field(None, description="用户编号")]
    user_type: Annotated[int | None, Field(None, description="用户类型")]
    application_name: Annotated[str, Field(..., description="应用名")]
    request_method: Annotated[str, Field(..., description="请求方法名")]
    request_url: Annotated[str, Field(..., description="访问地址")]
    request_params: Annotated[dict[str, Any] | None, Field(None, description="请求参数 (字典形式)")]
    response_body: Annotated[Any | None, Field(None, description="响应结果 (任意 JSON 类型)")]
    user_ip: Annotated[str, Field(..., description="用户 IP")]
    user_agent: Annotated[str, Field(..., description="浏览器 UA")]
    operate_module: Annotated[str | None, Field(None, description="操作模块")]
    operate_name: Annotated[str | None, Field(None, description="操作名")]
    operate_type: Annotated[int | None, Field(None, description="操作分类")]
    begin_time: Annotated[datetime, Field(..., description="开始请求时间")]
    end_time: Annotated[datetime, Field(..., description="结束请求时间")]
    duration: Annotated[int, Field(..., description="执行时长，单位：毫秒")]
    result_code: Annotated[int, Field(..., description="结果码")]
    result_msg: Annotated[str | None, Field(None, description="结果提示")]
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

    @field_validator("begin_time", mode="before")
    @classmethod
    def _validate_begin_time(cls, v: Any) -> Any:
        return NotNull.require_not_null(
            field_name="beginTime", value=v, error_msg="开始请求时间不能为空"
        )

    @field_validator("end_time", mode="before")
    @classmethod
    def _validate_end_time(cls, v: Any) -> Any:
        return NotNull.require_not_null(
            field_name="endTime", value=v, error_msg="结束请求时间不能为空"
        )

    @field_validator("duration", mode="before")
    @classmethod
    def _validate_duration(cls, v: Any) -> Any:
        return NotNull.require_not_null(
            field_name="duration", value=v, error_msg="执行时长不能为空"
        )

    @field_validator("result_code", mode="before")
    @classmethod
    def _validate_result_code(cls, v: Any) -> Any:
        return NotNull.require_not_null(
            field_name="resultCode", value=v, error_msg="错误码不能为空"
        )

    @field_validator("result_msg", mode="before")
    @classmethod
    def truncate_result_msg(cls, v: Any):
        """在验证前截断 result_msg"""
        if isinstance(v, str):
            if len(v) > RESULT_MSG_MAX_LENGTH:
                return v[:RESULT_MSG_MAX_LENGTH]
        return v


RESULT_MSG_MAX_LENGTH: int = 512
REQUEST_PARAMS_MAX_LENGTH: int = 8000
RESPONSE_BODY_MAX_LENGTH: int = 8000
