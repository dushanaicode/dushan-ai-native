from datetime import datetime
from typing import Annotated

from pydantic import Field

from framework.common.contracts.snowflake_id import (
    SnowflakeIdInput,
)
from framework.common.page.schemas.page_query import PageQuery


class NoticeMessagePageReqVO(PageQuery):
    """管理后台 - 站内信分页列表 Request VO"""

    user_id: Annotated[SnowflakeIdInput | None, Field(None, description="用户编号")]
    user_type: Annotated[int | None, Field(None, description="用户类型")]
    notice_id: Annotated[SnowflakeIdInput | None, Field(None, description="通知ID")]
    read_status: Annotated[bool | None, Field(None, description="是否已读")]
    notice_title: Annotated[str | None, Field(None, description="标题")]
    notice_type: Annotated[int | None, Field(None, description="通知类型")]
    create_time: Annotated[list[datetime] | None, Field(None, description="创建时间")]
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "userId": 1024,
                    "userType": 1,
                    "noticeId": 1024,
                    "readStatus": True,
                    "noticeTitle": "系统升级",
                    "noticeType": 1,
                    "createTime": ["2020-05-20T05:20:00Z", "2023-01-31T23:59:59Z"],
                    "pageNo": 1,
                    "pageSize": 10,
                }
            ]
        }
    }
