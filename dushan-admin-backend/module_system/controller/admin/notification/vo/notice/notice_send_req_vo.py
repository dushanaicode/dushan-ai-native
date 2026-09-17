from typing import Annotated

from pydantic import Field

from framework.common.contracts.snowflake_id import (
    SnowflakeIdInput,
)
from framework.common.schemas.base_request_vo import BaseRequestVO


class NoticeSendReqVO(BaseRequestVO):
    """管理后台 - 系统通知发送 Request VO"""

    id: Annotated[SnowflakeIdInput, Field(..., description="通知编号")]
    user_ids: Annotated[
        list[SnowflakeIdInput], Field(default_factory=list, description="接收用户编号")
    ]
    dept_ids: Annotated[
        list[SnowflakeIdInput], Field(default_factory=list, description="接收部门编号")
    ]
