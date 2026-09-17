from datetime import datetime
from typing import Annotated

from pydantic import Field

from framework.common.page.schemas.page_query import PageQuery


class PostPageReqVO(PageQuery):
    """管理后台 - 岗位分页列表 Request VO"""

    code: Annotated[str | None, Field(None, description="岗位编码，模糊匹配")]
    name: Annotated[str | None, Field(None, description="岗位名称，模糊匹配")]
    status: Annotated[int | None, Field(None, description="展示状态，参见 StatusEnum 枚举类")]
    create_time: Annotated[
        list[datetime] | None, Field(None, exclude=True, description="创建时间范围")
    ]
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "code": "dushan",
                    "name": "渡山",
                    "status": 1,
                    "createTime": ["2020-05-20T05:20:00Z", "2022-07-01T23:59:59Z"],
                }
            ]
        }
    }
