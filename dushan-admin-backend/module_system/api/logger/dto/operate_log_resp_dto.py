from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any

from pydantic import Field

from framework.common.schemas import BaseDTO


class OperateLogRespDTO(BaseDTO):
    """系统操作日志 Resp DTO"""

    id: Annotated[int | None, Field(default=None, description="日志编号")]
    trace_id: Annotated[str | None, Field(default=None, description="链路追踪编号")]
    user_id: Annotated[int | None, Field(default=None, description="用户编号")]
    user_type: Annotated[int | None, Field(default=None, description="用户类型")]
    type: Annotated[str | None, Field(default=None, description="操作模块类型")]
    sub_type: Annotated[str | None, Field(default=None, description="操作名")]
    biz_id: Annotated[int | None, Field(default=None, description="操作模块业务编号")]
    action: Annotated[str | None, Field(default=None, description="操作内容")]
    extra: Annotated[str | None, Field(default=None, description="拓展字段")]
    request_method: Annotated[str | None, Field(default=None, description="请求方法名")]
    request_url: Annotated[str | None, Field(default=None, description="请求地址")]
    user_ip: Annotated[str | None, Field(default=None, description="用户 IP")]
    user_agent: Annotated[str | None, Field(default=None, description="浏览器 UA")]
    create_time: Annotated[datetime | None, Field(default=None, description="创建时间")]
    user_info: Annotated[dict[str, Any] | None, Field(default=None, description="用户信息")]
