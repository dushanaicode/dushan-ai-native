from __future__ import annotations

from typing import Annotated, Any

from pydantic import Field, StrictInt, StrictStr, field_validator

from framework.common.schemas.base_dto import BaseDTO
from framework.common.validator.not_empty import NotEmpty
from framework.common.validator.not_null import NotNull


class OperateLogCreateReqDTO(BaseDTO):
    """系统操作日志 Create Request DTO"""

    trace_id: Annotated[str | None, Field(None, description="链路追踪编号")]
    user_id: Annotated[StrictInt, Field(..., description="用户编号")]
    user_type: Annotated[StrictInt, Field(..., description="用户类型")]
    type: Annotated[StrictStr, Field(..., description="操作模块类型")]
    sub_type: Annotated[StrictStr, Field(..., description="操作名")]
    biz_id: Annotated[StrictInt, Field(..., description="操作模块业务编号")]
    action: Annotated[StrictStr, Field(..., description="操作内容")]
    extra: Annotated[str | None, Field(None, description="拓展字段")]
    request_method: Annotated[StrictStr, Field(..., description="请求方法名")]
    request_url: Annotated[StrictStr, Field(..., description="请求地址")]
    user_ip: Annotated[StrictStr, Field(..., description="用户 IP")]
    user_agent: Annotated[StrictStr, Field(..., description="浏览器 UA")]
    user_info: Annotated[dict[str, Any] | None, Field(None, description="用户信息")]

    @field_validator("user_id", mode="before")
    @classmethod
    def _validate_user_id(cls, v: Any) -> Any:
        return NotNull.require_not_null(field_name="userId", value=v, error_msg="用户编号不能为空")

    @field_validator("user_type", mode="before")
    @classmethod
    def _validate_user_type(cls, v: Any) -> Any:
        return NotNull.require_not_null(
            field_name="userType", value=v, error_msg="用户类型不能为空"
        )

    @field_validator("type", mode="before")
    @classmethod
    def _validate_type(cls, v: Any) -> Any:
        return NotNull.require_not_null(
            field_name="type", value=v, error_msg="操作模块类型不能为空"
        )

    @field_validator("sub_type", mode="before")
    @classmethod
    def _validate_sub_type(cls, v: Any) -> Any:
        return NotEmpty.require_not_empty(field_name="subType", value=v, error_msg="操作名不能为空")

    @field_validator("biz_id", mode="before")
    @classmethod
    def _validate_biz_id(cls, v: Any) -> Any:
        return NotNull.require_not_null(
            field_name="bizId", value=v, error_msg="操作模块业务编号不能为空"
        )

    @field_validator("action", mode="before")
    @classmethod
    def _validate_action(cls, v: Any) -> Any:
        return NotEmpty.require_not_empty(
            field_name="action", value=v, error_msg="操作内容不能为空"
        )

    @field_validator("request_method", mode="before")
    @classmethod
    def _validate_request_method(cls, v: Any) -> Any:
        return NotEmpty.require_not_empty(
            field_name="requestMethod", value=v, error_msg="请求方法名不能为空"
        )

    @field_validator("request_url", mode="before")
    @classmethod
    def _validate_request_url(cls, v: Any) -> Any:
        return NotEmpty.require_not_empty(
            field_name="requestUrl", value=v, error_msg="请求地址不能为空"
        )

    @field_validator("user_ip", mode="before")
    @classmethod
    def _validate_user_ip(cls, v: Any) -> Any:
        return NotEmpty.require_not_empty(
            field_name="userIp", value=v, error_msg="用户 IP 不能为空"
        )

    @field_validator("user_agent", mode="before")
    @classmethod
    def _validate_user_agent(cls, v: Any) -> Any:
        return NotEmpty.require_not_empty(
            field_name="userAgent", value=v, error_msg="浏览器 UA 不能为空"
        )
