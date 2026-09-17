from datetime import datetime
from typing import Annotated

from pydantic import Field

from framework.common.contracts.snowflake_id import (
    SnowflakeIdInput,
)
from framework.common.schemas.base_request_vo import BaseRequestVO


class NoticeLogMessageVO(BaseRequestVO):
    """管理后台 - 推送日志消息明细 VO"""

    id: Annotated[SnowflakeIdInput, Field(..., description="消息ID")]
    user_id: Annotated[SnowflakeIdInput, Field(..., description="用户编号")]
    username: Annotated[str | None, Field(None, description="用户名")]
    nickname: Annotated[str | None, Field(None, description="用户昵称")]
    user_type: Annotated[int, Field(..., description="用户类型")]
    read_status: Annotated[bool, Field(..., description="是否已读")]
    read_time: Annotated[datetime | None, Field(None, description="阅读时间")]
    create_time: Annotated[datetime, Field(..., description="创建时间")]
