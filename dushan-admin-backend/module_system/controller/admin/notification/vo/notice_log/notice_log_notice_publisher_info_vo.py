from typing import Annotated

from pydantic import Field

from framework.common.contracts.snowflake_id import (
    SnowflakeIdInput,
)
from framework.common.schemas.base_request_vo import BaseRequestVO


class NoticePublisherInfoVO(BaseRequestVO):
    """管理后台 - 站内信发布者信息 VO"""

    id: Annotated[SnowflakeIdInput | None, Field(None, description="发布者用户ID")]
    username: Annotated[str | None, Field(None, description="发布者用户名")]
    nickname: Annotated[str | None, Field(None, description="发布者昵称")]
    avatar: Annotated[str | None, Field(None, description="发布者头像地址")]
    os: Annotated[str | None, Field(None, description="操作系统")]
    browser: Annotated[str | None, Field(None, description="浏览器信息")]
    ipaddr: Annotated[str | None, Field(None, description="IP 地址")]
    dept_id: Annotated[str | None, Field(None, description="部门 ID")]
    login_time: Annotated[str | None, Field(None, description="登录时间戳")]
    login_location: Annotated[str | None, Field(None, description="登录地点")]
