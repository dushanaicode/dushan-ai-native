from datetime import datetime
from typing import Annotated

from pydantic import Field

from framework.common.contracts.snowflake_id import (
    SnowflakeIdInput,
    SnowflakeReferenceInput,
)
from framework.common.schemas.base_request_vo import BaseRequestVO


class TenantUpdateReqVO(BaseRequestVO):
    """管理后台 - 租户更新 Request VO"""

    id: Annotated[SnowflakeIdInput, Field(..., description="租户编号")]
    name: Annotated[str | None, Field(None, description="租户名")]
    contact_name: Annotated[str | None, Field(None, description="联系人")]
    contact_mobile: Annotated[str | None, Field(None, description="联系手机")]
    status: Annotated[int | None, Field(None, description="租户状态")]
    websites: Annotated[list[str] | None, Field(None, description="绑定域名列表")]
    package_id: Annotated[SnowflakeReferenceInput | None, Field(None, description="租户套餐编号")]
    expire_time: Annotated[datetime | None, Field(None, description="过期时间")]
    account_count: Annotated[int | None, Field(None, description="账号数量")]
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "id": 1024,
                    "name": "渡山",
                    "contactName": "渡山",
                    "contactMobile": "18888888888",
                    "status": 1,
                    "websites": ["https://www.dushan.cn"],
                    "packageId": 1024,
                    "expireTime": "2020-05-20T05:20:00Z",
                    "accountCount": 1024,
                }
            ]
        }
    }
