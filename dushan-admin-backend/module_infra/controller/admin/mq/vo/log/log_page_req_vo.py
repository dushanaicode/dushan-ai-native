from datetime import datetime
from typing import Annotated

from pydantic import Field

from framework.common.page.schemas.page_query import PageQuery


class MqLogPageReqVO(PageQuery):
    """管理后台 - MQ 消息日志分页列表 Request VO"""

    message_id: Annotated[str | None, Field(default=None, description="关联的消息ID")]
    consumer: Annotated[str | None, Field(default=None, description="消费者名称，模糊匹配")]
    begin_time: Annotated[datetime | None, Field(default=None, description="开始消费时间")]
    end_time: Annotated[datetime | None, Field(default=None, description="结束消费时间")]
    status: Annotated[
        int | None, Field(default=None, description="消费状态，参见 MqLogStatusEnum 枚举")
    ]
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "messageId": "a8c6b7e1-3d5f-4a9b-8c7d-6e5f4a3b2c1d",
                    "consumer": "test-consumer",
                    "beginTime": "2023-01-01T00:00:00",
                    "endTime": "2023-01-01T23:59:59",
                    "status": 1,
                }
            ]
        }
    }
