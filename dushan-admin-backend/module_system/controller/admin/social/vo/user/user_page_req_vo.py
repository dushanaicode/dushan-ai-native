from datetime import datetime
from typing import Annotated

from pydantic import Field

from framework.common.page.schemas.page_query import PageQuery


class SocialUserPageReqVO(PageQuery):
    """管理后台 - 社交用户分页列表 Request VO"""

    type: Annotated[int | None, Field(None, description="社交平台的类型")]
    nickname: Annotated[str | None, Field(None, description="用户昵称")]
    openid: Annotated[str | None, Field(None, description="社交 openid")]
    create_time: Annotated[
        list[datetime] | None, Field(None, exclude=True, description="创建时间范围")
    ]
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "type": 30,
                    "nickname": "李四",
                    "openid": "oz-Jdt0kd_jdhUxJHQdBJMlOFN7w",
                    "createTime": ["2020-05-20T05:20:00Z", "2022-07-01T23:59:59Z"],
                    "pageNo": 1,
                    "pageSize": 10,
                }
            ]
        }
    }
