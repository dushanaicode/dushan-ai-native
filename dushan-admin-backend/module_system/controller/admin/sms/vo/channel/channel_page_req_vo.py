from datetime import datetime
from typing import Annotated

from pydantic import Field

from framework.common.page import PageQuery


class SmsChannelPageReqVO(PageQuery):
    """管理后台 - 短信渠道分页列表 Request VO"""

    status: Annotated[int | None, Field(None, description="任务状态")]
    signature: Annotated[str | None, Field(None, description="短信签名，模糊匹配")]
    code: Annotated[str | None, Field(None, description="渠道编码")]
    create_time: Annotated[list[datetime] | None, Field(None, description="创建时间")]
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "status": 1,
                    "signature": "渡山源码",
                    "code": "du shan yuan ma",
                    "createTime": ["2020-05-20 05:20:00", "2020-05-20 13:14:00"],
                    "pageNo": 1,
                    "pageSize": 10,
                }
            ]
        }
    }
