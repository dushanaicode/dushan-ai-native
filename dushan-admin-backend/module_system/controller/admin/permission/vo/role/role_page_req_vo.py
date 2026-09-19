from datetime import datetime
from typing import Annotated

from pydantic import Field

from framework.common.page import PageQuery


class RolePageReqVO(PageQuery):
    """管理后台 - 角色分页列表 Request VO"""

    name: Annotated[str | None, Field(None, description="角色名称，模糊匹配")]
    code: Annotated[str | None, Field(None, description="角色标识，模糊匹配")]
    status: Annotated[int | None, Field(None, description="展示状态，参见 StatusEnum 枚举类")]
    create_time: Annotated[
        list[datetime] | None, Field(None, exclude=True, description="创建时间范围")
    ]
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "name": "渡山",
                    "code": "dushan",
                    "status": 1,
                    "createTime": ["2020-05-20 05:20:00", "2020-05-20 13:14:00"],
                    "pageNo": 1,
                    "pageSize": 10,
                }
            ]
        }
    }
