from datetime import datetime
from typing import Annotated, Any

from pydantic import Field

from framework.common.contracts import (
    SnowflakeIdStr,
)
from framework.common.schemas import BaseVO
from framework.starter_excel.public import (
    EnumConverter,
    ExcelColumn,
)
from module_infra.definitions.enums.mq.mq_log_status_enum import MqLogStatusEnum


class MqLogRespVO(BaseVO):
    """管理后台 - MQ 消息日志信息 Response VO"""

    id: Annotated[SnowflakeIdStr, Field(..., description="日志编号"), ExcelColumn(title="日志编号")]
    message_id: Annotated[str, Field(..., description="关联的消息ID"), ExcelColumn(title="消息ID")]
    topic: Annotated[str, Field(..., description="消息主题")]
    consumer: Annotated[str, Field(..., description="消费者名称"), ExcelColumn(title="消费者名称")]
    execute_index: Annotated[
        int, Field(..., description="第几次消费"), ExcelColumn(title="第几次消费")
    ]
    begin_time: Annotated[
        datetime, Field(..., description="开始消费时间"), ExcelColumn(title="开始消费时间")
    ]
    end_time: Annotated[
        datetime | None,
        Field(default=None, description="结束消费时间"),
        ExcelColumn(title="结束消费时间"),
    ]
    duration: Annotated[
        int | None,
        Field(default=None, description="消费时长，单位：毫秒"),
        ExcelColumn(title="消费时长"),
    ]
    status: Annotated[
        int,
        Field(..., description="消费状态，参见 MqLogStatusEnum 枚举"),
        ExcelColumn(title="消费状态", converter=EnumConverter(MqLogStatusEnum)),
    ]
    result: Annotated[
        str | None, Field(default=None, description="结果数据"), ExcelColumn(title="结果数据")
    ]
    payload: Annotated[Any | None, Field(default=None, description="消息体/入参 (JSON)")]
    create_time: Annotated[
        datetime, Field(..., description="创建时间"), ExcelColumn(title="创建时间")
    ]
