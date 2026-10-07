from datetime import datetime
from typing import Annotated, Any

from pydantic import Field, field_validator

from framework.common.schemas import BaseDTO


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

    @field_validator("result_msg")
    @classmethod
    def truncate_result_msg(cls, value: str | None) -> str | None:
        """截断结果提示，保留未提供提示的状态。"""
        return value[:RESULT_MSG_MAX_LENGTH] if value is not None else None


RESULT_MSG_MAX_LENGTH: int = 512
REQUEST_PARAMS_MAX_LENGTH: int = 8000
RESPONSE_BODY_MAX_LENGTH: int = 8000
