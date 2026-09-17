from datetime import datetime
from typing import Annotated

from pydantic import Field

from framework.common.page.schemas.page_query import PageQuery


class NoticeMessageMyPageReqVO(PageQuery):
    """管理后台 - 我的站内信分页列表 Request VO"""

    read_status: Annotated[bool | None, Field(None, description="是否已读")]
    create_time: Annotated[list[datetime] | None, Field(None, description="创建时间")]
    notice_title: Annotated[str | None, Field(None, description="通知标题")]
    notice_type: Annotated[str | None, Field(None, description="通知类型")]
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "readStatus": True,
                    "createTime": ["2020-05-20T05:20:00Z", "2023-01-31T23:59:59Z"],
                    "pageNo": 1,
                    "pageSize": 10,
                }
            ]
        }
    }
