from datetime import datetime
from typing import Annotated

from pydantic import Field

from framework.common.page.schemas.page_query import PageQuery


class TenantPageReqVO(PageQuery):
    """管理后台 - 租户分页列表 Request VO"""

    name: Annotated[str | None, Field(None, description="租户名")]
    contact_name: Annotated[str | None, Field(None, description="联系人")]
    contact_mobile: Annotated[str | None, Field(None, description="联系手机")]
    status: Annotated[
        int | None,
        Field(
            None,
            description="租户状态（0正常 1停用）",
            json_schema_extra={"enum_info": {"type": "StatusEnum", "format": "label"}},
        ),
    ]
    create_time: Annotated[list[datetime] | None, Field(None, description="创建时间")]
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "name": "渡山",
                    "contactName": "渡山",
                    "contactMobile": "18888888888",
                    "status": 1,
                    "createTime": ["2020-05-20 05:20:00", "2020-05-20 13:14:00"],
                    "pageNo": 1,
                    "pageSize": 10,
                }
            ]
        }
    }
