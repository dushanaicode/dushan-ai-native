from typing import Annotated

from pydantic import Field

from framework.common.contracts import (
    SnowflakeIdInput,
)
from framework.common.schemas import BaseRequestVO


class MqSaveReqVO(BaseRequestVO):
    """管理后台 - MQ 消息定义创建/修改 Request VO"""

    id: Annotated[SnowflakeIdInput | None, Field(default=None, description="自增编号")]
    topic: Annotated[str, Field(..., description="消息主题")]
    consumer: Annotated[str, Field(..., description="消费者名称，即处理函数名")]
    retry_count: Annotated[int, Field(..., description="重试次数")]
    description: Annotated[str | None, Field(default=None, description="描述")]
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "id": 1024,
                    "topic": "test-topic",
                    "consumer": "test-consumer",
                    "retryCount": 3,
                    "description": "测试消息",
                }
            ]
        }
    }

    enabled: bool = True
    concurrency: int | None = Field(default=None, ge=1)
    prefetch: int | None = Field(default=None, ge=1)
