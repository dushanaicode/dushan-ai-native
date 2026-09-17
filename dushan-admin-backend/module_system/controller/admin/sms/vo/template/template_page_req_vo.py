from datetime import datetime
from typing import Annotated

from pydantic import Field

from framework.common.contracts.snowflake_id import (
    SnowflakeIdInput,
)
from framework.common.page.schemas.page_query import PageQuery


class SmsTemplatePageReqVO(PageQuery):
    """管理后台 - 短信模板分页列表 Request VO"""

    type: Annotated[int | None, Field(None, description="短信签名")]
    status: Annotated[int | None, Field(None, description="开启状态")]
    code: Annotated[str | None, Field(None, description="模板编码，模糊匹配")]
    content: Annotated[str | None, Field(None, description="模板内容，模糊匹配")]
    channel_id: Annotated[SnowflakeIdInput | None, Field(None, description="短信渠道编号")]
    create_time: Annotated[list[datetime] | None, Field(None, description="创建时间")]
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "type": 1,
                    "status": 1,
                    "code": "test_01",
                    "content": "你好，{name}。",
                    "channelId": 10,
                    "createTime": ["2020-05-20 05:20:00", "2020-05-20 13:14:00"],
                    "pageNo": 1,
                    "pageSize": 10,
                }
            ]
        }
    }
