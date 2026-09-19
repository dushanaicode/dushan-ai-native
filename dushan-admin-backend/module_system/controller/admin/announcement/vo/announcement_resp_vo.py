from datetime import datetime
from typing import Annotated

from pydantic import Field

from framework.common.contracts import (
    SnowflakeIdStr,
)
from framework.common.schemas import BaseVO


class AnnouncementRespVO(BaseVO):
    """管理后台 - 公告信息 Response VO"""

    id: Annotated[SnowflakeIdStr, Field(..., description="公告序号")]
    title: Annotated[str, Field(..., description="公告标题")]
    content: Annotated[str, Field(..., description="公告内容")]
    status: Annotated[int, Field(..., description="状态，参见 AnnouncementStatusEnum 枚举类")]
    is_top: Annotated[bool, Field(..., description="是否置顶")]
    sort: Annotated[int, Field(..., description="排序序号（数值越小越靠前）")]
    category: Annotated[int, Field(..., description="类别，参见 AnnouncementCategoryEnum 枚举类")]
    publish_time: Annotated[datetime | None, Field(None, description="发布时间")]
    expire_time: Annotated[datetime | None, Field(None, description="过期时间")]
    publisher: Annotated[str, Field(..., description="发布人")]
    create_time: Annotated[datetime, Field(..., description="创建时间")]
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "id": 1024,
                    "title": "系统升级通知",
                    "content": "系统将于2023年10月1日进行升级，届时将暂停服务2小时",
                    "status": 1,
                    "isTop": True,
                    "sort": 0,
                    "category": 1,
                    "publishTime": "2020-05-20 05:20:00",
                    "expireTime": "2020-05-20 13:14:00",
                    "publisher": "dushan",
                    "createTime": "2020-05-20 05:20:00",
                }
            ]
        }
    }
