from __future__ import annotations

from typing import Annotated, Any

from pydantic import Field, field_validator

from framework.common.schemas import BaseDTO
from framework.common.validator import NotEmpty, NotNull


class LoginLogCreateReqDTO(BaseDTO):
    """登录日志创建请求 DTO"""

    log_type: Annotated[int, Field(..., description="日志类型")]
    trace_id: Annotated[str, Field("", description="链路追踪编号")]
    user_id: Annotated[int | None, Field(0, description="用户编号")]
    user_type: Annotated[int | None, Field(None, description="用户类型")]
    username: Annotated[str, Field(..., description="用户账号")]
    result: Annotated[int, Field(..., description="登录结果")]
    user_ip: Annotated[str | None, Field(None, description="用户IP")]
    user_agent: Annotated[str | None, Field(None, description="浏览器UA")]
    tenant_id: Annotated[str | None, Field(None, description="租户编号")]
    creator: Annotated[str | None, Field(None, description="创建者")]

    @field_validator("log_type", mode="before")
    @classmethod
    def _validate_log_type(cls, v: Any) -> Any:
        return NotNull.require_not_null(
            field_name="log_type", value=v, error_msg="日志类型不能为空"
        )

    @field_validator("user_type", mode="before")
    @classmethod
    def _validate_user_type(cls, v: Any) -> Any:
        return NotNull.require_not_null(
            field_name="user_type", value=v, error_msg="用户类型不能为空"
        )

    @field_validator("result", mode="before")
    @classmethod
    def _validate_result(cls, v: Any) -> Any:
        return NotNull.require_not_null(field_name="result", value=v, error_msg="登录结果不能为空")

    @field_validator("user_ip", mode="before")
    @classmethod
    def _validate_user_ip(cls, v: Any) -> Any:
        return NotEmpty.require_not_empty(
            field_name="user_ip", value=v, error_msg="用户 IP 不能为空"
        )
