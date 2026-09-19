from datetime import datetime
from typing import Annotated

from pydantic import Field

from framework.common.page import PageQuery


class MqPageReqVO(PageQuery):
    """管理后台 - MQ 消息定义分页列表 Request VO"""

    topic: Annotated[str | None, Field(default=None, description="消息主题，模糊匹配")]
    status: Annotated[int | None, Field(default=None, description="消息状态，参见枚举")]
    consumer: Annotated[str | None, Field(default=None, description="消费者名称，模糊匹配")]
    create_time: Annotated[
        list[datetime] | None, Field(None, exclude=True, description="创建时间范围")
    ]
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "topic": "test-topic",
                    "status": 0,
                    "consumer": "test-consumer",
                    "createTime": ["2020-05-02 05:20:00", "2020-05-02 13:14:00"],
                }
            ]
        }
    }
