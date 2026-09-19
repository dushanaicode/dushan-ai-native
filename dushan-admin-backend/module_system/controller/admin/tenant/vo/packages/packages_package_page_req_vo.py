from datetime import datetime
from typing import Annotated

from pydantic import Field

from framework.common.page import PageQuery


class TenantPackagePageReqVO(PageQuery):
    """管理后台 - 租户套餐分页列表 Request VO"""

    name: Annotated[str | None, Field(None, description="套餐名")]
    status: Annotated[int | None, Field(None, description="状态")]
    create_time: Annotated[
        list[datetime] | None, Field(None, exclude=True, description="创建时间范围")
    ]
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "name": "VIP",
                    "status": 1,
                    "createTime": ["2020-05-20T05:20:00Z", "2023-01-31T23:59:59Z"],
                    "pageNo": 1,
                    "pageSize": 10,
                }
            ]
        }
    }
