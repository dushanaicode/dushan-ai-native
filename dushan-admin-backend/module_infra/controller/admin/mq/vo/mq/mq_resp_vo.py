from datetime import datetime
from typing import Annotated

from pydantic import Field

from framework.common.contracts.snowflake_id import (
    SnowflakeIdStr,
)
from framework.common.schemas.base_vo import BaseVO
from framework.starter_excel.model.excel_column import ExcelColumn


class MqRespVO(BaseVO):
    """管理后台 - MQ 消息定义信息 Response VO"""

    id: Annotated[SnowflakeIdStr, Field(..., description="自增编号"), ExcelColumn(title="编号")]
    topic: Annotated[str, Field(..., description="消息主题"), ExcelColumn(title="消息主题")]
    consumer: Annotated[str, Field(..., description="消费者名称"), ExcelColumn(title="消费者")]
    retry_count: Annotated[int, Field(..., description="重试次数"), ExcelColumn(title="重试次数")]
    description: Annotated[str | None, Field(default=None, description="描述")]
    create_time: Annotated[
        datetime, Field(..., description="创建时间"), ExcelColumn(title="创建时间")
    ]

    enabled: bool = True
    concurrency: int | None = Field(default=None, ge=1)
    prefetch: int | None = Field(default=None, ge=1)
