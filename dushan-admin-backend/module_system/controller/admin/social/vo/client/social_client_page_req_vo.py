from datetime import datetime
from typing import Annotated

from pydantic import Field

from framework.common.page import PageQuery


class SocialClientPageReqVO(PageQuery):
    """管理后台 - 社交客户端分页列表 Request VO"""

    name: Annotated[str | None, Field(None, description="应用名")]
    social_type: Annotated[int | None, Field(None, description="社交平台的类型")]
    user_type: Annotated[int | None, Field(None, description="用户类型")]
    client_id: Annotated[str | None, Field(None, description="客户端编号")]
    status: Annotated[int | None, Field(None, description="状态")]
    create_time: Annotated[
        list[datetime] | None, Field(None, exclude=True, description="创建时间范围")
    ]
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "name": "dushan商城",
                    "socialType": 31,
                    "userType": 2,
                    "clientId": "145442115",
                    "status": 1,
                    "createTime": ["2020-05-20T05:20:00Z", "2022-07-01T23:59:59Z"],
                    "pageNo": 1,
                    "pageSize": 10,
                }
            ]
        }
    }
