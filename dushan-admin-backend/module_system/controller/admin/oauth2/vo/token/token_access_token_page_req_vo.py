from datetime import datetime
from typing import Annotated

from pydantic import Field

from framework.common.contracts.snowflake_id import (
    SnowflakeIdInput,
)
from framework.common.page.schemas.page_query import PageQuery


class OAuth2AccessTokenPageReqVO(PageQuery):
    """管理后台 - 访问令牌分页列表 Request VO"""

    user_id: Annotated[SnowflakeIdInput | None, Field(None, description="用户编号")]
    user_type: Annotated[int | None, Field(None, description="用户类型，参见 UserTypeEnum 枚举")]
    client_id: Annotated[str | None, Field(None, description="客户端编号")]
    create_time: Annotated[
        list[datetime] | None, Field(None, exclude=True, description="创建时间范围")
    ]
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "userId": 666,
                    "userType": 2,
                    "clientId": "2",
                    "createTime": ["2020-05-20T05:20:00Z", "2023-01-31T23:59:59Z"],
                    "pageNo": 1,
                    "pageSize": 10,
                }
            ]
        }
    }
